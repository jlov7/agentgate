"""AgentGate: Containment-first security gateway for AI agents.

AgentGate sits between AI agents and MCP tools, enforcing policy-as-code
on every call and producing evidence-grade audit trails.

Key features:
    - Policy gates (ALLOW / DENY / REQUIRE_APPROVAL)
    - Kill switches (session / tool / global termination)
    - Credential brokering (time-bound, scope-limited access)
    - Evidence export (audit-ready JSON, HTML, PDF reports)
    - Prometheus metrics for observability
    - Webhook notifications for critical events

Example:
    >>> from agentgate.client import AgentGateClient
    >>> async with AgentGateClient("http://localhost:8000") as client:
    ...     result = await client.call_tool(
    ...         session_id="demo",
    ...         tool_name="db_query",
    ...         arguments={"query": "SELECT 1"},
    ...     )
"""

__all__ = ["__version__"]

__version__ = "0.2.0"
