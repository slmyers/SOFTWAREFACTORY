from pathlib import Path

from tools.bootstrap_harness import ensure_harness_scaffolding


def test_ensure_harness_scaffolding_creates_expected_files(tmp_path: Path):
    created = ensure_harness_scaffolding(tmp_path)

    expected = {
        tmp_path / "docs" / "AGENTS.md",
        tmp_path / "harness" / "quality-score.md",
        tmp_path / "harness" / "invariants.md",
        tmp_path / "harness" / "exec-plans" / "current.md",
    }

    assert expected.issubset(set(created))

    for path in expected:
        assert path.exists()
        assert path.read_text().strip() != ""


def test_ensure_harness_scaffolding_is_idempotent(tmp_path: Path):
    first_created = ensure_harness_scaffolding(tmp_path)
    assert len(first_created) == 4

    invariants_path = tmp_path / "harness" / "invariants.md"
    invariants_path.write_text("custom invariants\n")

    second_created = ensure_harness_scaffolding(tmp_path)
    assert second_created == []
    assert invariants_path.read_text() == "custom invariants\n"
