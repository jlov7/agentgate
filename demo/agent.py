"""Demo agent for AgentGate security controls."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from agentgate.client import AgentGateClient


class DemoAgent:
    """Demonstrates AgentGate containment controls."""

    def __init__(self, agentgate_url: str, session_id: str) -> None:
        self.client = AgentGateClient(agentgate_url)
        self.session_id = session_id
        self.approval_token = os.getenv("AGENTGATE_APPROVAL_TOKEN", "approved")

    async def run_demo(self) -> None:
        """Run the demo scenario end-to-end."""
        print("=== AgentGate Demo ===\n")

        print("1. Attempting database query (should be allowed)...")
        result = await self.client.call_tool(
            session_id=self.session_id,
            tool_name="db_query",
            arguments={"query": "SELECT * FROM products LIMIT 5"},
        )
        self._print_result(result)

        print("\n2. Attempting unknown tool (should be denied)...")
        result = await self.client.call_tool(
            session_id=self.session_id,
            tool_name="hack_the_planet",
            arguments={},
        )
        self._print_result(result)

        print("\n3. Attempting database insert without approval (should require approval)...")
        result = await self.client.call_tool(
            session_id=self.session_id,
            tool_name="db_insert",
            arguments={"table": "products", "data": {"name": "New Product"}},
        )
        self._print_result(result)

        print("\n4. [Operator approves the write action]")
        print("   Retrying with approval token...")
        result = await self.client.call_tool(
            session_id=self.session_id,
            tool_name="db_insert",
            arguments={"table": "products", "data": {"name": "New Product"}},
            approval_token=self.approval_token,
        )
        self._print_result(result)

        print("\n5. [Operator activates kill switch for this session]")
        await self.client.kill_session(self.session_id, reason="Demo session terminated")

        print("   Attempting another query (should fail)...")
        result = await self.client.call_tool(
            session_id=self.session_id,
            tool_name="db_query",
            arguments={"query": "SELECT 1"},
        )
        self._print_result(result)

        print("\n6. Exporting evidence pack...")
        evidence = await self.client.export_evidence(self.session_id)
        print(f"   Total events: {evidence['summary']['total_tool_calls']}")
        print(f"   Allowed: {evidence['summary']['by_decision']['ALLOW']}")
        print(f"   Denied: {evidence['summary']['by_decision']['DENY']}")

        with open(f"evidence_{self.session_id}.json", "w", encoding="utf-8") as handle:
            json.dump(evidence, handle, indent=2)
        print(f"   Saved to evidence_{self.session_id}.json")

        print("\n=== Demo Complete ===")
        await self.client.close()

    @staticmethod
    def _print_result(result: dict[str, Any]) -> None:
        """Print a concise summary of a tool call result."""
        if result.get("success"):
            print("   ALLOWED")
            print(f"   Result: {result.get('result')}")
        else:
            error = result.get("error") or "Unknown error"
            if "approval" in error.lower():
                print("   PENDING: Write action requires human approval")
            else:
                print(f"   BLOCKED: {error}")


if __name__ == "__main__":
    base_url = os.getenv("AGENTGATE_URL", "http://127.0.0.1:18081")
    session_id = os.getenv("AGENTGATE_DEMO_SESSION_ID", "demo_session")
    asyncio.run(DemoAgent(base_url, session_id).run_demo())
