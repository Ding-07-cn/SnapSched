"""Compatibility entrypoint for Nicole's original review-page launch command.

Keep one review screen and one event format; the integrated implementation is
app.py. Original Part C work is retained in Git history and the merged branch.
"""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().with_name("app.py")), run_name="__main__")
