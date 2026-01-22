"""AgentGate CLI entrypoint.

Usage:
    python -m agentgate              # Start the server
    python -m agentgate --demo       # Run interactive demo
    python -m agentgate --version    # Print version
    python -m agentgate --help       # Show help
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def print_banner() -> None:
    """Print the AgentGate banner."""
    banner = r"""
   _                    _    ____       _
  / \   __ _  ___ _ __ | |_ / ___| __ _| |_ ___
 / _ \ / _` |/ _ \ '_ \| __| |  _ / _` | __/ _ \
/ ___ \ (_| |  __/ | | | |_| |_| | (_| | ||  __/
/_/  \_\__, |\___|_| |_|\__|\____|\__,_|\__\___|
       |___/        Containment-First Security
"""
    print(banner)


async def run_demo() -> None:
    """Run the interactive demo."""
    from agentgate.client import AgentGateClient

    print_banner()
    print("=== AgentGate Interactive Demo ===\n")
    print("This demo requires the AgentGate server running at http://localhost:8000")
    print("Start the server with: make dev\n")

    try:
        async with AgentGateClient("http://localhost:8000") as client:
            session_id = "interactive_demo"

            # Step 1: Health check
            print("1. Checking server health...")
            import httpx

            async with httpx.AsyncClient() as http:
                resp = await http.get("http://localhost:8000/health")
                health = resp.json()
                print(f"   Status: {health['status']}")
                print(f"   Version: {health['version']}")
                print(f"   OPA: {'✓' if health['opa'] else '✗'}")
                print(f"   Redis: {'✓' if health['redis'] else '✗'}")

            # Step 2: List tools
            print("\n2. Listing available tools...")
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    "http://localhost:8000/tools/list",
                    params={"session_id": session_id},
                )
                tools = resp.json()
                print(f"   Available tools: {', '.join(tools['tools'])}")

            # Step 3: Allowed read
            print("\n3. Attempting database query (should be allowed)...")
            result = await client.call_tool(
                session_id=session_id,
                tool_name="db_query",
                arguments={"query": "SELECT * FROM products LIMIT 5"},
            )
            if result.get("success"):
                print("   ✓ ALLOWED")
                print(f"   Result: {result.get('result')}")
            else:
                print(f"   ✗ BLOCKED: {result.get('error')}")

            # Step 4: Denied unknown tool
            print("\n4. Attempting unknown tool (should be denied)...")
            result = await client.call_tool(
                session_id=session_id,
                tool_name="hack_the_planet",
                arguments={},
            )
            if result.get("success"):
                print("   ✓ ALLOWED (unexpected!)")
            else:
                print(f"   ✗ BLOCKED: {result.get('error')}")

            # Step 5: Write requires approval
            print("\n5. Attempting database insert without approval...")
            result = await client.call_tool(
                session_id=session_id,
                tool_name="db_insert",
                arguments={"table": "products", "data": {"name": "New Product"}},
            )
            if result.get("success"):
                print("   ✓ ALLOWED (unexpected!)")
            else:
                error = result.get("error", "")
                if "approval" in error.lower():
                    print("   ⏳ PENDING: Write action requires human approval")
                else:
                    print(f"   ✗ BLOCKED: {error}")

            # Step 6: Write with approval
            print("\n6. Retrying with approval token...")
            result = await client.call_tool(
                session_id=session_id,
                tool_name="db_insert",
                arguments={"table": "products", "data": {"name": "New Product"}},
                approval_token="approved",  # nosec B106
            )
            if result.get("success"):
                print("   ✓ ALLOWED (with approval)")
                print(f"   Result: {result.get('result')}")
            else:
                print(f"   ✗ BLOCKED: {result.get('error')}")

            # Step 7: Kill switch
            print("\n7. Activating kill switch for this session...")
            await client.kill_session(session_id, reason="Demo completed")
            print("   Kill switch activated")

            # Step 8: Verify blocked
            print("\n8. Attempting query after kill switch...")
            result = await client.call_tool(
                session_id=session_id,
                tool_name="db_query",
                arguments={"query": "SELECT 1"},
            )
            if result.get("success"):
                print("   ✓ ALLOWED (unexpected!)")
            else:
                print(f"   ✗ BLOCKED: {result.get('error')}")

            # Step 9: Export evidence
            print("\n9. Exporting evidence pack...")
            evidence = await client.export_evidence(session_id)
            summary = evidence.get("summary", {})
            print(f"   Total events: {summary.get('total_tool_calls', 0)}")
            print(f"   Allowed: {summary.get('by_decision', {}).get('ALLOW', 0)}")
            print(f"   Denied: {summary.get('by_decision', {}).get('DENY', 0)}")

            integrity = evidence.get("integrity", {})
            if integrity.get("signature"):
                print("   ✓ Evidence pack is cryptographically signed")
            else:
                print("   ⚠ Evidence pack is not signed (set AGENTGATE_SIGNING_KEY)")

            print("\n=== Demo Complete ===")
            print("\nTry these next:")
            print("  • View API docs: http://localhost:8000/docs")
            print("  • View metrics: http://localhost:8000/metrics")
            print("  • Export HTML evidence: http://localhost:8000/sessions/interactive_demo/evidence?format=html")

    except Exception as exc:
        print(f"\n✗ Demo failed: {exc}")
        print("\nMake sure the server is running: make dev")
        sys.exit(1)


def main() -> None:
    """CLI entrypoint."""
    from agentgate import __version__

    parser = argparse.ArgumentParser(
        prog="agentgate",
        description="AgentGate: Containment-first security gateway for AI agents",
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"AgentGate {__version__}"
    )
    parser.add_argument(
        "--demo", action="store_true", help="Run interactive demo"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"  # nosec B104
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind to (default: 8000)"
    )

    args = parser.parse_args()

    if args.demo:
        asyncio.run(run_demo())
    else:
        print_banner()
        import uvicorn

        uvicorn.run(
            "agentgate.main:app",
            host=args.host,
            port=args.port,
            reload=False,
        )


if __name__ == "__main__":
    main()
