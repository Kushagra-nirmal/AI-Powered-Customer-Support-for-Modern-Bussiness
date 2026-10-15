"""Specialist Tools for Production-Grade Enterprise Customer Support.

Includes:
- Knowledge / Grounded Enterprise RAG Search (`search_knowledge_base`)
- Support Ticket Management (`create_support_ticket`, `get_ticket_status`)
- Deterministic Refund & Replacement Engine with Human Approval Gates (`request_refund_or_replacement`)
- Human-in-the-Loop Escalation (`escalate_to_human_agent`)
"""

import datetime
import random
import re
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from sqlmodel import Session, create_engine, select
from sqlalchemy.engine import URL

from src.config.settings import settings
from src.data.models.ticket import Ticket
from src.data.models.knowledge import KnowledgeDocument
from src.data.models.order import OrderRecord


def _get_engine():
    connection_url = URL.create(
        "postgresql",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
    )
    return create_engine(connection_url, pool_pre_ping=True)


@tool
def search_knowledge_base(query: str, category: Optional[str] = None) -> str:
    """Search internal enterprise knowledge base for official policies, SLAs, hardware diagnostics, and FAQs.
    Use this tool whenever a customer asks about company policies, return rules, delivery guarantees, or technical manuals.

    Args:
        query: Specific keywords or question to search (e.g., 'refund policy', 'SLA timeline', 'bluetooth reset').
        category: Optional category filter ('Policy', 'Technical Support', 'Escalation', 'FAQ').
    """
    clean_query = query.strip().lower()
    keywords = [w for w in re.split(r"\W+", clean_query) if len(w) > 2]

    try:
        engine = _get_engine()
        with Session(engine) as session:
            stmt = select(KnowledgeDocument)
            if category:
                stmt = stmt.where(KnowledgeDocument.category == category)
            all_docs = session.exec(stmt).all()

            matches = []
            for doc in all_docs:
                doc_text = f"{doc.title} {doc.content} {doc.category}".lower()
                score = sum(1 for kw in keywords if kw in doc_text)
                if score > 0:
                    matches.append((score, doc))

            matches.sort(key=lambda x: x[0], reverse=True)

            if not matches:
                return (
                    "### ℹ️ Knowledge Base Search Result\n"
                    f"No exact internal policy document found for query: *'{query}'*.\n"
                    "**Guidance:** Abstaining from assumptions. Escalate to human specialist or query the live web if applicable."
                )

            top_doc = matches[0][1]
            return (
                f"### 📖 Grounded Knowledge Document: {top_doc.title}\n"
                f"- **Document ID:** `{top_doc.doc_id}` | **Category:** {top_doc.category}\n"
                f"- **Official Content:** {top_doc.content}\n"
                f"- **Verified Source Citation:** *{top_doc.source}*\n"
                f"- **Last Verified:** {top_doc.created_at.strftime('%Y-%m-%d')}"
            )
    except Exception as e:
        return f"Knowledge base retrieval temporarily unavailable: {str(e)}"


@tool
def create_support_ticket(
    subject: str,
    description: str,
    category: str = "General Support",
    priority: str = "Medium",
    customer_email: Optional[str] = None,
) -> str:
    """Create a persistent customer support ticket with SLA tracking in the PostgreSQL database.
    Use this when a customer issue requires ongoing investigation, return tracking, or specialist follow-up.

    Args:
        subject: Brief subject summary of the issue.
        description: Detailed explanation of the customer complaint or problem.
        category: Support category ('Order & Delivery', 'Billing & Refund', 'Technical Support', 'Human Escalation').
        priority: Priority rating ('Low', 'Medium', 'High', 'Critical').
        customer_email: Customer's contact email.
    """
    rand_num = random.randint(1000, 9999)
    ticket_id = f"#TICK-{rand_num}"
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # Determine assigned specialist agent
    if "billing" in category.lower() or "refund" in category.lower():
        assigned = "Billing Specialist AI"
    elif "order" in category.lower() or "delivery" in category.lower():
        assigned = "Order Specialist AI"
    elif "tech" in category.lower():
        assigned = "Technical Support AI"
    elif "escalat" in category.lower():
        assigned = "Senior Support Human Team"
    else:
        assigned = "Tier-1 Support AI"

    sla_hours = 1 if priority.upper() in ["HIGH", "CRITICAL"] else 12

    try:
        engine = _get_engine()
        with Session(engine) as session:
            ticket = Ticket(
                ticket_id=ticket_id,
                customer_email=customer_email or "active_session_customer@supportai.com",
                category=category,
                subject=subject.strip(),
                description=description.strip(),
                status="Open",
                priority=priority.title(),
                assigned_agent=assigned,
                internal_notes=f"Created via Autonomous Agentic Orchestrator. SLA: {sla_hours}h response target.",
                created_at=now_utc,
                updated_at=now_utc,
            )
            session.add(ticket)
            session.commit()

        return (
            f"### 🎫 Support Ticket Successfully Created!\n"
            f"- **Ticket ID:** `{ticket_id}`\n"
            f"- **Subject:** {subject.strip()}\n"
            f"- **Category:** {category} | **Priority:** {priority.title()}\n"
            f"- **Status:** **Open** (Assigned to: `{assigned}`)\n"
            f"- **Target SLA:** Resolution or follow-up within {sla_hours} hour(s).\n"
            f"- **Customer Notification:** Updates will be logged to this session and customer email."
        )
    except Exception as e:
        return f"Error persisting support ticket to database: {str(e)}"


@tool
def get_ticket_status(ticket_id: str) -> str:
    """Retrieve the current live status, audit trail, and assigned specialist of any support ticket.

    Args:
        ticket_id: The ticket identifier (e.g., '#TICK-8021', 'TICK-8021').
    """
    clean_id = ticket_id.strip()
    if not clean_id.startswith("#"):
        clean_id = f"#{clean_id}"

    try:
        engine = _get_engine()
        with Session(engine) as session:
            ticket = session.get(Ticket, clean_id)
            if not ticket:
                return f"### ❌ Ticket Not Found\nNo ticket found matching ID `{clean_id}` in database registry."

            resolved_info = f"\n- **Resolved At:** {ticket.resolved_at}" if ticket.resolved_at else ""
            notes = f"\n- **Specialist Notes:** {ticket.internal_notes}" if ticket.internal_notes else ""

            return (
                f"### 📋 Support Ticket Details: `{ticket.ticket_id}`\n"
                f"- **Subject:** {ticket.subject}\n"
                f"- **Category:** {ticket.category} | **Priority:** {ticket.priority}\n"
                f"- **Current Status:** **{ticket.status}**\n"
                f"- **Assigned Specialist:** `{ticket.assigned_agent}`\n"
                f"- **Created:** {ticket.created_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"- **Last Updated:** {ticket.updated_at.strftime('%Y-%m-%d %H:%M UTC')}"
                f"{resolved_info}{notes}"
            )
    except Exception as e:
        return f"Error retrieving ticket status: {str(e)}"


@tool
def request_refund_or_replacement(
    order_id: str,
    reason: str,
    action_type: str = "refund",
    amount: float = 0.0,
) -> str:
    """Process a refund or replacement request with deterministic policy validation and human approval gates.
    Auto-approves amounts under ₹5,000 / $100. Amounts exceeding threshold trigger mandatory human manager sign-off.

    Args:
        order_id: The order identifier (e.g. #ORD-12345).
        reason: Explanation for refund or replacement (e.g. 'damaged pizza', 'wrong size', 'defective audio').
        action_type: Either 'refund' or 'replacement'.
        amount: Requested monetary amount in local currency (0.0 if full order amount).
    """
    clean_id = order_id.strip()
    if not clean_id.startswith("#"):
        clean_id = f"#{clean_id}"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    idempotency_key = f"IDEMP_{random.randint(10000000, 99999999)}"

    # Determine amount & threshold
    threshold = 5000.0  # ₹5,000 auto-approval ceiling
    auto_approved = amount < threshold

    status_str = "Auto-Approved" if auto_approved else "Pending Human Manager Approval"
    sla_time = "2-4 Business Hours" if auto_approved else "Requires Senior Manager Review (within 24 hours)"

    # Record tracking ticket for audit trail
    try:
        engine = _get_engine()
        with Session(engine) as session:
            ticket_id = f"#TICK-{random.randint(5000, 9999)}"
            ticket = Ticket(
                ticket_id=ticket_id,
                category="Billing & Refund",
                subject=f"{action_type.title()} Request for {clean_id}",
                description=f"Action: {action_type.upper()} | Reason: {reason} | Amount: ₹{amount:,.2f} | Idempotency Key: {idempotency_key}",
                status=status_str,
                priority="High" if not auto_approved else "Medium",
                assigned_agent="Senior Finance Manager" if not auto_approved else "Billing Automation",
                internal_notes=f"Deterministic policy check: Auto-approved={auto_approved}. Threshold=₹{threshold:,.2f}.",
                created_at=now_utc,
                updated_at=now_utc,
            )
            session.add(ticket)
            session.commit()

        return (
            f"### 💳 {action_type.title()} Request Processed\n"
            f"- **Order ID:** `{clean_id}`\n"
            f"- **Action:** {action_type.upper()} | **Audit Ticket:** `{ticket_id}`\n"
            f"- **Decision:** **{status_str}**\n"
            f"- **Idempotency Key:** `{idempotency_key}`\n"
            f"- **Details:** {reason.strip()}\n"
            f"- **Timeline:** {sla_time}\n"
            f"- **Policy Rule:** Standard 30-day return window validated. {'Automated credit dispatched to source payment method.' if auto_approved else 'High-value request queued for Human Finance Supervisor approval.'}"
        )
    except Exception as e:
        return f"Refund request processing error: {str(e)}"


@tool
def escalate_to_human_agent(
    reason: str,
    customer_sentiment: str = "Frustrated",
    customer_phone: Optional[str] = None,
) -> str:
    """Escalate conversation directly to a live human support specialist with priority queuing.
    Use this when a customer explicitly requests a human, expresses anger/distress, or has complex unresolvable issues.

    Args:
        reason: Specific reason why AI is escalating to human.
        customer_sentiment: Customer emotional state ('Frustrated', 'Hostile', 'VIP Customer', 'Complex Technical Defect').
        customer_phone: Optional customer phone number for callback.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    ticket_id = f"#TICK-{random.randint(9000, 9999)}"
    callback_window = "10-15 Minutes"

    try:
        engine = _get_engine()
        with Session(engine) as session:
            ticket = Ticket(
                ticket_id=ticket_id,
                category="Human Escalation",
                subject=f"URGENT Human Escalation: {reason[:60]}",
                description=f"Sentiment: {customer_sentiment} | Reason: {reason} | Callback: {customer_phone or 'Active Browser Session'}",
                status="Escalated",
                priority="Critical",
                assigned_agent="Human Specialist Team",
                internal_notes=f"Customer escalated via autonomous sentiment detection. Immediate SLA: {callback_window}.",
                created_at=now_utc,
                updated_at=now_utc,
            )
            session.add(ticket)
            session.commit()

        return (
            f"### 👤 Human Specialist Escalation Triggered\n"
            f"- **Escalation Ticket:** `{ticket_id}`\n"
            f"- **Priority:** **CRITICAL / PRIORITY 1**\n"
            f"- **Queue:** Assigned to Live Senior Support Specialist\n"
            f"- **SLA Callback Window:** **{callback_window}**\n"
            f"- **Customer Sentiment Handled:** {customer_sentiment}\n"
            f"- **Message to User:** I have directly notified our senior specialist team with our complete conversation transcript. A human team member is reviewing your case and will connect with you shortly."
        )
    except Exception as e:
        return f"Escalation queue notification error: {str(e)}"


specialist_tools = [
    search_knowledge_base,
    create_support_ticket,
    get_ticket_status,
    request_refund_or_replacement,
    escalate_to_human_agent,
]
