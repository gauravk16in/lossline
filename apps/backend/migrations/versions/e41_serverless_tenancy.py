"""serverless tenancy, processing state, credentials, and rate limits

Revision ID: e41
Revises: d31
"""
from alembic import op
import sqlalchemy as sa

revision = "e41"
down_revision = "d31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clerk_organization_id", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_organizations_clerk_organization_id", "organizations", ["clerk_organization_id"], unique=True)
    with op.batch_alter_table("restaurants") as batch:
        batch.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_restaurants_organization", "organizations", ["organization_id"], ["id"])
        batch.create_index("ix_restaurants_organization_id", ["organization_id"])
    op.create_table("integration_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_prefix", sa.String(), nullable=False, unique=True),
        sa.Column("secret_hash", sa.String(), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("allowed_outlet_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_integration_credentials_public_prefix", "integration_credentials", ["public_prefix"], unique=True)
    op.create_index("ix_integration_credentials_organization_id", "integration_credentials", ["organization_id"])
    op.create_table("rate_limit_buckets",
        sa.Column("bucket_key", sa.String(), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False))
    op.add_column("events", sa.Column("processing_status", sa.String(), server_default="PENDING", nullable=False))
    op.add_column("events", sa.Column("processing_attempt_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("events", sa.Column("processing_last_error", sa.String(), nullable=True))
    op.add_column("events", sa.Column("processing_result", sa.JSON(), nullable=True))
    op.create_index("ix_events_processing_status", "events", ["processing_status"])


def downgrade() -> None:
    op.drop_index("ix_events_processing_status", table_name="events")
    for column in ("processing_result", "processing_last_error", "processing_attempt_count", "processing_status"):
        op.drop_column("events", column)
    op.drop_table("rate_limit_buckets")
    op.drop_index("ix_integration_credentials_organization_id", table_name="integration_credentials")
    op.drop_index("ix_integration_credentials_public_prefix", table_name="integration_credentials")
    op.drop_table("integration_credentials")
    with op.batch_alter_table("restaurants") as batch:
        batch.drop_index("ix_restaurants_organization_id")
        batch.drop_constraint("fk_restaurants_organization", type_="foreignkey")
        batch.drop_column("organization_id")
    op.drop_index("ix_organizations_clerk_organization_id", table_name="organizations")
    op.drop_table("organizations")
