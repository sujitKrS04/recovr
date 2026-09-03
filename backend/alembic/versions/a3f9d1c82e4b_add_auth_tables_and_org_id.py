"""add_auth_tables_and_org_id

Revision ID: a3f9d1c82e4b
Revises: 7cf15b326321
Create Date: 2026-09-03

Adds:
  - organizations table
  - users table (with UserRole enum)
  - refresh_tokens table
  - transactions.org_id FK column (nullable — existing rows are preserved)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum


revision: str = "a3f9d1c82e4b"
down_revision: Union[str, None] = "7cf15b326321"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Declare the PG enum without auto-create so we control creation explicitly
user_role = PgEnum("admin", "analyst", "viewer", name="user_role", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Create user_role enum type via raw SQL (idempotent) ─────────────
    bind.execute(sa.text(
        "CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'viewer')"
    ))

    # ── 2. organizations ────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    # ── 3. users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(length=256), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_org_id"), "users", ["org_id"], unique=False)

    # ── 4. refresh_tokens ───────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("hashed_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_jti"), "refresh_tokens", ["jti"], unique=True)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)
    op.create_index(
        "ix_refresh_tokens_user_id_revoked",
        "refresh_tokens", ["user_id", "revoked"], unique=False,
    )

    # ── 5. transactions.org_id FK (nullable — existing rows unaffected) ────
    op.add_column(
        "transactions",
        sa.Column("org_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_org_id",
        "transactions", "organizations",
        ["org_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_transactions_org_id"), "transactions", ["org_id"], unique=False)

    # ── 6. transaction_status — add 'suppressed' if the enum lacks it ──────
    bind.execute(sa.text(
        "ALTER TYPE transaction_status ADD VALUE IF NOT EXISTS 'suppressed'"
    ))


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_org_id"), table_name="transactions")
    op.drop_constraint("fk_transactions_org_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "org_id")

    op.drop_index("ix_refresh_tokens_user_id_revoked", table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_jti"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index(op.f("ix_users_org_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_table("organizations")

    op.execute(sa.text("DROP TYPE IF EXISTS user_role CASCADE"))
