"""Knowledge Document model for RAG document ingestion and retrieval."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeDocument(SQLModel, table=True):
    """Knowledge base chunk/document stored in PostgreSQL for grounded enterprise RAG."""

    __tablename__ = "knowledge_documents"

    doc_id: str = Field(primary_key=True, index=True)
    title: str = Field(index=True)
    category: str = Field(default="FAQ", index=True)  # FAQ, Policy, Product Manual, Troubleshooting
    content: str
    source: str = Field(default="Internal Knowledge Base")
    created_at: datetime = Field(default_factory=_get_utc_now)
