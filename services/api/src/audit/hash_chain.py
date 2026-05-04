"""Hash chain implementation for tamper-proof audit logs.

Each audit log record includes a SHA-256 hash computed from:
  - timestamp
  - user_id
  - tenant_id
  - action
  - details
  - previous record's hash

This creates a chain where altering any record breaks the chain.
"""

import hashlib
import json
from datetime import datetime
from typing import Optional


def compute_record_hash(
    created_at: str,
    user_id: Optional[str],
    tenant_id: Optional[str],
    category: str,
    action: str,
    resource_type: Optional[str],
    resource_id: Optional[str],
    details: dict,
    result: str,
    previous_hash: Optional[str],
) -> str:
    """Compute SHA-256 hash for an audit log record."""
    payload = json.dumps(
        {
            "created_at": created_at,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "category": category,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "result": result,
            "previous_hash": previous_hash or "",
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_chain(records: list[dict]) -> tuple[bool, Optional[int]]:
    """Verify the integrity of an audit log hash chain.

    Returns:
        (is_valid, first_broken_index): True if chain is intact,
        otherwise returns the index of the first broken record.
    """
    for i, record in enumerate(records):
        expected = compute_record_hash(
            created_at=record["created_at"],
            user_id=record.get("user_id"),
            tenant_id=record.get("tenant_id"),
            category=record["category"],
            action=record["action"],
            resource_type=record.get("resource_type"),
            resource_id=record.get("resource_id"),
            details=record.get("details", {}),
            result=record.get("result", "success"),
            previous_hash=record.get("previous_hash"),
        )
        if expected != record.get("record_hash"):
            return False, i

        # Verify chain linkage
        if i > 0 and record.get("previous_hash") != records[i - 1].get("record_hash"):
            return False, i

    return True, None
