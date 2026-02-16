# harness/bootstrap.py
from pathlib import Path


def bootstrap_harness():
    base = Path("harness")
    base.mkdir(exist_ok=True)
    (base / "exec-plans").mkdir(exist_ok=True)

    # quality-score.md
    if not (base / "quality-score.md").exists():
        (base / "quality-score.md").write_text("./quality-score.md")

    # invariants.md
    if not (base / "invariants.md").exists():
        (base / "invariants.md").write_text("./invariants.md")

    # docs/AGENTS.md
    docs = Path("docs")
    docs.mkdir(exist_ok=True)
    if not (docs / "AGENTS.md").exists():
        (docs / "AGENTS.md").write_text("./AGENTS.md")

    print("✅ Harness scaffolding bootstrapped")


# Templates as triple-quoted strings (full content from above)
