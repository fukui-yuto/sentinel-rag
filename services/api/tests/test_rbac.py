"""RBAC permission tests."""

from src.security.rbac import check_permission


def test_system_admin_full_access():
    assert check_permission("system_admin", "tenants", "read") is True
    assert check_permission("system_admin", "tenants", "write") is True
    assert check_permission("system_admin", "tenants", "delete") is True
    assert check_permission("system_admin", "system", "admin") is True


def test_user_basic_access():
    assert check_permission("user", "documents", "read") is True
    assert check_permission("user", "documents", "write") is True
    assert check_permission("user", "qa", "execute") is True


def test_user_no_admin():
    assert check_permission("user", "tenants", "read") is False
    assert check_permission("user", "audit_logs", "read") is False
    assert check_permission("user", "system", "admin") is False


def test_read_only():
    assert check_permission("read_only", "documents", "read") is True
    assert check_permission("read_only", "qa", "execute") is True
    assert check_permission("read_only", "documents", "write") is False


def test_auditor():
    assert check_permission("auditor", "audit_logs", "read") is True
    assert check_permission("auditor", "documents", "write") is False
