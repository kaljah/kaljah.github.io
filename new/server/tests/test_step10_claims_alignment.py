from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_readme_claims_alignment():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "spend-based screening" in readme.lower()
    assert "basic error propagation (monte carlo planned)" in readme.lower()
    assert "in-process background processing" in readme.lower()
    assert "preview, reconciliation logic in development" in readme.lower()
    assert "preview / roadmap" in readme.lower()
    assert "across all 15 ghg protocol categories" not in readme.lower()


def test_codemaps_claims_alignment():
    arch = (REPO_ROOT / "docs" / "CODEMAPS" / "architecture.md").read_text(encoding="utf-8")
    backend = (REPO_ROOT / "docs" / "CODEMAPS" / "backend.md").read_text(encoding="utf-8")
    frontend = (REPO_ROOT / "docs" / "CODEMAPS" / "frontend.md").read_text(encoding="utf-8")
    data = (REPO_ROOT / "docs" / "CODEMAPS" / "data.md").read_text(encoding="utf-8")

    assert "in-process background processing" in arch.lower()
    assert "spend-based screening" in arch.lower()
    assert "basic error propagation (monte carlo planned)" in backend.lower()
    assert "in-process background processing" in backend.lower()
    assert "preview, reconciliation logic in development" in frontend.lower()
    assert "preview / roadmap" in frontend.lower()
    assert "spend-based screening" in data.lower()
    assert "preview, reconciliation logic in development" in data.lower()
