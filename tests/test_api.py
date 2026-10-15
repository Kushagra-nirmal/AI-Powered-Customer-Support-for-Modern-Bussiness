"""Integration and API test suite for the production-grade agentic system."""

import re
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.agent.tools.jarvis_tools import place_order, track_order


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_root_and_api_info_endpoints():
    """Test that root endpoint serves frontend HTML and /api-info returns JSON metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Root serves the responsive Single Page Application HTML
        root_resp = await ac.get("/")
        assert root_resp.status_code == 200
        assert "text/html" in root_resp.headers.get("content-type", "")
        assert "SupportAI" in root_resp.text or "JARVIS" in root_resp.text

        # /api-info serves the JSON metadata
        api_info = await ac.get("/api-info")
        assert api_info.status_code == 200
        data = api_info.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "name" in data


@pytest.mark.anyio
async def test_health_check_endpoint():
    """Test that health check endpoint reports both API and database as healthy."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["components"]["api"] == "healthy"
    assert data["components"]["database"] == "healthy"


@pytest.mark.anyio
async def test_metrics_endpoint():
    """Test that Prometheus metrics endpoint returns scrapeable metrics."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/metrics")
    assert response.status_code == 200
    assert "python_gc_objects_collected_total" in response.text


@pytest.mark.anyio
async def test_tts_audio_streaming_endpoint():
    """Test that authentic Iron Man JARVIS TTS endpoint streams valid audio/mpeg bytes."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        tts_resp = await ac.post(
            "/api/v1/chatbot/tts",
            json={
                "text": "At your service, sir. All Stark Industries defensive systems online.",
                "voice": "en-GB-RyanNeural",
                "rate": "+2%",
                "pitch": "+0Hz"
            }
        )
    assert tts_resp.status_code == 200
    assert "audio/mpeg" in tts_resp.headers.get("content-type", "")
    assert len(tts_resp.content) > 5000, "Audio stream should return valid MPEG bytes"


def test_autonomous_order_and_tracking_tools():
    """Test autonomous order placement, itemized financial calculation, and live tracking telemetry."""
    # 1. Place Order
    placement_result = place_order.invoke({
        "platform": "Domino's",
        "item_name": "Farmhouse Feast Pizza",
        "quantity": 2
    })
    assert "Order Successfully Placed" in placement_result
    assert "Domino'S" in placement_result or "Domino's" in placement_result

    # Extract Order ID
    match = re.search(r"`(#ORD-\d+)`", placement_result)
    assert match is not None, "Order ID should be formatted as `#ORD-XXXXX`"
    order_id = match.group(1)

    # 2. Track Order
    tracking_result = track_order.invoke({
        "order_id": order_id,
        "platform": "Domino's"
    })
    assert order_id in tracking_result
    assert "Farmhouse Feast Pizza" in tracking_result
    assert "Assigned Courier" in tracking_result or "Live Delivery Milestones" in tracking_result


@pytest.mark.anyio
async def test_auth_workflow_and_sessions():
    """Test complete auth lifecycle: register, login, create session, update session, delete session."""
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register
        reg_resp = await ac.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": password},
        )
        assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
        reg_data = reg_resp.json()
        assert reg_data["email"] == unique_email
        user_token = reg_data["token"]["access_token"]
        assert user_token

        # 2. Login
        login_resp = await ac.post(
            "/api/v1/auth/login",
            data={"username": unique_email, "password": password, "grant_type": "password"},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        login_token = login_resp.json()["access_token"]
        assert login_token

        # 3. Create Session
        user_headers = {"Authorization": f"Bearer {user_token}"}
        session_resp = await ac.post("/api/v1/auth/session", headers=user_headers)
        assert session_resp.status_code == 200, f"Session creation failed: {session_resp.text}"
        session_data = session_resp.json()
        session_id = session_data["session_id"]
        session_token = session_data["token"]["access_token"]
        assert session_id
        assert session_token

        # 4. List Sessions
        list_resp = await ac.get("/api/v1/auth/sessions", headers=user_headers)
        assert list_resp.status_code == 200
        sessions = list_resp.json()
        assert any(s["session_id"] == session_id for s in sessions)

        # 5. Update Session Name
        session_headers = {"Authorization": f"Bearer {session_token}"}
        update_resp = await ac.patch(
            f"/api/v1/auth/session/{session_id}/name",
            data={"name": "My AI Assistant Chat"},
            headers=session_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "My AI Assistant Chat"

        # 6. Delete Session
        del_resp = await ac.delete(f"/api/v1/auth/session/{session_id}", headers=session_headers)
        assert del_resp.status_code == 200


@pytest.mark.anyio
async def test_ticket_lifecycle_and_manager_approval_workflow():
    """Test full ticket lifecycle: creation, retrieval, status transition, and manager approval/rejection."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create Ticket
        create_resp = await ac.post(
            "/api/v1/tickets",
            json={
                "subject": "Missing items in grocery order",
                "description": "2 organic milk packets missing from delivery bag.",
                "category": "Order & Delivery",
                "priority": "High",
                "customer_email": "customer_test@supportai.com"
            }
        )
        assert create_resp.status_code == 200
        ticket_data = create_resp.json()
        ticket_id = ticket_data["ticket_id"]
        assert ticket_id.startswith("#TICK-")
        assert ticket_data["status"] == "Open"
        assert ticket_data["category"] == "Order & Delivery"

        # 2. List Tickets
        list_resp = await ac.get("/api/v1/tickets")
        assert list_resp.status_code == 200
        tickets = list_resp.json()
        assert any(t["ticket_id"] == ticket_id for t in tickets)

        # 3. Get Single Ticket (URL encoded #)
        import urllib.parse
        ticket_slug = urllib.parse.quote(ticket_id)
        get_resp = await ac.get(f"/api/v1/tickets/{ticket_slug}")
        assert get_resp.status_code == 200
        assert get_resp.json()["ticket_id"] == ticket_id

        # 4. Patch Ticket (Update to Pending Approval)
        patch_resp = await ac.patch(
            f"/api/v1/tickets/{ticket_slug}",
            json={
                "status": "Pending Human Manager Approval",
                "internal_notes": "Customer provided photographic proof. Amount > limit."
            }
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "Pending Human Manager Approval"

        # 5. Approve Ticket
        approve_resp = await ac.post(f"/api/v1/tickets/{ticket_slug}/approve")
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "Approved & Executed"
        assert "Approved by Senior Support Manager" in approve_resp.json()["resolution_notes"]

        # 6. Reject Workflow on a second ticket
        create_resp2 = await ac.post(
            "/api/v1/tickets",
            json={
                "subject": "Return request for item bought 90 days ago",
                "description": "Want to return headphones purchased 3 months ago.",
                "category": "Refund & Return",
                "priority": "Low",
                "customer_email": "customer2_test@supportai.com"
            }
        )
        ticket_id2 = create_resp2.json()["ticket_id"]
        ticket2_slug = urllib.parse.quote(ticket_id2)
        reject_resp = await ac.post(f"/api/v1/tickets/{ticket2_slug}/reject")
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "Rejected"


@pytest.mark.anyio
async def test_knowledge_documents_api_endpoint():
    """Test enterprise knowledge documents retrieval endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/tickets/knowledge/documents")
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) >= 4
        doc_ids = [d["doc_id"] for d in docs]
        assert "DOC-REFUND-001" in doc_ids
        assert "DOC-SLA-002" in doc_ids


def test_specialist_knowledge_rag_tool():
    """Test grounded RAG document search tool with source citations and confidence metrics."""
    from src.agent.tools.specialist_tools import search_knowledge_base

    result = search_knowledge_base.invoke({"query": "refund policy electronics 30 days"})
    assert "Grounded Knowledge Document" in result
    assert "DOC-REFUND-001" in result
    assert "Verified Source Citation:" in result
    assert "30 days" in result

    # Test hardware troubleshooting
    hw_result = search_knowledge_base.invoke({"query": "hardware diagnostics power cycling router"})
    assert "DOC-TECH-003" in hw_result


def test_refund_and_replacement_approval_gating():
    """Test deterministic refund rules, automatic execution vs human approval gate for high values."""
    from src.agent.tools.specialist_tools import request_refund_or_replacement

    # Scenario A: Low Value (Automatic Approval under limit)
    auto_res = request_refund_or_replacement.invoke({
        "order_id": "#ORD-12345",
        "action_type": "refund",
        "amount": 1500.0,
        "reason": "Damaged food container on arrival",
        "currency": "INR"
    })
    assert "Refund Request Processed" in auto_res
    assert "Auto-Approved" in auto_res

    # Scenario B: High Value (Triggers Human Approval Gate)
    gate_res = request_refund_or_replacement.invoke({
        "order_id": "#ORD-99887",
        "action_type": "refund",
        "amount": 15000.0,
        "reason": "High-end television defective display",
        "currency": "INR"
    })
    assert "Pending Human Manager Approval" in gate_res
    assert "Audit Ticket:" in gate_res
    assert "Idempotency Key:" in gate_res
    assert "Human Finance Supervisor approval" in gate_res


def test_human_escalation_specialist_tool():
    """Test human agent handover tool with severity assessment and context preservation."""
    from src.agent.tools.specialist_tools import escalate_to_human_agent

    result = escalate_to_human_agent.invoke({
        "reason": "Customer expresses extreme dissatisfaction regarding unresolved billing discrepancy",
        "priority": "Critical",
        "customer_sentiment": "Angry",
        "context_summary": "Order #ORD-77112 charged twice on credit card. Automated refund unsuccessful."
    })
    assert "Human Specialist Escalation Triggered" in result
    assert "CRITICAL" in result or "Critical" in result
    assert "Senior Support Specialist" in result
