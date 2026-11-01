"""Production-Grade Concurrency and Multi-Database Load Testing Suite.

Simulates 500+ concurrent customers simultaneously interacting with the
FastAPI agentic system and PostgreSQL database across all entities:
1. Users & Authentication
2. Chat Sessions & Threads
3. Customer Support Tickets & Manager Approvals
4. Enterprise Knowledge Base RAG Documents
5. Food & E-Commerce Orders & Live Telemetry
6. Health & Metrics Telemetry
"""

import asyncio
import datetime
import os
import random
import sys
import time
import uuid
from collections import Counter
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import httpx
from sqlmodel import Session, select

from src.config.settings import settings
from src.data.db_manager import db_manager
from src.data.models.knowledge import KnowledgeDocument
from src.data.models.order import OrderRecord
from src.data.models.session import Session as ChatSession
from src.data.models.ticket import Ticket
from src.data.models.user import User

BASE_URL = "http://127.0.0.1:8000"


async def resilient_request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    """Execute HTTP request with transient connection retry for Windows TCP stack."""
    for attempt in range(4):
        try:
            return await client.request(method, url, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            if attempt == 3:
                raise
            await asyncio.sleep(0.05 * (attempt + 1))


async def customer_auth_worker(client: httpx.AsyncClient, cust_id: int) -> Dict[str, Any]:
    """Simulate Customer Cohort 1: User Registration, Login, and Session Lifecycle."""
    await asyncio.sleep((cust_id % 50) * 0.01)
    email = f"loadcust_{cust_id}_{uuid.uuid4().hex[:6]}@loadtest.com"
    password = "SecurePassword123!"
    try:
        # 1. Register
        reg_r = await resilient_request(
            client,
            "POST",
            f"{BASE_URL}/api/v1/auth/register",
            json={"email": email, "password": password},
            headers={"X-Forwarded-For": f"10.0.{cust_id // 250}.{cust_id % 250 + 1}"},
        )
        if reg_r.status_code != 200:
            return {"cohort": "auth", "status": reg_r.status_code, "error": f"reg: {reg_r.text[:50]}"}

        token = reg_r.json()["token"]["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Forwarded-For": f"10.0.{cust_id // 250}.{cust_id % 250 + 1}",
        }

        # 2. Create Session
        sess_r = await resilient_request(client, "POST", f"{BASE_URL}/api/v1/auth/session", headers=headers)
        if sess_r.status_code != 200:
            return {"cohort": "auth", "status": sess_r.status_code, "error": f"sess: {sess_r.text[:50]}"}
        session_id = sess_r.json()["session_id"]
        sess_token = sess_r.json()["token"]["access_token"]

        # 3. Update Session Name
        s_headers = {
            "Authorization": f"Bearer {sess_token}",
            "X-Forwarded-For": f"10.0.{cust_id // 250}.{cust_id % 250 + 1}",
        }
        patch_r = await resilient_request(
            client,
            "PATCH",
            f"{BASE_URL}/api/v1/auth/session/{session_id}/name",
            data={"name": f"Session for Customer #{cust_id}"},
            headers=s_headers,
        )

        # 4. List Sessions
        list_r = await resilient_request(client, "GET", f"{BASE_URL}/api/v1/auth/sessions", headers=headers)

        success = (
            reg_r.status_code == 200
            and sess_r.status_code == 200
            and patch_r.status_code == 200
            and list_r.status_code == 200
        )
        return {"cohort": "auth", "status": 200 if success else 500, "error": None}
    except Exception as e:
        return {"cohort": "auth", "status": "EXC", "error": str(e)}


async def customer_ticket_worker(client: httpx.AsyncClient, cust_id: int) -> Dict[str, Any]:
    """Simulate Customer Cohort 2: Support Ticket Creation, Querying, and Lifecycle."""
    await asyncio.sleep((cust_id % 50) * 0.01)
    try:
        headers = {"X-Forwarded-For": f"10.1.{cust_id // 250}.{cust_id % 250 + 1}"}
        # 1. Create Ticket
        create_r = await resilient_request(
            client,
            "POST",
            f"{BASE_URL}/api/v1/tickets",
            json={
                "subject": f"Automated Inquiry #{cust_id} - Order Delivery Delay",
                "description": f"Customer #{cust_id} requesting status of scheduled delivery.",
                "category": "Order & Delivery",
                "priority": "High" if cust_id % 2 == 0 else "Medium",
                "customer_email": f"cust_{cust_id}@loadtest.com",
            },
            headers=headers,
        )
        if create_r.status_code != 200:
            return {"cohort": "tickets", "status": create_r.status_code, "error": create_r.text[:50]}

        ticket_id = create_r.json()["ticket_id"]
        import urllib.parse
        slug = urllib.parse.quote(ticket_id)

        # 2. Get Ticket
        get_r = await resilient_request(client, "GET", f"{BASE_URL}/api/v1/tickets/{slug}", headers=headers)

        # 3. Update / Approve Ticket
        appr_r = await resilient_request(client, "POST", f"{BASE_URL}/api/v1/tickets/{slug}/approve", headers=headers)

        success = create_r.status_code == 200 and get_r.status_code == 200 and appr_r.status_code == 200
        return {"cohort": "tickets", "status": 200 if success else 500, "error": None}
    except Exception as e:
        return {"cohort": "tickets", "status": "EXC", "error": str(e)}


async def customer_knowledge_worker(client: httpx.AsyncClient, cust_id: int) -> Dict[str, Any]:
    """Simulate Customer Cohort 3: Enterprise Knowledge Base RAG Inquiries."""
    await asyncio.sleep((cust_id % 50) * 0.01)
    try:
        headers = {"X-Forwarded-For": f"10.2.{cust_id // 250}.{cust_id % 250 + 1}"}
        # 1. List Enterprise Knowledge Documents via HTTP
        docs_r = await resilient_request(client, "GET", f"{BASE_URL}/api/v1/tickets/knowledge/documents", headers=headers)

        # 2. Check Database directly with Session
        with Session(db_manager.engine) as session:
            count = session.exec(select(KnowledgeDocument)).all()
            assert len(count) >= 4

        return {"cohort": "knowledge", "status": docs_r.status_code, "error": None}
    except Exception as e:
        return {"cohort": "knowledge", "status": "EXC", "error": str(e)}


async def customer_order_worker(client: httpx.AsyncClient, cust_id: int) -> Dict[str, Any]:
    """Simulate Customer Cohort 4: E-Commerce & Food Orders in Database."""
    await asyncio.sleep((cust_id % 50) * 0.01)
    try:
        from src.agent.tools.jarvis_tools import place_order, track_order

        platform = random.choice(["Domino's", "Swiggy", "Zomato", "Amazon", "Apple"])
        item = random.choice([
            "Farmhouse Feast Pizza",
            "Cheesy Garlic Bread",
            "Apple AirPods Pro 2",
            "MacBook Air M3",
            "Hydration Energy Drink",
        ])

        # 1. Place order (invokes itemized pricing + saves to DB via shared engine)
        placement = place_order.invoke({
            "platform": platform,
            "item_name": item,
            "quantity": 1,
            "delivery_address": f"Suite {cust_id}, Tech Park Tower, Bangalore",
        })

        import re
        match = re.search(r"`(#ORD-\d+)`", placement)
        if not match:
            return {"cohort": "orders", "status": "FAIL", "error": f"Invalid order response: {placement[:50]}"}
        order_id = match.group(1)

        # 2. Track order (queries PostgreSQL order_records table)
        tracking = track_order.invoke({"order_id": order_id, "platform": platform})
        assert order_id in tracking

        return {"cohort": "orders", "status": 200, "error": None}
    except Exception as e:
        return {"cohort": "orders", "status": "EXC", "error": str(e)}


async def customer_telemetry_worker(client: httpx.AsyncClient, cust_id: int) -> Dict[str, Any]:
    """Simulate Customer Cohort 5: High-Frequency Telemetry & Health Probes."""
    await asyncio.sleep((cust_id % 50) * 0.01)
    try:
        headers = {"X-Forwarded-For": f"10.4.{cust_id // 250}.{cust_id % 250 + 1}"}
        h_resp = await resilient_request(client, "GET", f"{BASE_URL}/health", headers=headers)
        i_resp = await resilient_request(client, "GET", f"{BASE_URL}/api-info", headers=headers)

        success = h_resp.status_code == 200 and i_resp.status_code == 200
        return {"cohort": "telemetry", "status": 200 if success else h_resp.status_code, "error": None}
    except Exception as e:
        return {"cohort": "telemetry", "status": "EXC", "error": str(e)}


async def run_500_concurrency_test():
    """Run 500 simultaneous customer workers across all endpoints and database models."""
    print("=" * 80)
    print("[START] 500 CONCURRENT CUSTOMER LOAD & MULTI-DATABASE STRESS TEST")
    print(f"Target Server: {BASE_URL}")
    print(f"Database Pool: size={settings.POSTGRES_POOL_SIZE}, max_overflow={settings.POSTGRES_MAX_OVERFLOW}")
    print("=" * 80)

    limits = httpx.Limits(max_keepalive_connections=500, max_connections=500)
    timeout = httpx.Timeout(45.0, connect=10.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        # Pre-flight check
        r = await client.get(f"{BASE_URL}/health")
        assert r.status_code == 200, f"Server unhealthy: {r.text}"
        print(f"Pre-flight health check PASSED: {r.json()}")

        # Build 500 concurrent customer tasks
        tasks = []
        for i in range(1, 501):
            if i <= 100:
                tasks.append(customer_auth_worker(client, i))
            elif i <= 200:
                tasks.append(customer_ticket_worker(client, i))
            elif i <= 300:
                tasks.append(customer_knowledge_worker(client, i))
            elif i <= 400:
                tasks.append(customer_order_worker(client, i))
            else:
                tasks.append(customer_telemetry_worker(client, i))

        print(f"\n[EXEC] Launching {len(tasks)} concurrent customer transactions simultaneously...")
        start_time = time.perf_counter()

        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.perf_counter() - start_time
        print(f"\n[DONE] All 500 customer transactions completed in {elapsed:.2f} seconds!")
        rps = 500 / elapsed
        print(f"[METRIC] Average Throughput: {rps:.2f} customer workflows/second")

        # Process and categorize results
        statuses = []
        cohort_stats = Counter()
        failures = []

        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                statuses.append(f"EXCEPTION: {type(res).__name__}")
                failures.append((idx + 1, str(res)))
            else:
                st = res.get("status")
                cohort = res.get("cohort", "unknown")
                statuses.append(st)
                if st == 200:
                    cohort_stats[f"{cohort}_success"] += 1
                else:
                    cohort_stats[f"{cohort}_fail"] += 1
                    failures.append((idx + 1, res.get("error")))

        print("\n[SUMMARY] OVERALL STATUS SUMMARY:")
        print(Counter(statuses))

        print("\n[COHORTS] COHORT BREAKDOWN:")
        for k, v in sorted(cohort_stats.items()):
            print(f"  * {k}: {v}")

        if failures:
            print(f"\n[WARN] Total Failures: {len(failures)}:")
            for f in failures[:10]:
                print(f"  - Customer #{f[0]}: {f[1]}")
        else:
            print("\n[SUCCESS] ZERO FAILURES! 100% of 500 concurrent customers completed with HTTP 200!")

        # Post-test verification of database health
        db_healthy = await db_manager.health_check()
        print(f"\n[DB] Post-Test Database Health Check: {'HEALTHY' if db_healthy else 'UNHEALTHY'}")

        # Post-test verification of PostgreSQL active connections
        with Session(db_manager.engine) as s:
            from sqlalchemy import text
            res = s.exec(text("SELECT count(*) FROM pg_stat_activity WHERE datname = 'food_order_db'")).first()
            print(f"[DB] Active PostgreSQL connections for food_order_db: {res[0]}")


async def run_direct_multi_database_burst_test(concurrency: int = 500):
    """Direct multi-database tables burst test with 500 simultaneous database transactions."""
    print("\n" + "=" * 80)
    print(f"[START] DIRECT MULTI-DATABASE BURST TEST ({concurrency} SIMULTANEOUS TRANSACTIONS)")
    print("Testing concurrent operations across: Users, Sessions, Tickets, Knowledge, Orders")
    print("=" * 80)

    async def db_user_op(i: int):
        with Session(db_manager.engine) as session:
            u = User(email=f"burst_u_{i}_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            session.add(u)
            session.commit()
            session.refresh(u)
            assert session.get(User, u.id) is not None
            return "user_success"

    async def db_session_op(i: int):
        with Session(db_manager.engine) as session:
            sid = f"burst_s_{i}_{uuid.uuid4().hex[:8]}"
            cs = ChatSession(id=sid, user_id=1, name=f"Burst Chat {i}")
            session.add(cs)
            session.commit()
            session.refresh(cs)
            assert session.get(ChatSession, sid) is not None
            return "session_success"

    async def db_ticket_op(i: int):
        with Session(db_manager.engine) as session:
            tid = f"#TICK-BURST-{i}-{random.randint(1000, 9999)}"
            now = datetime.datetime.now(datetime.timezone.utc)
            t = Ticket(
                ticket_id=tid,
                customer_email=f"burst_{i}@test.com",
                category="Billing & Refund",
                subject=f"Burst Ticket #{i}",
                description="Simultaneous multi-db stress query",
                status="Open",
                priority="High",
                created_at=now,
                updated_at=now,
            )
            session.add(t)
            session.commit()
            t.status = "Approved & Executed"
            session.add(t)
            session.commit()
            return "ticket_success"

    async def db_knowledge_op(i: int):
        with Session(db_manager.engine) as session:
            docs = session.exec(select(KnowledgeDocument)).all()
            assert len(docs) >= 4
            return "knowledge_success"

    async def db_order_op(i: int):
        with Session(db_manager.engine) as session:
            oid = f"#ORD-BURST-{i}-{random.randint(10000, 99999)}"
            now = datetime.datetime.now(datetime.timezone.utc)
            o = OrderRecord(
                order_id=oid,
                platform="Domino's",
                item_name=f"Burst Item #{i}",
                quantity=1,
                delivery_address="Tech Campus, Block B",
                subtotal="$25.00",
                tax="$2.00",
                delivery_fee="FREE",
                total="$27.00",
                eta_desc="30 mins",
                carrier_name="Fleet 9",
                vehicle="EV",
                txn_id=f"TXN_{i}",
                is_food=True,
                created_at=now,
            )
            session.add(o)
            session.commit()
            assert session.get(OrderRecord, oid) is not None
            return "order_success"

    tasks = []
    chunk = concurrency // 5
    for i in range(chunk):
        tasks.append(db_user_op(i))
        tasks.append(db_session_op(i))
        tasks.append(db_ticket_op(i))
        tasks.append(db_knowledge_op(i))
        tasks.append(db_order_op(i))

    print(f"[EXEC] Dispatching {len(tasks)} simultaneous multi-table PostgreSQL transactions...")
    start_t = time.perf_counter()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    dur = time.perf_counter() - start_t

    stats = Counter([type(r).__name__ if isinstance(r, Exception) else r for r in results])
    print(f"\n[DONE] {len(tasks)} multi-database transactions finished in {dur:.2f} seconds ({len(tasks)/dur:.2f} tx/sec)")
    print("[SUMMARY] Multi-Database Transaction Breakdown:")
    for k, v in stats.items():
        print(f"  * {k}: {v}")

    # Verify no leaks
    with Session(db_manager.engine) as s:
        from sqlalchemy import text
        res = s.exec(text("SELECT count(*) FROM pg_stat_activity WHERE datname = 'food_order_db'")).first()
        print(f"[DB] Final active PostgreSQL connections: {res[0]}")


async def main():
    await run_500_concurrency_test()
    await run_direct_multi_database_burst_test(500)


if __name__ == "__main__":
    asyncio.run(main())
