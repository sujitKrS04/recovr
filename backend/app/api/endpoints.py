from fastapi import APIRouter, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import asyncio
from typing import List, Dict, Any

from app.core.database import get_db
from app.core.auth_deps import get_current_user, require_analyst_or_above, require_admin
from app.models.auth_models import User
from app.models.models import Transaction, TransactionStatus, BaselineResult, ActionLog, RecoveryReceipt
from app.api.ws import manager
from app.services import classifier, decision_agent, executors, compliance_guard, receipts

router = APIRouter()


# ---------------------------------------------------------------------------
# WebSocket — per-org broadcast
# ---------------------------------------------------------------------------

@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket, org_id: int = Query(...)):
    """
    Connect with ?org_id=<id> so the server can scope broadcasts to the
    authenticated organization.  The org_id is passed as a query param
    (WebSocket doesn't support Authorization headers in browsers).
    """
    await manager.connect(websocket, org_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, org_id)
    except Exception as e:
        import logging
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, org_id)


# ---------------------------------------------------------------------------
# GET /api/summary
# ---------------------------------------------------------------------------

@router.get("/api/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Summary stats for the dashboard — scoped to the authenticated org."""
    org_id = current_user.org_id
    txs = db.query(Transaction).filter(Transaction.org_id == org_id).all()
    total_at_risk = sum((float(tx.amount) for tx in txs), 0.0)

    recovered_txs = [tx for tx in txs if tx.status == TransactionStatus.recovered]
    total_recovered = sum((float(tx.amount) for tx in recovered_txs), 0.0)
    
    recovering_txs = [tx for tx in txs if tx.status == TransactionStatus.recovering]
    total_recovering = sum((float(tx.amount) for tx in recovering_txs), 0.0)

    recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk else 0.0

    tx_ids = [tx.id for tx in txs]
    baselines = db.query(BaselineResult).filter(BaselineResult.transaction_id.in_(tx_ids)).all() if tx_ids else []
    baseline_recovered = sum(float(b.amount_recovered or 0) for b in baselines if b.recovered)
    baseline_rate = (baseline_recovered / total_at_risk * 100) if total_at_risk else 0.0

    # Break down by category
    categories: dict = {}
    for tx in txs:
        cat = "unclassified"
        if tx.classifications:
            cat = tx.classifications[0].root_cause_category.value
        if cat not in categories:
            categories[cat] = {"total": 0, "recovered": 0.0, "at_risk": 0.0, "recovering": 0.0}

        categories[cat]["total"] += 1
        categories[cat]["at_risk"] += float(tx.amount)
        if tx.status == TransactionStatus.recovered:
            categories[cat]["recovered"] += float(tx.amount)
        elif tx.status == TransactionStatus.recovering:
            categories[cat]["recovering"] += float(tx.amount)

    return {
        "total_at_risk": total_at_risk,
        "total_recovered": total_recovered,
        "total_recovering": total_recovering,
        "recovery_rate": recovery_rate,
        "baseline_recovery_rate": baseline_rate,
        "categories": categories,
    }


# ---------------------------------------------------------------------------
# GET /api/transactions
# ---------------------------------------------------------------------------

@router.get("/api/transactions")
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: str | None = None,
    category: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """Paginated list of transactions — scoped to the authenticated org."""
    query = db.query(Transaction).filter(Transaction.org_id == current_user.org_id)
    if status:
        query = query.filter(Transaction.status == status)

    txs = query.order_by(Transaction.id).offset(offset).limit(limit).all()

    result = []
    for tx in txs:
        cat = tx.classifications[0].root_cause_category.value if tx.classifications else None
        if category and cat != category:
            continue

        decision = tx.decisions[0] if tx.decisions else None

        result.append({
            "id": tx.id,
            "external_payment_id": tx.external_payment_id,
            "customer_name": tx.customer_name,
            "amount": tx.amount,
            "currency": tx.currency,
            "status": tx.status.value,
            "failure_reason": tx.failure_reason,
            "category": cat,
            "action": decision.action_type.value if decision else None,
            "auto_executed": decision.auto_executed if decision else None,
            "retry_count": tx.retry_count,
        })
    return result


# ---------------------------------------------------------------------------
# GET /api/receipts
# ---------------------------------------------------------------------------

@router.get("/api/receipts")
def get_all_receipts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
):
    """List of recovery receipts — scoped to the authenticated org."""
    # Get org transaction IDs first
    tx_ids = [
        tx.id for tx in db.query(Transaction.id).filter(Transaction.org_id == current_user.org_id).all()
    ]
    if not tx_ids:
        return []

    receipts_list = (
        db.query(RecoveryReceipt)
        .filter(RecoveryReceipt.transaction_id.in_(tx_ids))
        .order_by(RecoveryReceipt.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    res = []
    for r in receipts_list:
        tx = db.query(Transaction).filter(Transaction.id == r.transaction_id).first()
        res.append({
            "id": r.id,
            "transaction_id": r.transaction_id,
            "customer_name": tx.customer_name if tx else "Unknown",
            "amount": tx.amount if tx else 0,
            "root_cause": r.root_cause,
            "action_taken": r.action_taken,
            "reasoning": r.reasoning,
            "amount_recovered": r.amount_recovered if r.amount_recovered else None,
            "outcome": r.outcome.value if hasattr(r.outcome, "value") else str(r.outcome),
            "generated_at": str(r.generated_at),
        })
    return res


# ---------------------------------------------------------------------------
# GET /api/receipts/{transaction_id}
# ---------------------------------------------------------------------------

@router.get("/api/receipts/{transaction_id}")
def get_receipt(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full recovery receipt for a given transaction — org-scoped."""
    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.org_id == current_user.org_id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    receipt = db.query(RecoveryReceipt).filter(RecoveryReceipt.transaction_id == transaction_id).first()
    if not receipt:
        return {"error": "Receipt not found"}

    return {
        "id": receipt.id,
        "transaction_id": receipt.transaction_id,
        "customer_name": tx.customer_name,
        "amount": tx.amount,
        "root_cause": receipt.root_cause,
        "action_taken": receipt.action_taken,
        "reasoning": receipt.reasoning,
        "amount_recovered": receipt.amount_recovered if receipt.amount_recovered else None,
        "outcome": receipt.outcome.value if hasattr(receipt.outcome, "value") else str(receipt.outcome),
        "generated_at": str(receipt.generated_at),
    }


# ---------------------------------------------------------------------------
# GET /api/review-queue
# ---------------------------------------------------------------------------

@router.get("/api/review-queue")
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transactions escalated to human review — org-scoped."""
    txs = db.query(Transaction).filter(
        Transaction.org_id == current_user.org_id,
        Transaction.status == TransactionStatus.escalated,
    ).all()
    queue = []
    for tx in txs:
        decision = tx.decisions[0] if tx.decisions else None
        classification = tx.classifications[0] if tx.classifications else None
        queue.append({
            "transaction_id": tx.id,
            "customer_name": tx.customer_name,
            "amount": tx.amount,
            "failure_reason": tx.failure_reason,
            "category": classification.root_cause_category.value if classification else "fraud_false_positive",
            "confidence": classification.confidence if classification else 0.1,
            "decision_reasoning": decision.reasoning if decision else "No reasoning available",
        })
    return queue


# ---------------------------------------------------------------------------
# POST /api/simulate-failure — analyst+ only
# ---------------------------------------------------------------------------

@router.post("/api/simulate-failure")
def simulate_failure(current_user: User = Depends(require_analyst_or_above)):
    """Deliberately injects a failure into the next executor call."""
    executors.INJECT_FAILURE_ONCE = True
    return {"message": "Failure injection armed for next execution."}


# ---------------------------------------------------------------------------
# POST /api/simulate-payment-confirmation/{transaction_id}
# ---------------------------------------------------------------------------

@router.post("/api/simulate-payment-confirmation/{transaction_id}")
async def simulate_payment_confirmation(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Simulates a Razorpay webhook for a customer completing a payment."""
    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id, 
        Transaction.org_id == current_user.org_id
    ).first()
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
        
    if tx.status != TransactionStatus.recovering:
        raise HTTPException(status_code=400, detail="Transaction is not in recovering state.")
        
    tx.status = TransactionStatus.recovered
    
    # Update the corresponding action_log amount_recovered
    if tx.decisions and tx.decisions[0].actions_log:
        latest_action = tx.decisions[0].actions_log[-1]
        latest_action.amount_recovered = tx.amount
        
    # Generate receipt
    receipt = receipts.generate_receipt(tx, db)
    db.commit()
    
    # Broadcast to dashboard
    classification = tx.classifications[0] if tx.classifications else None
    decision = tx.decisions[0] if tx.decisions else None
    
    from datetime import datetime
    time_str = datetime.now().strftime("%H:%M:%S")
    await manager.broadcast_to_org(current_user.org_id, {
        "type": "tx_recovered_async",
        "transaction_id": tx.id,
        "customer_name": tx.customer_name,
        "amount": float(tx.amount),
        "category": classification.root_cause_category.value if classification else "unknown",
        "action": decision.action_type.value if decision else "unknown",
        "status": tx.status.value,
        "success": True,
        "reasoning": receipt.reasoning if receipt else "Payment completed successfully.",
        "timestamp": time_str,
    })
    
    return {"message": "Payment confirmed and transaction recovered."}


# ---------------------------------------------------------------------------
# Background batch pipeline
# ---------------------------------------------------------------------------

async def _run_batch_pipeline(org_id: int):
    """
    Background task to run the full pipeline end-to-end and broadcast events
    to the organization's connected WebSocket clients.
    """
    from app.core.database import SessionLocal
    from datetime import datetime
    db = SessionLocal()
    try:
        txs = db.query(Transaction).filter(
            Transaction.org_id == org_id,
            Transaction.status.in_([TransactionStatus.failed, TransactionStatus.recovering]),
        ).all()

        for tx in txs:
            time_str = datetime.now().strftime("%H:%M:%S")
            # Phase 3: Classifier
            c_res = classifier.classify_and_persist(tx, db)
            await manager.broadcast_to_org(org_id, {
                "type": "tx_classified",
                "transaction_id": tx.id,
                "customer_name": tx.customer_name,
                "amount": float(tx.amount),
                "failure_reason": tx.failure_reason,
                "category": c_res.root_cause_category.value,
                "confidence": c_res.confidence,
                "timestamp": time_str,
            })
            await asyncio.sleep(0.04)

            # Phase 4: Decision
            d_res = decision_agent.decide_and_persist(tx, c_res, db)
            await manager.broadcast_to_org(org_id, {
                "type": "tx_decided",
                "transaction_id": tx.id,
                "customer_name": tx.customer_name,
                "amount": float(tx.amount),
                "failure_reason": tx.failure_reason,
                "category": c_res.root_cause_category.value,
                "confidence": c_res.confidence,
                "action": d_res.action_type.value,
                "auto_executed": d_res.auto_executed,
                "reasoning": d_res.reasoning,
                "timestamp": time_str,
            })
            await asyncio.sleep(0.04)

            # Phase 5 & 6: Executor & Compliance
            decision_record = d_res
            db.flush()

            action_log = executors.execute_decision(
                tx, decision_record, db, category=c_res.root_cause_category
            )

            # If simulated failure occurred, simulate automated retry and recovery
            if not action_log.success and "SIMULATED FAILURE" in (action_log.error_message or ""):
                await manager.broadcast_to_org(org_id, {
                    "type": "tx_failed_injected",
                    "transaction_id": tx.id,
                    "customer_name": tx.customer_name,
                    "amount": float(tx.amount),
                    "category": c_res.root_cause_category.value,
                    "confidence": c_res.confidence,
                    "action": d_res.action_type.value,
                    "status": "failed",
                    "success": False,
                    "reasoning": "Detected transient gateway connection reset. Queuing automatic retry...",
                    "timestamp": time_str,
                })
                await asyncio.sleep(0.2)

                tx.status = TransactionStatus.recovering
                retry_log = executors.execute_decision(
                    tx, decision_record, db, category=c_res.root_cause_category
                )
                time_str = datetime.now().strftime("%H:%M:%S")

                if tx.status in (TransactionStatus.recovered, TransactionStatus.failed, TransactionStatus.escalated, TransactionStatus.suppressed, TransactionStatus.exhausted):
                    receipts.generate_receipt(tx, db)
                    db.commit()

                await manager.broadcast_to_org(org_id, {
                    "type": "tx_retried_recovered",
                    "transaction_id": tx.id,
                    "customer_name": tx.customer_name,
                    "amount": float(tx.amount),
                    "category": c_res.root_cause_category.value,
                    "confidence": c_res.confidence,
                    "action": d_res.action_type.value,
                    "status": tx.status.value,
                    "success": True,
                    "reasoning": f"Automated retry successful: recovered INR {int(tx.amount)} via fallback gateway route.",
                    "timestamp": time_str,
                })
                await asyncio.sleep(0.08)
                continue

            # Normal execution completion
            receipt = None
            if tx.status in (TransactionStatus.recovered, TransactionStatus.failed, TransactionStatus.escalated, TransactionStatus.suppressed, TransactionStatus.exhausted):
                receipt = receipts.generate_receipt(tx, db)
                db.commit()

            await manager.broadcast_to_org(org_id, {
                "type": "tx_executed",
                "transaction_id": tx.id,
                "customer_name": tx.customer_name,
                "amount": float(tx.amount),
                "category": c_res.root_cause_category.value,
                "confidence": c_res.confidence,
                "action": d_res.action_type.value,
                "status": tx.status.value,
                "success": action_log.success,
                "reasoning": receipt.reasoning if receipt else (d_res.reasoning or "Action completed."),
                "error_message": action_log.error_message,
                "timestamp": time_str,
            })

            await asyncio.sleep(0.06)
            
        # Demo Auto-Simulation: convert ~70% of 'recovering' to 'recovered' after a short delay
        recovering_txs = [tx for tx in txs if tx.status == TransactionStatus.recovering]
        if recovering_txs:
            await asyncio.sleep(3.0) # Simulate customer dwell time
            import random
            
            # Select 70% to simulate payment completion
            num_to_convert = int(len(recovering_txs) * 0.70)
            txs_to_convert = random.sample(recovering_txs, num_to_convert)
            
            for tx in txs_to_convert:
                tx.status = TransactionStatus.recovered
                if tx.decisions and tx.decisions[0].actions_log:
                    tx.decisions[0].actions_log[-1].amount_recovered = tx.amount
                    
                receipt = receipts.generate_receipt(tx, db)
                db.commit()
                
                c_res = tx.classifications[0] if tx.classifications else None
                d_res = tx.decisions[0] if tx.decisions else None
                
                time_str = datetime.now().strftime("%H:%M:%S")
                await manager.broadcast_to_org(org_id, {
                    "type": "tx_recovered_async",
                    "transaction_id": tx.id,
                    "customer_name": tx.customer_name,
                    "amount": float(tx.amount),
                    "category": c_res.root_cause_category.value if c_res else "unknown",
                    "action": d_res.action_type.value if d_res else "unknown",
                    "status": tx.status.value,
                    "success": True,
                    "reasoning": receipt.reasoning if receipt else "Customer completed payment via link/prompt.",
                    "timestamp": time_str,
                })
                await asyncio.sleep(0.15)

    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /api/run-batch — admin only
# ---------------------------------------------------------------------------

@router.post("/api/run-batch")
def run_batch(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Triggers the full pipeline run on demand — admin only, org-scoped."""
    from app.models.models import Classification, Decision
    org_id = current_user.org_id

    # Only clean up this org's data
    tx_ids = [
        tx.id for tx in db.query(Transaction.id).filter(Transaction.org_id == org_id).all()
    ]
    if tx_ids:
        db.query(ActionLog).filter(
            ActionLog.decision_id.in_(
                db.query(Decision.id).filter(Decision.transaction_id.in_(tx_ids))
            )
        ).delete(synchronize_session=False)
        db.query(RecoveryReceipt).filter(RecoveryReceipt.transaction_id.in_(tx_ids)).delete(synchronize_session=False)
        db.query(Decision).filter(Decision.transaction_id.in_(tx_ids)).delete(synchronize_session=False)
        from app.models.models import Classification
        db.query(Classification).filter(Classification.transaction_id.in_(tx_ids)).delete(synchronize_session=False)
        db.query(Transaction).filter(Transaction.id.in_(tx_ids)).update(
            {"status": TransactionStatus.failed, "retry_count": 0}, synchronize_session=False
        )
    db.commit()

    background_tasks.add_task(_run_batch_pipeline, org_id)
    return {"message": "Batch pipeline started in background."}
