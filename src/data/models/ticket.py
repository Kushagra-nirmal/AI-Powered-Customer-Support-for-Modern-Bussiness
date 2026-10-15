"""Ticket model for persistent customer support ticket lifecycle management."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Ticket(SQLModel, table=True):
    """Customer support ticket entity stored in PostgreSQL."""

    __tablename__ = "tickets"

    ticket_id: str = Field(primary_key=True, index=True)
    user_id: Optional[int] = Field(default=None, index=True)
    customer_email: Optional[str] = Field(default=None, index=True)
    category: str = Field(default="General Support", index=True)
    subject: str
    description: str
    status: str = Field(default="Open", index=True)  # Open, In Progress, Pending Approval, Escalated, Resolved, Closed
    priority: str = Field(default="Medium", index=True)  # Low, Medium, High, Critical
    assigned_agent: str = Field(default="AI Specialist")
    internal_notes: Optional[str] = Field(default="")
    resolution_notes: Optional[str] = Field(default="")
    created_at: datetime = Field(default_factory=_get_utc_now)
    updated_at: datetime = Field(default_factory=_get_utc_now)
    resolved_at: Optional[datetime] = Field(default=None)
