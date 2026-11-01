"""Ticket management endpoints for customer support and admin dashboard."""

import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from src.config.settings import settings
from src.data.db_manager import db_manager
from src.data.models.ticket import Ticket
from src.data.models.knowledge import KnowledgeDocument
from src.system.logs import logger

router = APIRouter()


def _get_engine():
    """Return shared pooled database engine."""
    return db_manager.engine


class TicketCreateRequest(BaseModel):
    subject: str
    description: str
    category: Optional[str] = "General Support"
    priority: Optional[str] = "Medium"
    customer_email: Optional[str] = None


class TicketUpdateRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_agent: Optional[str] = None
    internal_notes: Optional[str] = None
    resolution_notes: Optional[str] = None


@router.get("", response_model=List[Ticket])
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status (e.g. Open, In Progress, Pending Approval, Resolved)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
):
    """List customer support tickets with optional filtering."""
    try:
        engine = _get_engine()
        with Session(engine) as session:
            stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(limit)
            if status:
                stmt = stmt.where(Ticket.status == status)
            if category:
                stmt = stmt.where(Ticket.category == category)
            tickets = session.exec(stmt).all()
            return list(tickets)
    except Exception as e:
        logger.error("list_tickets_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch tickets: {str(e)}")


@router.post("", response_model=Ticket)
async def create_ticket(req: TicketCreateRequest):
    """Create a new support ticket."""
    import random
    ts_part = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000) % 10000000
    ticket_id = f"#TICK-{ts_part}-{random.randint(100, 999)}"
    now = datetime.datetime.now(datetime.timezone.utc)

    try:
        engine = _get_engine()
        with Session(engine) as session:
            ticket = Ticket(
                ticket_id=ticket_id,
                customer_email=req.customer_email or "customer@supportai.com",
                category=req.category or "General Support",
                subject=req.subject.strip(),
                description=req.description.strip(),
                status="Open",
                priority=req.priority or "Medium",
                assigned_agent="Tier-1 Support AI",
                internal_notes="Created via Ticket API",
                created_at=now,
                updated_at=now,
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket
    except Exception as e:
        logger.error("create_ticket_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")


@router.get("/knowledge/documents", response_model=List[KnowledgeDocument])
async def list_knowledge_documents():
    """List enterprise knowledge base documents stored in PostgreSQL."""
    try:
        engine = _get_engine()
        with Session(engine) as session:
            docs = session.exec(select(KnowledgeDocument).order_by(KnowledgeDocument.doc_id)).all()
            return list(docs)
    except Exception as e:
        logger.error("list_knowledge_documents_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticket_id}", response_model=Ticket)
async def get_ticket(ticket_id: str):
    """Retrieve details for a single ticket by ID."""
    clean_id = ticket_id.strip()
    if not clean_id.startswith("#"):
        clean_id = f"#{clean_id}"

    try:
        engine = _get_engine()
        with Session(engine) as session:
            ticket = session.get(Ticket, clean_id)
            if not ticket:
                raise HTTPException(status_code=404, detail=f"Ticket {clean_id} not found")
            return ticket
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_ticket_failed", ticket_id=ticket_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ticket_id}", response_model=Ticket)
async def update_ticket(ticket_id: str, req: TicketUpdateRequest):
    """Update ticket status, assignment, or notes."""
    clean_id = ticket_id.strip()
    if not clean_id.startswith("#"):
        clean_id = f"#{clean_id}"

    try:
        engine = _get_engine()
        with Session(engine) as session:
            ticket = session.get(Ticket, clean_id)
            if not ticket:
                raise HTTPException(status_code=404, detail=f"Ticket {clean_id} not found")

            now = datetime.datetime.now(datetime.timezone.utc)
            if req.status:
                ticket.status = req.status
                if req.status.lower() in ["resolved", "closed"]:
                    ticket.resolved_at = now
            if req.priority:
                ticket.priority = req.priority
            if req.assigned_agent:
                ticket.assigned_agent = req.assigned_agent
            if req.internal_notes:
                ticket.internal_notes = f"{ticket.internal_notes}\n[{now.strftime('%H:%M')}] {req.internal_notes}".strip()
            if req.resolution_notes:
                ticket.resolution_notes = req.resolution_notes
            ticket.updated_at = now

            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_ticket_failed", ticket_id=ticket_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticket_id}/approve", response_model=Ticket)
async def approve_ticket_action(ticket_id: str):
    """Manager approval action for pending refund or high-value replacements."""
    clean_id = ticket_id.strip()
    if not clean_id.startswith("#"):
        clean_id = f"#{clean_id}"

    try:
        engine = _get_engine()
        with Session(engine) as session:
            ticket = session.get(Ticket, clean_id)
            if not ticket:
                raise HTTPException(status_code=404, detail=f"Ticket {clean_id} not found")

            now = datetime.datetime.now(datetime.timezone.utc)
            ticket.status = "Approved & Executed"
            ticket.resolution_notes = "Approved by Senior Support Manager. Financial credit issued."
            ticket.resolved_at = now
            ticket.updated_at = now
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket
    except HTTPException:
        raise
    except Exception as e:
        logger.error("approve_ticket_failed", ticket_id=ticket_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticket_id}/reject", response_model=Ticket)
async def reject_ticket_action(ticket_id: str):
    """Manager rejection action for pending refund or ineligible replacements."""
    clean_id = ticket_id.strip()
    if not clean_id.startswith("#"):
        clean_id = f"#{clean_id}"

    try:
        engine = _get_engine()
        with Session(engine) as session:
            ticket = session.get(Ticket, clean_id)
            if not ticket:
                raise HTTPException(status_code=404, detail=f"Ticket {clean_id} not found")

            now = datetime.datetime.now(datetime.timezone.utc)
            ticket.status = "Rejected"
            ticket.resolution_notes = "Request declined per terms of service or return window expiration."
            ticket.updated_at = now
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket
    except HTTPException:
        raise
    except Exception as e:
        logger.error("reject_ticket_failed", ticket_id=ticket_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
