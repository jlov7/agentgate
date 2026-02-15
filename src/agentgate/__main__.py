"""AgentGate CLI entrypoint.

Usage:
    python -m agentgate              # Start the server
    python -m agentgate --demo       # Run interactive demo
    python -m agentgate --showcase   # Run showcase and generate artifacts
    python -m agentgate --version    # Print version
    python -m agentgate --help       # Show help
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentgate.client import AgentGateClient
from agentgate.invariants import evaluate_policy_invariants
from agentgate.transparency import verify_inclusion_proof

DEMO_BASE_URL = "http://localhost:8000"


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


def run_self_check(base_url: str, output_json: bool = False) -> int:
    """Run first-run diagnostics and print actionable guidance."""
    import httpx

    checks: dict[str, dict[str, Any]] = {}

    python_ok = sys.version_info >= (3, 12)
    checks["python_version"] = {
        "required": True,
        "status": "pass" if python_ok else "fail",
        "detail": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "hint": "Install Python 3.12+." if not python_ok else "Detected supported Python version.",
    }

    docker_binary = shutil.which("docker")
    docker_ok = docker_binary is not None
    docker_detail = docker_binary or "docker not found"
    checks["docker_cli"] = {
        "required": True,
        "status": "pass" if docker_ok else "fail",
        "detail": docker_detail,
        "hint": "Install Docker Desktop and ensure `docker` is on PATH."
        if not docker_ok
        else "Docker CLI detected.",
    }

    docker_compose_binary = shutil.which("docker-compose")
    compose_ok = docker_ok or docker_compose_binary is not None
    compose_detail = docker_compose_binary or "docker compose plugin expected via docker CLI"
    checks["docker_compose"] = {
        "required": True,
        "status": "pass" if compose_ok else "fail",
        "detail": compose_detail,
        "hint": "Install Docker Compose (plugin or docker-compose binary)."
        if not compose_ok
        else "Compose detected.",
    }

    policy_path = Path(__file__).resolve().parents[2] / "policies" / "data.json"
    policy_ok = policy_path.exists()
    checks["policy_data"] = {
        "required": True,
        "status": "pass" if policy_ok else "fail",
        "detail": str(policy_path),
        "hint": (
            "Ensure repository includes policies/data.json."
            if not policy_ok
            else "Policy data found."
        ),
    }

    server_ok = False
    server_detail = f"Could not reach {base_url}/health"
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{base_url}/health")
            if response.status_code == 200:
                payload = response.json()
                server_ok = True
                server_detail = (
                    f"status={payload.get('status')}, "
                    f"opa={payload.get('opa')}, redis={payload.get('redis')}"
                )
            else:
                server_detail = f"HTTP {response.status_code}"
    except Exception as exc:
        server_detail = str(exc)

    checks["server_health"] = {
        "required": False,
        "status": "pass" if server_ok else "warn",
        "detail": server_detail,
        "hint": "Start the stack with `make dev` and re-run self-check."
        if not server_ok
        else "Server health endpoint reachable.",
    }

    required_failed = [
        name
        for name, check in checks.items()
        if check["required"] and check["status"] != "pass"
    ]
    warnings = [name for name, check in checks.items() if check["status"] == "warn"]
    status = "pass" if not required_failed else "fail"

    payload = {
        "status": status,
        "required_failed": required_failed,
        "warnings": warnings,
        "checks": checks,
    }

    if output_json:
        print(json.dumps(payload, indent=2))
    else:
        print("AgentGate Self-Check")
        print("")
        for name, check in checks.items():
            print(f"{name}: {check['status']} | {check['detail']}")
            print(f"  hint: {check['hint']}")
        print("")
        print(f"overall: {status}")
        if required_failed:
            print(f"required failures: {', '.join(required_failed)}")
        if warnings:
            print(f"warnings: {', '.join(warnings)}")

    return 0 if status == "pass" else 1


def _load_json_payload(value: str) -> dict[str, Any]:
    path = Path(value)
    payload = (
        json.loads(path.read_text(encoding="utf-8"))
        if path.exists()
        else json.loads(value)
    )
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object for payload.")
    return payload


async def run_demo(base_url: str | None = None) -> None:
    """Run the interactive demo."""
    from agentgate.client import AgentGateClient

    base_url = base_url or DEMO_BASE_URL
    print_banner()
    print("=== AgentGate Interactive Demo ===\n")
    print(f"This demo requires the AgentGate server running at {base_url}")
    print("Start the server with: make dev\n")

    try:
        async with AgentGateClient(base_url) as client:
            session_id = "interactive_demo"

            # Step 1: Health check
            print("1. Checking server health...")
            import httpx

            async with httpx.AsyncClient() as http:
                resp = await http.get(f"{base_url}/health")
                health = resp.json()
                print(f"   Status: {health['status']}")
                print(f"   Version: {health['version']}")
                print(f"   OPA: {'✓' if health['opa'] else '✗'}")
                print(f"   Redis: {'✓' if health['redis'] else '✗'}")

            # Step 2: List tools
            print("\n2. Listing available tools...")
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    f"{base_url}/tools/list",
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
        print("\n✗ Demo failed: AgentGate server is not reachable.")
        print("Fix: start the server with `make dev`.")
        print(f"Details: {exc}")
        sys.exit(1)


def main() -> None:
    """CLI entrypoint."""
    from agentgate import __version__
    from agentgate.showcase import ShowcaseConfig, run_showcase

    parser = argparse.ArgumentParser(
        prog="agentgate",
        description="AgentGate: Containment-first security gateway for AI agents",
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"AgentGate {__version__}"
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--demo", action="store_true", help="Run interactive demo")
    mode_group.add_argument(
        "--showcase", action="store_true", help="Run showcase and generate artifacts"
    )
    mode_group.add_argument(
        "--self-check",
        action="store_true",
        help="Run first-run diagnostics and setup guidance",
    )
    mode_group.add_argument(
        "--replay-run",
        help="Run a replay using a JSON payload or path to JSON file",
    )
    mode_group.add_argument(
        "--incident-release",
        help="Release a quarantined incident by ID",
    )
    mode_group.add_argument(
        "--invariant-check",
        help="Run local policy invariant checks from a JSON payload or file path",
    )
    mode_group.add_argument(
        "--verify-transparency",
        help="Verify transparency proof report from JSON payload or file path",
    )
    mode_group.add_argument(
        "--rollout-start",
        help="Start a tenant rollout (provide tenant ID)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for demo/showcase (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--showcase-output",
        default="docs/showcase",
        help="Output directory for showcase artifacts (default: docs/showcase)",
    )
    parser.add_argument(
        "--showcase-session",
        default=None,
        help="Session ID for showcase run (default: auto-generated timestamp)",
    )
    parser.add_argument(
        "--showcase-delay",
        type=float,
        default=float(os.getenv("AGENTGATE_SHOWCASE_DELAY", "0")),
        help="Seconds to pause between showcase steps (default: 0)",
    )
    parser.add_argument(
        "--showcase-theme",
        default=os.getenv("AGENTGATE_SHOWCASE_THEME", "studio"),
        help="Theme for evidence HTML/PDF (default: studio)",
    )
    parser.add_argument(
        "--showcase-light-theme",
        default=os.getenv("AGENTGATE_SHOWCASE_LIGHT_THEME", "light"),
        help="Alternate light theme name for evidence export (default: light)",
    )
    parser.add_argument(
        "--self-check-json",
        action="store_true",
        help="Emit JSON output for --self-check mode",
    )
    parser.add_argument(
        "--admin-key",
        default=os.getenv("AGENTGATE_ADMIN_API_KEY", ""),
        help="Admin API key for privileged commands",
    )
    parser.add_argument(
        "--released-by",
        default=None,
        help="Actor name for incident release",
    )
    parser.add_argument(
        "--rollout-payload",
        default=None,
        help="Rollout payload JSON or path to JSON file",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"  # nosec B104
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind to (default: 8000)"
    )

    args = parser.parse_args()

    if args.self_check_json and not args.self_check:
        parser.error("--self-check-json requires --self-check")
    if args.incident_release and not args.released_by:
        parser.error("--released-by is required for --incident-release")
    if args.rollout_start and not args.rollout_payload:
        parser.error("--rollout-payload is required for --rollout-start")

    if args.demo:
        global DEMO_BASE_URL
        DEMO_BASE_URL = args.base_url
        asyncio.run(run_demo())
    elif args.showcase:
        session_id = args.showcase_session
        if session_id is None:
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            session_id = f"showcase-{stamp}"
        config = ShowcaseConfig(
            base_url=args.base_url,
            output_dir=Path(args.showcase_output),
            session_id=session_id,
            approval_token=os.getenv("AGENTGATE_APPROVAL_TOKEN", "approved"),
            step_delay=args.showcase_delay,
            evidence_theme=args.showcase_theme,
            light_theme=args.showcase_light_theme,
        )
        sys.exit(asyncio.run(run_showcase(config)))
    elif args.self_check:
        sys.exit(run_self_check(args.base_url, output_json=args.self_check_json))
    elif args.replay_run:
        if not args.admin_key:
            parser.error("--admin-key required for --replay-run")

        async def run_replay() -> int:
            payload = _load_json_payload(args.replay_run)
            async with AgentGateClient(args.base_url) as client:
                result = await client.create_replay_run(
                    api_key=args.admin_key,
                    payload=payload,
                )
                print(json.dumps(result, indent=2))
            return 0

        sys.exit(asyncio.run(run_replay()))
    elif args.invariant_check:
        payload = _load_json_payload(args.invariant_check)
        baseline_policy_data = payload.get("baseline_policy_data")
        candidate_policy_data = payload.get("candidate_policy_data")
        selected_invariants = payload.get("invariants")
        if not isinstance(baseline_policy_data, dict) or not isinstance(
            candidate_policy_data, dict
        ):
            parser.error(
                "--invariant-check payload must include "
                "baseline_policy_data and candidate_policy_data objects"
            )
        if selected_invariants is not None and (
            not isinstance(selected_invariants, list)
            or any(not isinstance(item, str) for item in selected_invariants)
        ):
            parser.error("invariants must be a list of strings")
        report = evaluate_policy_invariants(
            run_id=str(payload.get("run_id", "cli-invariant-check")),
            baseline_policy_data=baseline_policy_data,
            candidate_policy_data=candidate_policy_data,
            selected_invariants=selected_invariants,
        )
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["status"] == "pass" else 1)
    elif args.verify_transparency:
        payload = _load_json_payload(args.verify_transparency)
        event_count = payload.get("event_count")
        root_hash = payload.get("root_hash")
        proofs = payload.get("proofs")
        if not isinstance(event_count, int) or event_count < 0:
            parser.error("transparency payload must include integer event_count")
        if not isinstance(root_hash, str):
            parser.error("transparency payload must include root_hash")
        if not isinstance(proofs, list):
            parser.error("transparency payload must include proofs list")
        failures: list[str] = []
        for proof_entry in proofs:
            if not isinstance(proof_entry, dict):
                failures.append("invalid-proof-entry")
                continue
            event_id = str(proof_entry.get("event_id", "unknown"))
            leaf_hash = proof_entry.get("leaf_hash")
            index = proof_entry.get("index")
            proof = proof_entry.get("proof")
            if (
                not isinstance(leaf_hash, str)
                or not isinstance(index, int)
                or not isinstance(proof, list)
                or any(not isinstance(item, str) for item in proof)
            ):
                failures.append(event_id)
                continue
            ok = verify_inclusion_proof(
                leaf_hash=leaf_hash,
                index=index,
                total_leaves=max(event_count, 1),
                proof=proof,
                root_hash=root_hash,
            )
            if not ok:
                failures.append(event_id)
        result = {
            "status": "pass" if not failures else "fail",
            "verified": len(proofs) - len(failures),
            "total": len(proofs),
            "failures": failures,
        }
        print(json.dumps(result, indent=2))
        sys.exit(0 if not failures else 1)
    elif args.incident_release:
        if not args.admin_key:
            parser.error("--admin-key required for --incident-release")

        async def run_release() -> int:
            async with AgentGateClient(args.base_url) as client:
                result = await client.release_incident(
                    api_key=args.admin_key,
                    incident_id=args.incident_release,
                    released_by=args.released_by,
                )
                print(json.dumps(result, indent=2))
            return 0

        sys.exit(asyncio.run(run_release()))
    elif args.rollout_start:
        if not args.admin_key:
            parser.error("--admin-key required for --rollout-start")

        async def run_rollout() -> int:
            payload = _load_json_payload(args.rollout_payload)
            async with AgentGateClient(args.base_url) as client:
                result = await client.start_rollout(
                    api_key=args.admin_key,
                    tenant_id=args.rollout_start,
                    payload=payload,
                )
                print(json.dumps(result, indent=2))
            return 0

        sys.exit(asyncio.run(run_rollout()))
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
