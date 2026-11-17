from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_readme_claims_alignment():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    low = readme.lower()

    # Preserved honest limitations
    assert "spend-based screening" in low
    assert "basic error propagation (monte carlo planned)" in low
    assert "in-process background processing" in low
    assert "across all 15 ghg protocol categories" not in low

    # OGMP 2.0 & CBAM XML are full features (no preview/dev copy)
    assert "level 1–5" in low or "level 1-5" in low or "13-sheet excel" in low
    assert "cbam" in low and "2023/1773" in low
    assert "preview, reconciliation logic in development" not in low
    assert "preview / roadmap" not in low


def test_codemaps_claims_alignment():
    arch = (REPO_ROOT / "docs" / "CODEMAPS" / "architecture.md").read_text(encoding="utf-8")
    backend = (REPO_ROOT / "docs" / "CODEMAPS" / "backend.md").read_text(encoding="utf-8")
    frontend = (REPO_ROOT / "docs" / "CODEMAPS" / "frontend.md").read_text(encoding="utf-8")
    data = (REPO_ROOT / "docs" / "CODEMAPS" / "data.md").read_text(encoding="utf-8")

    # Preserved honest limitations
    assert "in-process background processing" in arch.lower()
    assert "spend-based screening" in arch.lower()
    assert "basic error propagation (monte carlo planned)" in backend.lower()
    assert "in-process background processing" in backend.lower()
    assert "basic error propagation; monte carlo planned" in frontend.lower()
    assert "spend-based screening" in data.lower()

    # OGMP 2.0 & CBAM XML have zero preview/dev disclaimers in codemaps
    assert "preview, reconciliation logic in development" not in frontend.lower()
    assert "preview / roadmap" not in frontend.lower()
    assert "preview, reconciliation logic in development" not in data.lower()
    assert "level 4/5" in data.lower() or "rss" in data.lower()
