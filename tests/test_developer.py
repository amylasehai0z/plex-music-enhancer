"""Developer-mode diagnostics tests."""

from __future__ import annotations

from json import dumps, loads

from typer.testing import CliRunner

from plex_music_enhancer.cli import app
from plex_music_enhancer.developer import (
    DeveloperAnalyzer,
    PromptDebugReader,
    PromptMetaReader,
    ReviewLogReader,
)

runner = CliRunner()


def test_prompt_reader_reports_stats(tmp_path) -> None:
    """Prompt reader should compute stats from the prompt and metadata files."""
    prompt_path = tmp_path / "openai_prompt.txt"
    meta_path = tmp_path / "openai_prompt_meta.json"
    prompt_path.write_text("Ein kurzer Prompt mit Inhalt.", encoding="utf-8")
    meta_path.write_text(
        dumps({"prompt_version": "1.2", "max_prompt_characters": 20000}),
        encoding="utf-8",
    )

    document = PromptDebugReader(prompt_path, meta_path).read()

    assert document.exists is True
    assert document.stats.characters == len("Ein kurzer Prompt mit Inhalt.")
    assert document.stats.words == 5
    assert document.stats.budget == 20000
    assert document.stats.prompt_version == "1.2"


def test_meta_reader_handles_malformed_json(tmp_path) -> None:
    """Meta reader should not expose malformed JSON errors to the CLI."""
    meta_path = tmp_path / "openai_prompt_meta.json"
    meta_path.write_text("{not json", encoding="utf-8")

    document = PromptMetaReader(meta_path).read()

    assert document.exists is True
    assert document.payload == {}


def test_review_reader_parses_sections(tmp_path) -> None:
    """Review reader should parse sectioned temporary review logs."""
    log_path = tmp_path / "plex_review.log"
    log_path.write_text(
        "\n".join(
            [
                "header",
                "=== PROMPT QUALITY =================================================",
                "Prompt efficiency: 91",
                "=== VERIFICATION ===================================================",
                "Conflicts: none",
            ]
        ),
        encoding="utf-8",
    )

    document = ReviewLogReader(log_path).read()

    assert document.exists is True
    assert document.section("prompt quality") == "Prompt efficiency: 91"
    assert document.section("verification") == "Conflicts: none"


def test_developer_analyzer_explains_prompt_decisions(tmp_path) -> None:
    """Developer analyzer should summarize existing debug artifacts."""
    prompt_path = tmp_path / "openai_prompt.txt"
    meta_path = tmp_path / "openai_prompt_meta.json"
    log_path = tmp_path / "plex_review.log"
    prompt_path.write_text("Prompt " * 100, encoding="utf-8")
    meta_path.write_text(
        dumps(
            {
                "prompt_characters": 700,
                "estimated_prompt_tokens": 175,
                "max_prompt_characters": 20000,
            }
        ),
        encoding="utf-8",
    )
    log_path.write_text(_review_log(), encoding="utf-8")
    analyzer = DeveloperAnalyzer(
        prompt_reader=PromptDebugReader(prompt_path, meta_path),
        meta_reader=PromptMetaReader(meta_path),
        review_reader=ReviewLogReader(log_path),
    )

    explanation = analyzer.explain()
    doctor = analyzer.doctor()

    assert explanation.prompt_size == 700
    assert explanation.used_sources["Wikipedia"] == "used"
    assert "Duplicate genres" in explanation.prompt_decisions["removed"]
    assert "Legacy" in explanation.missed_opportunities
    assert doctor.checks["promptDump"] == "PASS"
    assert doctor.checks["reviewLog"] == "PASS"


def test_debug_prompt_json_cli(monkeypatch, tmp_path) -> None:
    """Debug prompt command should export JSON without running AI."""
    prompt_path = tmp_path / "openai_prompt.txt"
    meta_path = tmp_path / "openai_prompt_meta.json"
    prompt_path.write_text("Prompt text", encoding="utf-8")
    meta_path.write_text(dumps({"prompt_version": "1.0"}), encoding="utf-8")
    monkeypatch.setattr(
        "plex_music_enhancer.developer.readers.PROMPT_DEBUG_DUMP_PATH",
        prompt_path,
    )
    monkeypatch.setattr(
        "plex_music_enhancer.developer.readers.PROMPT_DEBUG_METADATA_PATH",
        meta_path,
    )

    result = runner.invoke(app, ["debug", "prompt", "--json"])

    assert result.exit_code == 0
    payload = loads(result.output)
    assert payload["content"] == "Prompt text"
    assert payload["stats"]["promptVersion"] == "1.0"


def test_debug_review_section_cli(monkeypatch, tmp_path) -> None:
    """Debug review command should render selected sections."""
    log_path = tmp_path / "plex_review.log"
    log_path.write_text(_review_log(), encoding="utf-8")
    monkeypatch.setattr("plex_music_enhancer.developer.readers.REVIEW_DEBUG_LOG_PATH", log_path)

    result = runner.invoke(app, ["debug", "review", "--section", "coverage"])

    assert result.exit_code == 0
    assert "Coverage: 81%" in result.output


def _review_log() -> str:
    """Return a representative review debug log."""
    return "\n".join(
        [
            "=== PROMPT BUDGET ==================================================",
            "Wikipedia: 3000 chars, 750 tokens, 49%",
            "Discogs: 300 chars, 75 tokens, 5%",
            "=== USED SOURCES ===================================================",
            "Wikipedia: used",
            "Discogs: used",
            "Last.fm: omitted",
            "=== PROMPT DECISIONS ===============================================",
            "Included",
            "✓ Historical significance",
            "",
            "Removed",
            "- Duplicate genres",
            "",
            "Trimmed",
            "- Existing biography (42%)",
            "=== PROMPT QUALITY =================================================",
            "Prompt redundancy: LOW",
            "Prompt efficiency: 91",
            "=== EDITORIAL COVERAGE =============================================",
            "Evidence available",
            "✓ Major works",
            "✓ Legacy",
            "",
            "Output coverage",
            "✓ Major works",
            "✗ Legacy",
            "=== EVIDENCE COVERAGE ==============================================",
            "High-value evidence: 4",
            "Used: 3",
            "Coverage: 81%",
            "Missed: Legacy",
            "=== VERIFICATION ===================================================",
            "Conflicts: none",
        ]
    )
