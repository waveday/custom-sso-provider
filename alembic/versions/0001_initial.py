"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sub", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("given_name", sa.String(length=255), nullable=False),
        sa.Column("family_name", sa.String(length=255), nullable=False),
        sa.Column("picture", sa.String(length=1024), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_sub"), "users", ["sub"], unique=True)

    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("client_secret_hash", sa.String(length=255), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=False),
        sa.Column("redirect_uris", sa.Text(), nullable=False),
        sa.Column("is_confidential", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_oauth_clients_client_id"), "oauth_clients", ["client_id"], unique=True)

    op.create_table(
        "signing_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kid", sa.String(length=64), nullable=False),
        sa.Column("private_jwk", sa.Text(), nullable=False),
        sa.Column("public_jwk", sa.Text(), nullable=False),
        sa.Column("algorithm", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_signing_keys_kid"), "signing_keys", ["kid"], unique=True)

    op.create_table(
        "auth_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("redirect_uri", sa.String(length=1024), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("code_challenge", sa.String(length=255), nullable=False),
        sa.Column("code_challenge_method", sa.String(length=16), nullable=False),
        sa.Column("nonce", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["oauth_clients.client_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_auth_codes_code"),
    )
    op.create_index(op.f("ix_auth_codes_client_id"), "auth_codes", ["client_id"], unique=False)
    op.create_index(op.f("ix_auth_codes_code"), "auth_codes", ["code"], unique=True)
    op.create_index(op.f("ix_auth_codes_user_id"), "auth_codes", ["user_id"], unique=False)

    op.create_table(
        "access_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["oauth_clients.client_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_access_tokens_client_id"), "access_tokens", ["client_id"], unique=False)
    op.create_index(op.f("ix_access_tokens_jti"), "access_tokens", ["jti"], unique=True)
    op.create_index(op.f("ix_access_tokens_user_id"), "access_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_access_tokens_user_id"), table_name="access_tokens")
    op.drop_index(op.f("ix_access_tokens_jti"), table_name="access_tokens")
    op.drop_index(op.f("ix_access_tokens_client_id"), table_name="access_tokens")
    op.drop_table("access_tokens")
    op.drop_index(op.f("ix_auth_codes_user_id"), table_name="auth_codes")
    op.drop_index(op.f("ix_auth_codes_code"), table_name="auth_codes")
    op.drop_index(op.f("ix_auth_codes_client_id"), table_name="auth_codes")
    op.drop_table("auth_codes")
    op.drop_index(op.f("ix_signing_keys_kid"), table_name="signing_keys")
    op.drop_table("signing_keys")
    op.drop_index(op.f("ix_oauth_clients_client_id"), table_name="oauth_clients")
    op.drop_table("oauth_clients")
    op.drop_index(op.f("ix_users_sub"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
