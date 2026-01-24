"""Showcase runner for AgentGate demo artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentgate.client import AgentGateClient

BANNER = r"""
   _                    _    ____       _
  / \   __ _  ___ _ __ | |_ / ___| __ _| |_ ___
 / _ \ / _` |/ _ \ '_ \| __| |  _ / _` | __/ _ \
/ ___ \ (_| |  __/ | | | |_| |_| | (_| | ||  __/
/_/  \_\__, |\___|_| |_|\__|\____|\__,_|\__\___|
       |___/        Containment-First Security
"""


@dataclass(frozen=True)
class ShowcaseConfig:
    """Runtime configuration for the showcase flow."""

    base_url: str
    output_dir: Path
    session_id: str
    approval_token: str


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _render_banner(console: Console) -> None:
    panel = Panel.fit(
        BANNER.strip("\n"),
        title="AgentGate Showcase",
        subtitle="Containment-first security in 60 seconds",
        box=box.ASCII,
    )
    console.print(panel)


async def run_showcase(config: ShowcaseConfig) -> int:
    """Run a narrated showcase and write demo artifacts."""
    console = Console(record=True, force_terminal=True, width=96)
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "base_url": config.base_url,
        "session_id": config.session_id,
        "artifacts": {},
    }

    try:
        _render_banner(console)
        console.print("")
        console.print("This run will create demo artifacts in:", output_dir)
        console.print("Ensure the AgentGate server is running before continuing.")
        console.print("")

        async with httpx.AsyncClient(base_url=config.base_url, timeout=10.0) as http:
            console.print("Step 1/9: Health check")
            health_resp = await http.get("/health")
            health_resp.raise_for_status()
            health = health_resp.json()
            summary["health"] = health

            health_table = Table(box=box.ASCII, show_header=True, header_style="bold")
            health_table.add_column("Component")
            health_table.add_column("Status")
            health_table.add_row("Gateway", str(health.get("status", "unknown")))
            health_table.add_row("Version", str(health.get("version", "unknown")))
            health_table.add_row("OPA", "OK" if health.get("opa") else "DOWN")
            health_table.add_row("Redis", "OK" if health.get("redis") else "DOWN")
            console.print(health_table)
            console.print("")

            console.print("Step 2/9: Listing tools allowed by policy")
            tools_resp = await http.get("/tools/list", params={"session_id": config.session_id})
            tools_resp.raise_for_status()
            tools = tools_resp.json().get("tools", [])
            console.print(f"Allowed tools: {', '.join(tools)}")
            console.print("")

        async with AgentGateClient(config.base_url) as client:
            console.print("Step 3/9: Allowed read (db_query)")
            allow_result = await client.call_tool(
                session_id=config.session_id,
                tool_name="db_query",
                arguments={"query": "SELECT * FROM products LIMIT 5"},
            )
            console.print(f"Decision: {'ALLOW' if allow_result.get('success') else 'DENY'}")
            console.print("")

            console.print("Step 4/9: Denied unknown tool")
            deny_result = await client.call_tool(
                session_id=config.session_id,
                tool_name="hack_the_planet",
                arguments={},
            )
            console.print(f"Decision: {'ALLOW' if deny_result.get('success') else 'DENY'}")
            console.print("")

            console.print("Step 5/9: Write without approval")
            pending_result = await client.call_tool(
                session_id=config.session_id,
                tool_name="db_insert",
                arguments={"table": "products", "data": {"name": "New Product"}},
            )
            pending_error = (pending_result.get("error") or "").lower()
            pending_state = "REQUIRE_APPROVAL" if "approval" in pending_error else "DENY"
            console.print(f"Decision: {pending_state}")
            console.print("")

            console.print("Step 6/9: Write with approval token")
            approve_result = await client.call_tool(
                session_id=config.session_id,
                tool_name="db_insert",
                arguments={"table": "products", "data": {"name": "New Product"}},
                approval_token=config.approval_token,
            )
            console.print(f"Decision: {'ALLOW' if approve_result.get('success') else 'DENY'}")
            console.print("")

            console.print("Step 7/9: Activate kill switch")
            await client.kill_session(config.session_id, reason="Showcase completed")
            console.print("Kill switch activated")
            console.print("")

            console.print("Step 8/9: Confirm blocked after kill switch")
            blocked_result = await client.call_tool(
                session_id=config.session_id,
                tool_name="db_query",
                arguments={"query": "SELECT 1"},
            )
            console.print(f"Decision: {'ALLOW' if blocked_result.get('success') else 'DENY'}")
            console.print("")

            console.print("Step 9/9: Export evidence pack")
            evidence = await client.export_evidence(config.session_id)
            evidence_path = output_dir / "evidence.json"
            _write_json(evidence_path, evidence)
            summary["artifacts"]["evidence_json"] = str(evidence_path)
            console.print(f"Evidence JSON saved: {evidence_path}")

            async with httpx.AsyncClient(base_url=config.base_url, timeout=20.0) as http:
                html_resp = await http.get(
                    f"/sessions/{config.session_id}/evidence",
                    params={"format": "html"},
                )
                html_resp.raise_for_status()
                html_path = output_dir / "evidence.html"
                _write_text(html_path, html_resp.text)
                summary["artifacts"]["evidence_html"] = str(html_path)
                console.print(f"Evidence HTML saved: {html_path}")

                pdf_path = output_dir / "evidence.pdf"
                pdf_resp = await http.get(
                    f"/sessions/{config.session_id}/evidence",
                    params={"format": "pdf"},
                )
                if pdf_resp.status_code == 200:
                    pdf_path.write_bytes(pdf_resp.content)
                    summary["artifacts"]["evidence_pdf"] = str(pdf_path)
                    console.print(f"Evidence PDF saved: {pdf_path}")
                else:
                    console.print("Evidence PDF skipped (install agentgate[pdf] to enable)")

                metrics_resp = await http.get("/metrics")
                metrics_resp.raise_for_status()
                metrics_path = output_dir / "metrics.prom"
                _write_text(metrics_path, metrics_resp.text)
                summary["artifacts"]["metrics"] = str(metrics_path)
                console.print(f"Metrics snapshot saved: {metrics_path}")

            summary["results"] = {
                "allow": bool(allow_result.get("success")),
                "deny": bool(deny_result.get("success") is False),
                "pending": pending_state,
                "approved": bool(approve_result.get("success")),
                "blocked": bool(blocked_result.get("success") is False),
            }

        console.print("")
        console.print("Showcase complete. Share these artifacts with stakeholders:")
        console.print(f"- {output_dir}/showcase.log")
        console.print(f"- {output_dir}/evidence.html")
        console.print(f"- {output_dir}/metrics.prom")

        summary_path = output_dir / "summary.json"
        summary["artifacts"]["summary"] = str(summary_path)
        _write_json(summary_path, summary)
        return 0
    except Exception as exc:
        console.print("")
        console.print(f"Showcase failed: {exc}")
        return 1
    finally:
        log_path = output_dir / "showcase.log"
        _write_text(log_path, console.export_text(clear=False))
