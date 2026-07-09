"""German editorial style engine tests."""

from __future__ import annotations

from plex_music_enhancer.editorial import GermanEditorialStyleEngine


def test_style_engine_detects_llm_cliches() -> None:
    """Common LLM phrases should be reported as style issues."""
    diagnostics = GermanEditorialStyleEngine().analyze(
        "Das Album zeigt eindrucksvoll eine gelungene Mischung aus Pop und Rock. "
        "Es nimmt den Hörer mit auf eine emotionale Reise.",
    )

    assert diagnostics.llm_cliches in {"MEDIUM", "HIGH"}
    assert "zeigt eindrucksvoll" in diagnostics.detected_cliches
    assert "gelungene Mischung" in diagnostics.detected_cliches
    assert "LLM_CLICHES" in diagnostics.issues


def test_style_engine_detects_repetition_and_sentence_openings() -> None:
    """Repeated openings, words, artists, and album names should be visible."""
    diagnostics = GermanEditorialStyleEngine().analyze(
        "Pastel Blues erschien 1965. "
        "Pastel Blues verbindet Jazz und Blues. "
        "Pastel Blues zeigt Blues, Blues und nochmals Blues. "
        "Nina Simone prägt das Album, Nina Simone führt es, Nina Simone rahmt es.",
        artist="Nina Simone",
        album="Pastel Blues",
    )

    assert "pastel blues" in diagnostics.repetitive_sentence_openings
    assert diagnostics.repeated_album_names > 0
    assert diagnostics.repeated_artist_names > 0
    assert diagnostics.repetition in {"MEDIUM", "HIGH"}
    assert "REPETITION" in diagnostics.issues


def test_style_engine_reports_readability_and_lexical_diversity() -> None:
    """Readability metrics should expose sentence rhythm and vocabulary diversity."""
    diagnostics = GermanEditorialStyleEngine().analyze(
        "Die Aufnahme entstand in einem konzentrierten Produktionsumfeld und verbindet "
        "sparsamen Jazz mit zurückhaltendem Soul. Zugleich ordnet sie die Sängerin "
        "in eine Phase ein, in der interpretatorische Präzision wichtiger wirkt als "
        "äußerer Effekt.",
    )

    assert diagnostics.average_sentence_length > 8
    assert diagnostics.lexical_diversity > 0.6
    assert diagnostics.readability_score > 70
    assert diagnostics.vocabulary_diversity in {"GOOD", "VERY GOOD", "EXCELLENT"}


def test_style_engine_detects_list_like_and_passive_voice() -> None:
    """List-style writing and passive constructions should be diagnosed."""
    diagnostics = GermanEditorialStyleEngine().analyze(
        "1. Artist: Nina Simone. 2. Album: Pastel Blues. "
        "Das Album wurde 1965 veröffentlicht und wurde später eingeordnet.",
    )

    assert diagnostics.list_like_writing is True
    assert diagnostics.passive_voice in {"LOW", "MEDIUM", "HIGH"}
    assert "LIST_LIKE_WRITING" in diagnostics.issues


def test_style_engine_polishes_cliches_without_changing_facts() -> None:
    """Polishing should only adjust wording and preserve names, dates, and titles."""
    result = GermanEditorialStyleEngine().improve(
        "Pastel Blues zeigt eindrucksvoll, wie Nina Simone 1965 Jazz und Blues verbindet.",
        artist="Nina Simone",
        album="Pastel Blues",
    )

    assert result.changed is True
    assert "zeigt eindrucksvoll" not in result.text
    assert "Pastel Blues" in result.text
    assert "Nina Simone" in result.text
    assert "1965" in result.text
    assert "Jazz" in result.text
    assert "Blues" in result.text


def test_style_engine_varies_repeated_album_sentence_starts() -> None:
    """Optional polishing should reduce mechanical repeated openings."""
    result = GermanEditorialStyleEngine().improve(
        "Das Album erschien 1965. "
        "Das Album verbindet Jazz und Blues. "
        "Das Album nutzt sparsame Arrangements.",
    )

    assert result.text.count("Das Album") == 1
    assert "Musikalisch verbindet Jazz und Blues." in result.text


def test_style_engine_detects_artist_biography_issues() -> None:
    """Artist biographies should report generic openings and jumpy chronology."""
    diagnostics = GermanEditorialStyleEngine().analyze(
        "Nina Simone ist eine Sängerin und ist bekannt für Jazz. "
        "Sie wurde 1970 international erwähnt, war 1954 bereits aktiv und blieb 1965 präsent. "
        "Sie ist Musikerin, war Pianistin und wurde bekannt durch mehrere Aufnahmen.",
        artist="Nina Simone",
    )

    assert "WEAK_ARTIST_OPENING" in diagnostics.issues
    assert "GENERIC_BIOGRAPHY" in diagnostics.issues
    assert "CHRONOLOGICAL_JUMPS" in diagnostics.issues
    assert "SIMPLE_VERB_OVERUSE" in diagnostics.issues


def test_style_engine_rewards_stronger_artist_narrative() -> None:
    """Artist biographies with narrative flow should avoid artist-specific issue codes."""
    diagnostics = GermanEditorialStyleEngine().analyze(
        "Als klassisch ausgebildete Pianistin verband Nina Simone Jazz, Soul und Blues "
        "mit einer unverwechselbaren interpretatorischen Strenge. Nach frühen Auftritten "
        "entwickelte sie ein Repertoire, das musikalische Präzision mit politischem "
        "Bewusstsein verband und ihre Rolle innerhalb der afroamerikanischen "
        "Musikgeschichte sichtbar machte.",
        artist="Nina Simone",
    )

    assert "WEAK_ARTIST_OPENING" not in diagnostics.issues
    assert "GENERIC_BIOGRAPHY" not in diagnostics.issues
