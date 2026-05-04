"""Audit log hash chain tests."""

from src.audit.hash_chain import compute_record_hash, verify_chain


def _make_record(idx: int, previous_hash: str | None = None) -> dict:
    record_hash = compute_record_hash(
        created_at=f"2024-01-01T00:00:{idx:02d}Z",
        user_id="user-1",
        tenant_id="tenant-1",
        category="auth",
        action="login",
        resource_type=None,
        resource_id=None,
        details={},
        result="success",
        previous_hash=previous_hash,
    )
    return {
        "created_at": f"2024-01-01T00:00:{idx:02d}Z",
        "user_id": "user-1",
        "tenant_id": "tenant-1",
        "category": "auth",
        "action": "login",
        "resource_type": None,
        "resource_id": None,
        "details": {},
        "result": "success",
        "previous_hash": previous_hash,
        "record_hash": record_hash,
    }


def test_valid_chain():
    records = []
    for i in range(5):
        prev_hash = records[-1]["record_hash"] if records else None
        records.append(_make_record(i, prev_hash))

    is_valid, broken_at = verify_chain(records)
    assert is_valid is True
    assert broken_at is None


def test_broken_chain():
    records = []
    for i in range(5):
        prev_hash = records[-1]["record_hash"] if records else None
        records.append(_make_record(i, prev_hash))

    # Tamper with record 2
    records[2]["record_hash"] = "tampered_hash"

    is_valid, broken_at = verify_chain(records)
    assert is_valid is False
    assert broken_at == 2


def test_empty_chain():
    is_valid, broken_at = verify_chain([])
    assert is_valid is True
    assert broken_at is None
