from pathlib import Path


def test_boostrap_creates_expected_files_and_prints_message(
    tmp_path: Path, monkeypatch, capsys
):
    """bootstrap_harness should create harness/docs scaffolding and print a message."""
    monkeypatch.chdir(tmp_path)

    # import and run the function under test
    from harness.boostrap import bootstrap_harness

    bootstrap_harness()

    # directories
    assert (tmp_path / "harness").is_dir()
    assert (tmp_path / "harness" / "exec-plans").is_dir()

    # files and contents (function writes short path placeholders)
    assert (tmp_path / "harness" / "quality-score.md").exists()
    assert (tmp_path / "harness" / "invariants.md").exists()
    assert (tmp_path / "docs" / "AGENTS.md").exists()

    assert (
        tmp_path / "harness" / "quality-score.md"
    ).read_text().strip() == "./quality-score.md"
    assert (
        tmp_path / "harness" / "invariants.md"
    ).read_text().strip() == "./invariants.md"
    assert (tmp_path / "docs" / "AGENTS.md").read_text().strip() == "./AGENTS.md"

    # printed feedback
    captured = capsys.readouterr()
    assert "Harness scaffolding bootstrapped" in captured.out


def test_boostrap_is_idempotent_and_does_not_overwrite_existing_files(
    tmp_path: Path, monkeypatch, capsys
):
    """Running bootstrap twice must not overwrite existing files."""
    monkeypatch.chdir(tmp_path)

    from harness.boostrap import bootstrap_harness

    # first run creates files
    bootstrap_harness()

    invariants_path = tmp_path / "harness" / "invariants.md"
    assert invariants_path.exists()

    # modify the invariants file
    invariants_path.write_text("custom invariants\n")

    # second run should not overwrite the modified file
    bootstrap_harness()

    assert invariants_path.read_text() == "custom invariants\n"

    # function prints feedback on each invocation
    captured = capsys.readouterr()
    assert captured.out.count("Harness scaffolding bootstrapped") >= 2
