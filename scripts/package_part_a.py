"""Package only shareable project files; never include .git, .venv or secrets."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'SnapSched_Part_A_Interface_2026-10-21.zip'
files=[
    '.gitignore','README.md','README_INTERFACE.md','app.py','interface_state.py',
    'integrations.py','requirements.txt','requirements-ui.txt',
    'samples/demo_poster.png','scripts/create_sample_poster.py','scripts/package_part_a.py',
    'tests/test_app.py','tests/test_interface_state.py',
    '.github/workflows/ui-tests.yml','.streamlit/config.toml',
    'docs/PART_A_TEST_REPORT.md','docs/GE_JIAYU_CONTRIBUTION.md',
    'docs/part-a-interface.jpg','docs/part-a-mobile.jpg',
]
with ZipFile(OUT,'w',ZIP_DEFLATED) as z:
    for name in files:
        z.write(ROOT/name,'SnapSched/'+name)
with ZipFile(OUT) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(files)
    assert not any('/.venv/' in name or '/.git/' in name or name.endswith('.env') for name in z.namelist())
print(OUT)
print(f'{len(files)} files, {OUT.stat().st_size:,} bytes; ZIP integrity checked.')
