from fastapi import APIRouter, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import asyncio
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.models import Transaction, TransactionStatus, BaselineResult, ActionLog, RecoveryReceipt
from app.api.ws import manager
from app.services import classifier, decision_agent, executors, compliance_guard, receipts

router = APIRouter()

# WebSocket endpoint
@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        import logging
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/api/summary")
def get_summary(db: Session = Depends(get_db)):
    """Summary stats for the dashboard."""
    txs = db.query(Transaction).all()
    total_at_risk = sum(tx.amount for tx in txs)
    
    recovered_txs = [tx for tx in txs if tx.status == TransactionStatus.recovered]
    total_recovered = sum(tx.amount for tx in recovered_txs)
    recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk else 0.0

    baselines = db.query(BaselineResult).all()
    baseline_recovered = sum(b.amount_recovered for b in baselines if b.recovered)
    baseline_rate = (baseline_recovered / total_at_risk * 100) if total_at_risk else 0.0

    # Break down by category
    categories = {}
    for tx in txs:
        cat = "unclassified"
        if tx.classifications:
            cat = tx.classifications[0].root_cause_category.value
        if cat not in categories:
            categories[cat] = {"total": 0, "recovered": 0, "at_risk": 0}
        
        categories[cat]["total"] += 1
        categories[cat]["at_risk"] += float(tx.amount)
        if tx.status == TransactionStatus.recovered:
            categories[cat]["recovered"] += float(tx.amount)

    return {
        "total_at_risk": total_at_risk,
        "total_recovered": total_recovered,
        "recovery_rate": recovery_rate,
        "baseline_recovery_rate": baseline_rate,
        "categories": categories
    }


@router.get("/api/transactions")
def get_transactions(db: Session = Depends(get_db), status: str = None, category: str = None, limit: int = 100, offset: int = 0):
    """Paginated list of transactions."""
    query = db.query(Transaction)
    if status:
        query = query.filter(Transaction.status == status)
    
    # We can filter by category by joining Classification, but for simplicity we fetch all matching status and filter in memory if needed
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
            "retry_count": tx.retry_count
        })
    return result


@router.get("/api/receipts")
def get_all_receipts(db: Session = Depends(get_db), limit: int = 100, offset: int = 0):
    """List of all recovery receipts."""
    receipts_list = db.query(RecoveryReceipt).order_by(RecoveryReceipt.id.desc()).offset(offset).limit(limit).all()
    res = []
    for r in receipts_list:
        tx = db.query(Transaction).filter(Transaction.id == r.transaction_id).first()
        res.append({
            "id": r.id,
            "transaction_id": r.transaction_id,
            "customer_name": tx.customer_name if tx else "Unknown",
            "amount": float(tx.amount) if tx else 0,
            "root_cause": r.root_cause,
            "action_taken": r.action_taken,
            "reasoning": r.reasoning,
            "amount_recovered": float(r.amount_recovered) if r.amount_recovered else None,
            "outcome": r.outcome.value if hasattr(r.outcome, 'value') else str(r.outcome),
            "generated_at": str(r.generated_at)
        })
    return res


@router.get("/api/receipts/{transaction_id}")
def get_receipt(transaction_id: int, db: Session = Depends(get_db)):
    """Full recovery receipt for a given transaction."""
    receipt = db.query(RecoveryReceipt).filter(RecoveryReceipt.transaction_id == transaction_id).first()
    if not receipt:
        return {"error": "Receipt not found"}
    tx = db.query(Transaction).filter(Transaction.id == receipt.transaction_id).first()
    return {
        "id": receipt.id,
        "transaction_id": receipt.transaction_id,
        "customer_name": tx.customer_name if tx else "Unknown",
        "amount": float(tx.amount) if tx else 0,
        "root_cause": receipt.root_cause,
        "action_taken": receipt.action_taken,
        "reasoning": receipt.reasoning,
        "amount_recovered": float(receipt.amount_recovered) if receipt.amount_recovered else None,
        "outcome": receipt.outcome.value if hasattr(receipt.outcome, 'value') else str(receipt.outcome),
        "generated_at": str(receipt.generated_at)
    }


@router.get("/api/review-queue")
def get_review_queue(db: Session = Depends(get_db)):
    """Transactions escalated to human review, with reasoning."""
    txs = db.query(Transaction).filter(Transaction.status == TransactionStatus.escalated).all()
    queue = []
    for tx in txs:
        decision = tx.decisions[0] if tx.decisions else None
        classification = tx.classifications[0] if tx.classifications else None
        queue.append({
            "transaction_id": tx.id,
            "customer_name": tx.customer_name,
            "amount": float(tx.amount),
            "failure_reason": tx.failure_reason,
            "category": classification.root_cause_category.value if classification else "fraud_false_positive",
            "confidence": classification.confidence if classification else 0.1,
            "decision_reasoning": decision.reasoning if decision else "No reasoning available",
        })
    return queue


@router.post("/api/simulate-failure")
def simulate_failure():
    """Deliberately injects a failure into the next executor call."""
    executors.INJECT_FAILURE_ONCE = True
    return {"message": "Failure injection armed for next execution."}


async def _run_batch_pipeline(db: Session):
    """
    Background task to run the full pipeline end-to-end and broadcast events.
    """
    from datetime import datetime
    txs = db.query(Transaction).filter(
        Transaction.status.in_([TransactionStatus.failed, TransactionStatus.recovering])
    ).all()
    
    for tx in txs:
        time_str = datetime.now().strftime("%H:%M:%S")
        # Phase 3: Classifier
        c_res = await asyncio.to_thread(classifier.classify_and_persist, tx, db)
        await manager.broadcast({
            "type": "tx_classified",
            "transaction_id": tx.id,
            "customer_name": tx.customer_name,
            "amount": float(tx.amount),
            "failure_reason": tx.failure_reason,
            "category": c_res.root_cause_category.value,
            "confidence": c_res.confidence,
            "timestamp": time_str
        })
        await asyncio.sleep(0.04)
        
        # Phase 4: Decision
        d_res = await asyncio.to_thread(decision_agent.decide_and_persist, tx, c_res, db)
        await manager.broadcast({
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
            "timestamp": time_str
        })
        await asyncio.sleep(0.04)
        
        # Phase 5 & 6: Executor & Compliance
        decision_record = d_res
        db.flush()
        
        action_log = await asyncio.to_thread(
            executors.execute_decision, tx, decision_record, db, category=c_res.root_cause_category
        )
        
        # If simulated failure occurred, simulate automated retry and recovery
        if not action_log.success and "SIMULATED FAILURE" in (action_log.error_message or ""):
            # Broadcast the detected issue / failure
            await manager.broadcast({
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
                "timestamp": time_str
            })
            await asyncio.sleep(0.2)
            
            # Execute automated retry
            tx.status = TransactionStatus.recovering
            retry_log = await asyncio.to_thread(
                executors.execute_decision, tx, decision_record, db, category=c_res.root_cause_category
            )
            time_str = datetime.now().strftime("%H:%M:%S")
            
            if tx.status in (TransactionStatus.recovered, TransactionStatus.failed, TransactionStatus.escalated, TransactionStatus.suppressed, TransactionStatus.exhausted):
                await asyncio.to_thread(receipts.generate_receipt, tx, db)
                db.commit()
                
            await manager.broadcast({
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
                "timestamp": time_str
            })
            await asyncio.sleep(0.08)
            continue

        # Normal execution completion
        receipt = None
        if tx.status in (TransactionStatus.recovered, TransactionStatus.failed, TransactionStatus.escalated, TransactionStatus.suppressed, TransactionStatus.exhausted):
            receipt = await asyncio.to_thread(receipts.generate_receipt, tx, db)
            db.commit()
            
        await manager.broadcast({
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
            "timestamp": time_str
        })
        
        await asyncio.sleep(0.06)


@router.post("/api/run-batch")
def run_batch(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Triggers the full pipeline run on demand (useful for live demo)."""
    # Clean up state for rerun
    from app.models.models import Classification, Decision
    db.query(ActionLog).delete()
    db.query(RecoveryReceipt).delete()
    db.query(Decision).delete()
    db.query(Classification).delete()
    db.query(Transaction).update({"status": TransactionStatus.failed, "retry_count": 0})
    db.commit()
    
    background_tasks.add_task(_run_batch_pipeline, db)
    return {"message": "Batch pipeline started in background."}
