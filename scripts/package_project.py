"""Package an explicit source allowlist; no keys, environments or private logs."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "SnapSched_Integrated_MVP_2026-10-24.zip"
FILES = [
    ".gitignore", ".streamlit/config.toml", ".streamlit/secrets.toml.example",
    ".github/workflows/ui-tests.yml", "README.md", "README_INTERFACE.md",
    "app.py", "interface_state.py", "integrations.py", "integrations-c.py",
    "review_page.py", "extraction.py", "prompts.py", "ai_extraction.py",
    "calendar_export.py", "runtime_config.py", "test_extraction.py",
    "tests_log_template.csv", "requirements.txt", "requirements-ui.txt",
    "requirements-calendar.txt", "requirements-dev.txt", "repository_link.txt",
    "samples/demo_poster.png", "scripts/create_sample_poster.py",
    "scripts/create_evaluation_posters.py", "scripts/evaluate_live.py",
    "scripts/package_project.py", "docs/INTEGRATION_TEST_REPORT.md",
    "docs/DEMO_GUIDE.md", "docs/GE_JIAYU_CONTRIBUTION.md",
    "evaluation/README.md", "evaluation/expected.json",
]
FILES += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "tests").glob("test_*.py"))]
FILES += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "evaluation/posters").glob("*.png"))]
FILES += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "docs").glob("integrated-*.png"))]


def main():
    for name in FILES:
        if not (ROOT / name).is_file():
            raise FileNotFoundError(name)
    with ZipFile(OUT, "w", ZIP_DEFLATED) as package:
        for name in FILES:
            package.write(ROOT / name, "SnapSched/" + name)
    with ZipFile(OUT) as package:
        names = package.namelist()
        assert package.testzip() is None
        assert len(names) == len(set(names)) == len(FILES)
        assert not any("/.venv/" in name or "/.git/" in name or
                       name.endswith(("/.env", "/secrets.toml")) for name in names)
    print(OUT)
    print(f"{len(FILES)} files, {OUT.stat().st_size:,} bytes; ZIP integrity checked.")


if __name__ == "__main__":
    main()
