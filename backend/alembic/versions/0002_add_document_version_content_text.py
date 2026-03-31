"""add content_text to document_versions

Revision ID: 0002_content_text
Revises: 0001_initial_schema
Create Date: 2026-03-30 15:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_content_text"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_versions", sa.Column("content_text", sa.Text(), nullable=True))
    op.execute("UPDATE document_versions SET content_text = '' WHERE content_text IS NULL")
    op.alter_column("document_versions", "content_text", nullable=False)


def downgrade() -> None:
    op.drop_column("document_versions", "content_text")
