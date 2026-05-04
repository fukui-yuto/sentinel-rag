"""RBAC (Role-Based Access Control) using Casbin policy model."""

# Casbin model definition (RBAC)
CASBIN_MODEL = """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
"""

# Default policy rules
DEFAULT_POLICIES = [
    # system_admin: full access
    ("system_admin", "tenants", "read"),
    ("system_admin", "tenants", "write"),
    ("system_admin", "tenants", "delete"),
    ("system_admin", "users", "read"),
    ("system_admin", "users", "write"),
    ("system_admin", "users", "delete"),
    ("system_admin", "documents", "read"),
    ("system_admin", "documents", "write"),
    ("system_admin", "documents", "delete"),
    ("system_admin", "qa", "execute"),
    ("system_admin", "audit_logs", "read"),
    ("system_admin", "providers", "read"),
    ("system_admin", "providers", "write"),
    ("system_admin", "system", "admin"),

    # tenant_admin: tenant-scoped management
    ("tenant_admin", "users", "read"),
    ("tenant_admin", "users", "write"),
    ("tenant_admin", "documents", "read"),
    ("tenant_admin", "documents", "write"),
    ("tenant_admin", "documents", "delete"),
    ("tenant_admin", "qa", "execute"),
    ("tenant_admin", "audit_logs", "read"),
    ("tenant_admin", "providers", "read"),

    # content_manager: document management
    ("content_manager", "documents", "read"),
    ("content_manager", "documents", "write"),
    ("content_manager", "documents", "delete"),
    ("content_manager", "qa", "execute"),

    # user: basic access
    ("user", "documents", "read"),
    ("user", "documents", "write"),
    ("user", "qa", "execute"),

    # auditor: audit log access only
    ("auditor", "audit_logs", "read"),
    ("auditor", "documents", "read"),
    ("auditor", "qa", "execute"),

    # read_only: QA only
    ("read_only", "documents", "read"),
    ("read_only", "qa", "execute"),
]


def check_permission(role: str, resource: str, action: str) -> bool:
    """Check if a role has permission for a resource action.

    This is a simplified in-memory check. For production with complex policies,
    integrate Casbin with the SQLAlchemy adapter for database-backed policies.
    """
    return (role, resource, action) in _POLICY_SET


_POLICY_SET = {(sub, obj, act) for sub, obj, act in DEFAULT_POLICIES}
