"""Deterministic proposals: retrieved prose is evidence, never authority."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    order_status: Literal["cancelled", "expired", "confirmed", "unknown"]
    payment_status: Literal["paid", "unpaid", "unknown"]
    amount_cents: int = Field(ge=0, le=1_000_000)
    contradictory: bool = False
    retrieved_text: str = Field(default="", max_length=8000)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["flag_refund", "close_no_action", "abstain"]
    reason: str = Field(min_length=1, max_length=500)


def propose(evidence: Evidence) -> Action:
    if (
        evidence.contradictory
        or evidence.order_status == "unknown"
        or evidence.payment_status == "unknown"
    ):
        return Action(kind="abstain", reason="Evidence is incomplete or contradictory.")
    if evidence.payment_status == "paid" and evidence.order_status in {
        "expired",
        "cancelled",
    }:
        return Action(kind="flag_refund", reason="Paid order is no longer fulfillable.")
    return Action(kind="close_no_action", reason="No unmatched payment was observed.")


def action_hash(case_id: str, context_version: int, action: Action) -> str:
    envelope = {
        "schema_version": 1,
        "case_id": case_id,
        "context_version": context_version,
        "action": action.model_dump(),
    }
    return hashlib.sha256(
        json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
