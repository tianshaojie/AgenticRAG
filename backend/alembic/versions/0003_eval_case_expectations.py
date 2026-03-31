"""extend eval_cases for golden regression expectations

Revision ID: 0003_eval_case_expectations
Revises: 0002_content_text
Create Date: 2026-03-31 09:50:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_eval_case_expectations"
down_revision = "0002_content_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_cases",
        sa.Column(
            "expected_document_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "eval_cases",
        sa.Column(
            "expected_chunk_indices",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "eval_cases",
        sa.Column(
            "expected_abstain",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "eval_cases",
        sa.Column(
            "citation_constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("eval_cases", sa.Column("difficulty", sa.String(length=32), nullable=True))
    op.add_column("eval_cases", sa.Column("scenario_type", sa.String(length=64), nullable=True))
    op.create_index("ix_eval_cases_dataset_name", "eval_cases", ["dataset", "name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_eval_cases_dataset_name", table_name="eval_cases")
    op.drop_column("eval_cases", "scenario_type")
    op.drop_column("eval_cases", "difficulty")
    op.drop_column("eval_cases", "citation_constraints")
    op.drop_column("eval_cases", "expected_abstain")
    op.drop_column("eval_cases", "expected_chunk_indices")
    op.drop_column("eval_cases", "expected_document_keys")
