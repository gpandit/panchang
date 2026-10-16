"""Enable transaction-local row-level security for user-owned data.

The API sets ``app.user_id`` after resolving the JWT subject.  Policies are
intentionally limited to tables that carry a direct user ownership column;
public Panchang/CMS data and operational tables are not tenant tables.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_user_data_rls"
down_revision: str | None = "0004_s2_calendar_overlays"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (table, ownership column).  Keep this list explicit so a newly added table
# cannot silently inherit an overly broad policy.
_OWNED_TABLES = (
    ("user_preferences", "user_id"),
    ("locations", "user_id"),
    ("family_groups", "owner_user_id"),
    ("family_memberships", "user_id"),
    ("vault_refs", "subject_id"),
    ("devices", "user_id"),
    ("legal_acceptances", "user_id"),
    ("notes", "owner_user_id"),
    ("bookmarks", "user_id"),
    ("reminders", "user_id"),
    ("vrat_records", "user_id"),
    ("planner_requests", "user_id"),
    ("calendar_jobs", "user_id"),
    ("subscriptions", "user_id"),
    ("provider_accounts", "user_id"),
)


def _policy_name(table: str) -> str:
    return f"rls_{table}_owner"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table, column in _OWNED_TABLES:
        policy = _policy_name(table)
        # FORCE also applies the policy to the table owner, preventing a
        # privileged application connection from accidentally bypassing RLS.
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
        op.execute(
            f'''CREATE POLICY "{policy}" ON "{table}"
                USING (current_setting('app.user_id', true) = "{column}"::text)
                WITH CHECK (current_setting('app.user_id', true) = "{column}"::text)'''
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table, _column in reversed(_OWNED_TABLES):
        policy = _policy_name(table)
        op.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
