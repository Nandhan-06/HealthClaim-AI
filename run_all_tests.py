"""
run_all_tests.py
=================
Convenience script for the deliverable: "Console/log output showing all
10 sample test cases run through both implementations, including at
least one REVISE loop actually firing in the LangGraph version."

Runs both langgraph_healthclaim/main.py and crewai_healthclaim/main.py
as subprocesses, prints their output, and saves it to output/test_run_log.txt.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def run(label: str, cwd: Path) -> str:
    header = f"\n{'=' * 70}\n{label}\n{'=' * 70}\n"
    result = subprocess.run(
        [sys.executable, "main.py"], cwd=cwd, capture_output=True, text=True
    )
    body = result.stdout
    if result.returncode != 0:
        body += f"\n[exit code {result.returncode}]\n{result.stderr}"
    return header + body


def main():
    sections = [
        run("LANGGRAPH HEALTHCLAIM AI — all 10 sample cases", ROOT / "langgraph_healthclaim"),
        run("CREWAI HEALTHCLAIM AI — all 10 sample cases", ROOT / "crewai_healthclaim"),
    ]
    full_log = "\n".join(sections)
    print(full_log)

    log_path = OUTPUT_DIR / "test_run_log.txt"
    log_path.write_text(full_log, encoding="utf-8")
    print(f"\nSaved combined log to {log_path}")


if __name__ == "__main__":
    main()
