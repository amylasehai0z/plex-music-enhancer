"""German editorial style analysis and conservative polishing."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from re import IGNORECASE, findall, search, split, sub
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StyleRating = Literal["EXCELLENT", "VERY GOOD", "GOOD", "FAIR", "POOR"]
RepetitionLevel = Literal["NONE", "LOW", "MEDIUM", "HIGH"]


class GermanStyleDiagnostics(BaseModel):
    """Structured diagnostics for German encyclopedia-style album prose."""

    model_config = ConfigDict(frozen=True)

    sentence_variation: StyleRating
    vocabulary_diversity: StyleRating
    repetition: RepetitionLevel
    readability: StyleRating
    llm_cliches: RepetitionLevel
    passive_voice: RepetitionLevel
    overall_style: StyleRating
    readability_score: int = Field(ge=0, le=100)
    average_sentence_length: float = Field(ge=0)
    average_paragraph_length: float = Field(ge=0)
    lexical_diversity: float = Field(ge=0, le=1)
    repeated_words: dict[str, int] = Field(default_factory=dict)
    repeated_artist_names: int = Field(default=0, ge=0)
    repeated_album_names: int = Field(default=0, ge=0)
    repetitive_sentence_openings: list[str] = Field(default_factory=list)
    detected_cliches: list[str] = Field(default_factory=list)
    unnatural_transitions: list[str] = Field(default_factory=list)
    overly_short_sentences: int = Field(default=0, ge=0)
    overly_long_sentences: int = Field(default=0, ge=0)
    list_like_writing: bool = False
    issues: list[str] = Field(default_factory=list)


class GermanStyleResult(BaseModel):
    """Polished text plus diagnostics for the original/generated prose."""

    model_config = ConfigDict(frozen=True)

    text: str
    diagnostics: GermanStyleDiagnostics
    changed: bool = False


class GermanEditorialStyleEngine:
    """Analyze and conservatively polish German generated album descriptions."""

    def __init__(self, replacements: dict[str, str] | None = None) -> None:
        """Create a style engine with optional cliché replacements."""
        self._replacements = {**DEFAULT_CLICHE_REPLACEMENTS, **(replacements or {})}

    def analyze(
        self,
        text: str,
        *,
        artist: str | None = None,
        album: str | None = None,
    ) -> GermanStyleDiagnostics:
        """Return structured style diagnostics without modifying text."""
        normalized = _normalize_whitespace(text)
        sentences = _sentences(normalized)
        words = _words(normalized)
        repeated_words = _repeated_content_words(words)
        sentence_lengths = [len(_words(sentence)) for sentence in sentences]
        average_sentence_length = _average(sentence_lengths)
        average_paragraph_length = _average(
            len(_words(paragraph)) for paragraph in _paragraphs(normalized)
        )
        lexical_diversity = _lexical_diversity(words)
        repetitive_openings = _repetitive_sentence_openings(sentences)
        cliches = _detected_cliches(normalized)
        passive_count = _passive_voice_count(normalized)
        list_like = _is_list_like(normalized)
        unnatural_transitions = _unnatural_transitions(sentences)
        overly_short = sum(1 for length in sentence_lengths if 0 < length < 6)
        overly_long = sum(1 for length in sentence_lengths if length > 32)
        artist_count = _name_repetition_count(normalized, artist)
        album_count = _name_repetition_count(normalized, album)

        sentence_variation_score = _sentence_variation_score(
            repetitive_openings=repetitive_openings,
            sentences=len(sentences),
            repeated_names=artist_count + album_count,
        )
        vocabulary_score = _vocabulary_score(
            lexical_diversity=lexical_diversity,
            repeated_words=repeated_words,
            cliches=cliches,
        )
        readability_score = _readability_score(
            average_sentence_length=average_sentence_length,
            overly_short=overly_short,
            overly_long=overly_long,
            list_like=list_like,
            transition_count=len(unnatural_transitions),
        )
        repetition_score = _repetition_score(
            repeated_words=repeated_words,
            repetitive_openings=repetitive_openings,
            repeated_names=artist_count + album_count,
        )
        passive_score = max(0, 100 - (passive_count * 18))
        cliche_score = max(0, 100 - (len(cliches) * 18))
        overall_score = round(
            (
                sentence_variation_score
                + vocabulary_score
                + readability_score
                + repetition_score
                + passive_score
                + cliche_score
            )
            / 6
        )

        issues = _issues(
            repetitive_openings=repetitive_openings,
            repeated_words=repeated_words,
            artist_count=artist_count,
            album_count=album_count,
            cliches=cliches,
            passive_count=passive_count,
            list_like=list_like,
            overly_short=overly_short,
            overly_long=overly_long,
            unnatural_transitions=unnatural_transitions,
        )
        issues.extend(
            _artist_biography_issues(
                normalized,
                sentences=sentences,
                artist=artist,
                album=album,
            )
        )

        return GermanStyleDiagnostics(
            sentence_variation=_style_rating(sentence_variation_score),
            vocabulary_diversity=_style_rating(vocabulary_score),
            repetition=_repetition_level(100 - repetition_score),
            readability=_style_rating(readability_score),
            llm_cliches=_repetition_level(len(cliches) * 22),
            passive_voice=_repetition_level(passive_count * 22),
            overall_style=_style_rating(overall_score),
            readability_score=readability_score,
            average_sentence_length=round(average_sentence_length, 2),
            average_paragraph_length=round(average_paragraph_length, 2),
            lexical_diversity=round(lexical_diversity, 3),
            repeated_words=repeated_words,
            repeated_artist_names=artist_count,
            repeated_album_names=album_count,
            repetitive_sentence_openings=repetitive_openings,
            detected_cliches=cliches,
            unnatural_transitions=unnatural_transitions,
            overly_short_sentences=overly_short,
            overly_long_sentences=overly_long,
            list_like_writing=list_like,
            issues=issues,
        )

    def improve(
        self,
        text: str,
        *,
        artist: str | None = None,
        album: str | None = None,
    ) -> GermanStyleResult:
        """Return conservatively polished text and diagnostics."""
        original = text
        polished = _normalize_whitespace(text)
        for phrase, replacement in self._replacements.items():
            polished = sub(
                rf"\b{phrase}\b",
                replacement,
                polished,
                flags=IGNORECASE,
            )
        polished = _remove_duplicate_sentence_starts(polished)
        diagnostics = self.analyze(polished, artist=artist, album=album)
        return GermanStyleResult(
            text=polished,
            diagnostics=diagnostics,
            changed=polished != original,
        )


DEFAULT_CLICHES = (
    "zeigt eindrucksvoll",
    "beeindruckt durch",
    "zeichnet sich aus",
    "gilt als",
    "nimmt den Hörer mit",
    "verschmilzt",
    "gelungene Mischung",
    "facettenreich",
    "vielschichtig",
    "emotionale Reise",
)

DEFAULT_CLICHE_REPLACEMENTS = {
    "zeigt eindrucksvoll": "zeigt",
    "beeindruckt durch": "arbeitet mit",
    "zeichnet sich aus": "ist geprägt",
    "nimmt den Hörer mit": "entwickelt",
    "verschmilzt": "verbindet",
    "gelungene Mischung": "Verbindung",
    "facettenreich": "vielgestaltig",
    "vielschichtig": "differenziert",
    "emotionale Reise": "dramaturgische Entwicklung",
}

STOP_WORDS = {
    "aber",
    "als",
    "am",
    "an",
    "auch",
    "auf",
    "bei",
    "das",
    "dem",
    "den",
    "der",
    "des",
    "die",
    "ein",
    "eine",
    "einem",
    "einen",
    "einer",
    "es",
    "für",
    "im",
    "in",
    "ist",
    "mit",
    "und",
    "von",
    "zu",
}


def _normalize_whitespace(text: str) -> str:
    """Normalize spacing without changing prose content."""
    lines = [sub(r"[ \t]+", " ", line).strip() for line in text.strip().splitlines()]
    paragraphs = [line for line in lines if line]
    return "\n\n".join(paragraphs)


def _paragraphs(text: str) -> list[str]:
    """Return non-empty paragraphs."""
    return [paragraph.strip() for paragraph in split(r"\n\s*\n", text) if paragraph.strip()]


def _sentences(text: str) -> list[str]:
    """Return sentence-like chunks."""
    return [sentence.strip() for sentence in split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _words(text: str) -> list[str]:
    """Return normalized word tokens."""
    return findall(r"\b[\wÄÖÜäöüß-]+\b", text.casefold())


def _average(values: Iterable[int]) -> float:
    """Return an average for an iterable of integers."""
    selected = list(values)
    if not selected:
        return 0.0
    return sum(selected) / len(selected)


def _lexical_diversity(words: list[str]) -> float:
    """Return vocabulary diversity excluding common function words."""
    content = [word for word in words if word not in STOP_WORDS and len(word) > 2]
    if not content:
        return 0.0
    return len(set(content)) / len(content)


def _repeated_content_words(words: list[str]) -> dict[str, int]:
    """Return repeated content words that affect style."""
    content = [word for word in words if word not in STOP_WORDS and len(word) > 4]
    counts = Counter(content)
    return dict(sorted((word, count) for word, count in counts.items() if count >= 3))


def _sentence_opening(sentence: str) -> str | None:
    """Return a normalized two-word sentence opening."""
    words = _words(sentence)
    if len(words) < 2:
        return None
    return " ".join(words[:2])


def _repetitive_sentence_openings(sentences: list[str]) -> list[str]:
    """Return sentence openings repeated at least twice."""
    openings = [opening for sentence in sentences if (opening := _sentence_opening(sentence))]
    counts = Counter(openings)
    return sorted(opening for opening, count in counts.items() if count >= 2)


def _detected_cliches(text: str) -> list[str]:
    """Return detected common LLM-style phrases."""
    lowered = text.casefold()
    return [phrase for phrase in DEFAULT_CLICHES if phrase.casefold() in lowered]


def _passive_voice_count(text: str) -> int:
    """Return a rough German passive voice count."""
    patterns = (
        r"\bwurde(?:n)?\b[^.!?]{0,60}\bge\w+t\b",
        r"\bwurde(?:n)?\b[^.!?]{0,60}\b\w+(?:iert|t)\b",
        r"\bwird\b[^.!?]{0,60}\bge\w+t\b",
        r"\bworden\b",
    )
    return sum(len(findall(pattern, text.casefold())) for pattern in patterns)


def _is_list_like(text: str) -> bool:
    """Return whether text resembles a list rather than prose."""
    return bool(search(r"(?m)^\s*([-*+]|\d+\.)\s+", text)) or text.count(";") >= 5


def _unnatural_transitions(sentences: list[str]) -> list[str]:
    """Return transition markers that often sound mechanical."""
    markers = (
        "darüber hinaus",
        "des weiteren",
        "zusammenfassend",
        "abschließend",
        "insgesamt lässt sich sagen",
    )
    joined = " ".join(sentences).casefold()
    return [marker for marker in markers if marker in joined]


def _name_repetition_count(text: str, name: str | None) -> int:
    """Return excessive name repetitions beyond the first two mentions."""
    if not name:
        return 0
    pattern = sub(r"\s+", r"\\s+", name.strip())
    count = len(findall(rf"\b{pattern}\b", text, flags=IGNORECASE))
    return max(0, count - 2)


def _sentence_variation_score(
    *,
    repetitive_openings: list[str],
    sentences: int,
    repeated_names: int,
) -> int:
    """Return sentence variation score."""
    if sentences <= 1:
        return 70
    return max(0, 100 - (len(repetitive_openings) * 22) - (repeated_names * 8))


def _vocabulary_score(
    *,
    lexical_diversity: float,
    repeated_words: dict[str, int],
    cliches: list[str],
) -> int:
    """Return vocabulary diversity score."""
    base = round(lexical_diversity * 100)
    return max(0, min(100, base - (len(repeated_words) * 8) - (len(cliches) * 6)))


def _readability_score(
    *,
    average_sentence_length: float,
    overly_short: int,
    overly_long: int,
    list_like: bool,
    transition_count: int,
) -> int:
    """Return readability score tuned for concise German encyclopedia prose."""
    score = 100
    if average_sentence_length < 8:
        score -= 18
    elif average_sentence_length > 26:
        score -= 14
    score -= overly_short * 8
    score -= overly_long * 12
    score -= 18 if list_like else 0
    score -= transition_count * 6
    return max(0, min(100, score))


def _repetition_score(
    *,
    repeated_words: dict[str, int],
    repetitive_openings: list[str],
    repeated_names: int,
) -> int:
    """Return repetition score."""
    penalty = sum(count - 2 for count in repeated_words.values()) * 8
    penalty += len(repetitive_openings) * 18
    penalty += repeated_names * 8
    return max(0, 100 - penalty)


def _style_rating(score: int) -> StyleRating:
    """Return a display rating for a score."""
    if score >= 90:
        return "EXCELLENT"
    if score >= 80:
        return "VERY GOOD"
    if score >= 68:
        return "GOOD"
    if score >= 50:
        return "FAIR"
    return "POOR"


def _repetition_level(score: int) -> RepetitionLevel:
    """Return qualitative level for issue intensity."""
    if score <= 0:
        return "NONE"
    if score < 25:
        return "LOW"
    if score < 55:
        return "MEDIUM"
    return "HIGH"


def _issues(
    *,
    repetitive_openings: list[str],
    repeated_words: dict[str, int],
    artist_count: int,
    album_count: int,
    cliches: list[str],
    passive_count: int,
    list_like: bool,
    overly_short: int,
    overly_long: int,
    unnatural_transitions: list[str],
) -> list[str]:
    """Return stable diagnostic issue codes."""
    issues: list[str] = []
    if repetitive_openings:
        issues.append("REPETITIVE_SENTENCE_OPENINGS")
    if repeated_words or artist_count or album_count:
        issues.append("REPETITION")
    if cliches:
        issues.append("LLM_CLICHES")
    if passive_count:
        issues.append("PASSIVE_VOICE")
    if list_like:
        issues.append("LIST_LIKE_WRITING")
    if overly_short:
        issues.append("OVERLY_SHORT_SENTENCES")
    if overly_long:
        issues.append("OVERLY_LONG_SENTENCES")
    if unnatural_transitions:
        issues.append("UNNATURAL_TRANSITIONS")
    return issues


def _artist_biography_issues(
    text: str,
    *,
    sentences: list[str],
    artist: str | None,
    album: str | None,
) -> list[str]:
    """Return diagnostics specific to artist biographies."""
    if album is not None:
        return []

    issues: list[str] = []
    lowered = text.casefold()
    if _has_generic_artist_opening(sentences, artist):
        issues.append("WEAK_ARTIST_OPENING")
    if _has_generic_biography_language(lowered):
        issues.append("GENERIC_BIOGRAPHY")
    if _has_chronological_jumps(sentences):
        issues.append("CHRONOLOGICAL_JUMPS")
    if _overuses_simple_artist_verbs(lowered):
        issues.append("SIMPLE_VERB_OVERUSE")
    return issues


def _has_generic_artist_opening(sentences: list[str], artist: str | None) -> bool:
    """Return whether an artist biography starts like a dictionary entry."""
    if not sentences:
        return True
    first = sentences[0].casefold()
    name = artist.casefold() if artist else ""
    generic_prefixes = (
        f"{name} ist " if name else "",
        f"{name} war " if name else "",
        "der künstler ist ",
        "die künstlerin ist ",
        "die band ist ",
        "der sänger ist ",
        "die sängerin ist ",
    )
    return any(prefix and first.startswith(prefix) for prefix in generic_prefixes)


def _has_generic_biography_language(lowered: str) -> bool:
    """Return whether prose relies on generic biography wording."""
    phrases = (
        "ist bekannt für",
        "wurde bekannt durch",
        "gehört zu den bekanntesten",
        "zählt zu den bedeutendsten",
    )
    return any(phrase in lowered for phrase in phrases)


def _has_chronological_jumps(sentences: list[str]) -> bool:
    """Return whether year mentions move backwards without a transition."""
    years: list[int] = []
    for sentence in sentences:
        years.extend(int(year) for year in findall(r"\b(?:19|20)\d{2}\b", sentence))
    if len(years) < 3:
        return False
    return any(current < previous for previous, current in zip(years, years[1:], strict=False))


def _overuses_simple_artist_verbs(lowered: str) -> bool:
    """Return whether a biography leans too heavily on simple linking verbs."""
    simple_verbs = sum(lowered.count(f" {verb} ") for verb in ("ist", "war", "wurde"))
    sentence_count = max(1, len(_sentences(lowered)))
    return simple_verbs >= 5 and simple_verbs / sentence_count > 1.2


def _remove_duplicate_sentence_starts(text: str) -> str:
    """Lightly vary repeated 'Das Album' sentence starts without changing facts."""
    sentences = _sentences(text)
    replacements = ["Musikalisch", "Innerhalb der Einordnung", "In der Produktion"]
    rewritten: list[str] = []
    album_start_count = 0
    for sentence in sentences:
        if sentence.casefold().startswith("das album "):
            album_start_count += 1
            if album_start_count > 1:
                replacement = replacements[(album_start_count - 2) % len(replacements)]
                sentence = sub(r"^Das Album", replacement, sentence)
        rewritten.append(sentence)
    return " ".join(rewritten) if rewritten else text
