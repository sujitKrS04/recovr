"""
Root-cause classifier service for Recovr.

Two-stage pipeline:
  1. Rule-based first pass  — handles unambiguous cases (confidence 0.90–0.95)
  2. LLM fallback           — OpenRouter free-tier for anything the rules don't
                              cover with sufficient confidence

Design constraints:
  - Deterministic for known strings (rules always win if confidence ≥ RULE_MIN_CONFIDENCE)
  - LLM results are cached in-memory by failure_reason to avoid re-calling
  - Exponential backoff on 429 / 5xx responses (free tier: ~20 req/min)
  - All results written to the `classifications` table with full reasoning
  - If OPENROUTER_API_KEY is unset, LLM path returns a flagged fallback result
    rather than crashing (safe degradation)
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    Classification,
    ClassifierMethod,
    RootCauseCategory,
    Transaction,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openrouter/auto"          # free-tier auto-router
RULE_MIN_CONFIDENCE = 0.85                    # if rule score < this → LLM fallback
LLM_MAX_RETRIES = 3
LLM_BASE_BACKOFF_S = 4                        # seconds; doubles each attempt
LLM_TIMEOUT_S = 20

# ---------------------------------------------------------------------------
# In-memory LLM result cache (keyed on failure_reason string)
# ---------------------------------------------------------------------------
_llm_cache: dict[str, "ClassificationResult"] = {}
_cache_hits: int = 0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ClassificationResult:
    root_cause_category: RootCauseCategory
    classifier_method: ClassifierMethod
    confidence: float
    reasoning: str


# ---------------------------------------------------------------------------
# Rule-based classifier
# ---------------------------------------------------------------------------

# Each entry: (list_of_patterns, category, confidence)
# Patterns are matched case-insensitively against failure_reason.
# First matching rule wins. Order matters — put most specific first.
_RULES: list[tuple[list[str], RootCauseCategory, float]] = [
    # --- card_declined ---
    (
        [
            r"card declin",
            r"do not honour",
            r"card report",      # "card reported stolen"
            r"card block",
            r"expired card",
            r"card not set",
            r"insufficient credit limit",
        ],
        RootCauseCategory.card_declined,
        0.95,
    ),
    # --- insufficient_funds ---
    (
        [
            r"insufficient fund",
            r"insufficient balance",
            r"debit failed.*insufficient",
            r"balance.*insufficient",
            r"insufficient.*balance",
        ],
        RootCauseCategory.insufficient_funds,
        0.95,
    ),
    # --- gateway_timeout ---
    (
        [
            r"gateway.*timeout",
            r"gateway.*timed out",
            r"gateway request",
            r"payment gateway",
            r"connection to payment",
            r"network timeout",
            r"upstream payment",
            r"timed out",
        ],
        RootCauseCategory.gateway_timeout,
        0.90,
    ),
    # --- bank_downtime ---
    (
        [
            r"issuing bank",
            r"bank.*unavailable",
            r"bank.*maintenance",
            r"core banking",
            r"bank not respond",
            r"bank undergo",
            r"bank server",
            r"scheduled maintenance",
        ],
        RootCauseCategory.bank_downtime,
        0.90,
    ),
    # --- otp_failure ---
    (
        [
            r"otp.*fail",
            r"otp.*expir",
            r"otp not receiv",
            r"incorrect otp",
            r"3d secure",
            r"authentication fail",
        ],
        RootCauseCategory.otp_failure,
        0.95,
    ),
    # NOTE: fraud_false_positive has NO rule — deliberately sent to LLM.
    # Fraud flags require contextual judgment that keyword rules cannot provide.
    # See DECISIONS.md #004.
]


def rule_classify(failure_reason: str) -> Optional[ClassificationResult]:
    """
    Try to classify failure_reason via regex rules.
    Returns ClassificationResult if confident match found, else None.
    """
    text = failure_reason.lower().strip()

    for patterns, category, confidence in _RULES:
        for pattern in patterns:
            if re.search(pattern, text):
                reasoning = (
                    f"Rule match: pattern '{pattern}' matched failure reason. "
                    f"Category '{category.value}' assigned with confidence {confidence}."
                )
                return ClassificationResult(
                    root_cause_category=category,
                    classifier_method=ClassifierMethod.rule,
                    confidence=confidence,
                    reasoning=reasoning,
                )

    return None  # No rule matched → fall through to LLM


# ---------------------------------------------------------------------------
# LLM classifier (OpenRouter)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a payment failure root-cause analyst for an Indian fintech platform.
Classify the given payment failure reason into exactly ONE of these categories:
- card_declined: card blocked, expired, over-limit, or issuer declined without a specific reason
- insufficient_funds: customer account balance too low
- gateway_timeout: payment processor or network timed out
- bank_downtime: issuing bank servers were down or under maintenance
- otp_failure: OTP/2FA verification failed or expired
- fraud_false_positive: transaction incorrectly flagged as fraudulent by a risk/fraud engine

Respond with ONLY valid JSON in this exact schema:
{
  "root_cause_category": "<one of the six values above>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence explaining the classification>"
}"""

_VALID_CATEGORIES = {c.value for c in RootCauseCategory}


def _call_openrouter(failure_reason: str) -> dict:
    """Make a single HTTP call to OpenRouter. Raises on failure."""
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/sujitKrS04/recovr",
        "X-Title": "Recovr - AI Revenue Recovery",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Classify this payment failure reason:\n\n\"{failure_reason}\"",
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,   # Low temp for deterministic classification
        "max_tokens": 150,
    }
    with httpx.Client(timeout=LLM_TIMEOUT_S) as client:
        resp = client.post(OPENROUTER_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


def _parse_llm_response(raw: dict, failure_reason: str) -> ClassificationResult:
    """Parse OpenRouter response into a ClassificationResult. Raises ValueError on bad output."""
    try:
        content = raw["choices"][0]["message"]["content"]
        if content is None:
            raise ValueError("LLM returned None content")
        data = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Malformed LLM response structure: {exc}") from exc

    cat_str = data.get("root_cause_category", "").strip()
    if cat_str not in _VALID_CATEGORIES:
        raise ValueError(
            f"LLM returned unknown category '{cat_str}'. "
            f"Valid: {_VALID_CATEGORIES}"
        )

    confidence = float(data.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))  # clamp

    reasoning = str(data.get("reasoning", "LLM classified this failure reason."))

    return ClassificationResult(
        root_cause_category=RootCauseCategory(cat_str),
        classifier_method=ClassifierMethod.llm,
        confidence=confidence,
        reasoning=reasoning,
    )


def llm_classify(failure_reason: str) -> ClassificationResult:
    """
    Classify via OpenRouter LLM with retry + exponential backoff.
    Falls back to a flagged 'other' result if API is unavailable or key is missing.
    """
    global _cache_hits

    # Cache check
    if failure_reason in _llm_cache:
        _cache_hits += 1
        logger.debug("LLM cache hit for: %s", failure_reason[:60])
        cached = _llm_cache[failure_reason]
        return cached

    # No API key — safe degradation
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY.startswith("your_"):
        logger.warning("OPENROUTER_API_KEY not set — returning degraded result for: %s", failure_reason[:60])
        result = ClassificationResult(
            root_cause_category=RootCauseCategory.other,
            classifier_method=ClassifierMethod.llm,
            confidence=0.10,
            reasoning=(
                "LLM classification skipped: OPENROUTER_API_KEY not configured. "
                "Set the key in .env and re-run to get a real classification."
            ),
        )
        _llm_cache[failure_reason] = result
        return result

    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(LLM_MAX_RETRIES):
        try:
            raw = _call_openrouter(failure_reason)
            result = _parse_llm_response(raw, failure_reason)
            _llm_cache[failure_reason] = result
            logger.info(
                "LLM classified '%s...' → %s (conf=%.2f)",
                failure_reason[:40],
                result.root_cause_category.value,
                result.confidence,
            )
            return result

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                retry_after = int(exc.response.headers.get("retry-after", LLM_BASE_BACKOFF_S * (2 ** attempt)))
                logger.warning("OpenRouter rate limited (429). Waiting %ds before retry %d/%d.", retry_after, attempt + 1, LLM_MAX_RETRIES)
                time.sleep(retry_after)
            elif status >= 500:
                wait = LLM_BASE_BACKOFF_S * (2 ** attempt)
                logger.warning("OpenRouter server error %d. Waiting %ds before retry %d/%d.", status, wait, attempt + 1, LLM_MAX_RETRIES)
                time.sleep(wait)
            else:
                logger.error("OpenRouter HTTP error %d: %s", status, exc.response.text[:200])
                last_exc = exc
                break
            last_exc = exc

        except httpx.TimeoutException as exc:
            wait = LLM_BASE_BACKOFF_S * (2 ** attempt)
            logger.warning("OpenRouter timeout. Waiting %ds before retry %d/%d.", wait, attempt + 1, LLM_MAX_RETRIES)
            time.sleep(wait)
            last_exc = exc

        except ValueError as exc:
            # Bad response structure — don't retry, just log and return degraded
            logger.error("LLM parse error for '%s': %s", failure_reason[:60], exc)
            last_exc = exc
            break

    # All retries exhausted — return degraded result rather than crashing
    logger.error("LLM classification failed after %d attempts for '%s': %s", LLM_MAX_RETRIES, failure_reason[:60], last_exc)
    result = ClassificationResult(
        root_cause_category=RootCauseCategory.other,
        classifier_method=ClassifierMethod.llm,
        confidence=0.10,
        reasoning=f"LLM unavailable after {LLM_MAX_RETRIES} retries: {str(last_exc)[:120]}",
    )
    _llm_cache[failure_reason] = result
    return result


# ---------------------------------------------------------------------------
# Public classify() function
# ---------------------------------------------------------------------------

def classify(failure_reason: str) -> ClassificationResult:
    """
    Classify a failure reason using the two-stage pipeline:
      1. Rule-based (fast, deterministic, confidence 0.90–0.95)
      2. LLM fallback (OpenRouter, with cache + retry)

    Returns a ClassificationResult. Never raises — safe degradation if LLM fails.
    """
    result = rule_classify(failure_reason)
    if result is not None:
        return result
    # Rule had no match — fall back to LLM
    return llm_classify(failure_reason)


# ---------------------------------------------------------------------------
# Batch classify + persist to DB
# ---------------------------------------------------------------------------

def classify_and_persist(tx: Transaction, session: Session) -> Classification:
    """
    Classify a single transaction, persist to classifications table, and return the ORM row.
    Does NOT commit — caller is responsible for commit.
    """
    result = classify(tx.failure_reason or "")

    classification = Classification(
        transaction_id=tx.id,
        root_cause_category=result.root_cause_category,
        classifier_method=result.classifier_method,
        confidence=result.confidence,
        reasoning=result.reasoning,
    )
    session.add(classification)
    return classification


def get_cache_stats() -> dict:
    return {
        "cached_entries": len(_llm_cache),
        "cache_hits": _cache_hits,
    }
