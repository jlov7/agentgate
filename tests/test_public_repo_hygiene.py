from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_readme_documents_frontend_and_repo_structure() -> None:
    readme = _read("README.md")

    assert "## Frontier Console" in readme
    assert "## Repository Structure" in readme
    assert "apps/console" in readme
    assert "packages/ui" in readme
    assert "packages/agentgate-client" in readme
    assert "scripts/run_frontend_gate.sh" in readme


def test_frontend_readme_covers_console_operating_model() -> None:
    readme = _read("apps/console/README.md")

    assert "## Route Ownership" in readme
    assert "## Data Flow" in readme
    assert "## Verification" in readme
    assert "AGENTGATE_API_BASE_URL" in readme
    assert "No horizontal overflow" in readme


def test_generated_frontend_artifacts_are_ignored() -> None:
    gitignore = _read(".gitignore")

    for pattern in (".next/", ".turbo/", "*.tsbuildinfo", ".playwright-mcp/"):
        assert pattern in gitignore


def test_public_limitations_are_current() -> None:
    readme = _read("README.md")
    stale_credential_claim = "Credential broker is a " + "stub"

    assert "Credential provider defaults to demo mode" in readme
    assert "JWKS-backed JWTs" in readme
    assert stale_credential_claim not in readme
