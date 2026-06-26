"""Doc-quality analysis (pure, deterministic — A-pillar of Insights subsystem).

All public functions are **pure**: they take plain data and return plain data.
No DB access, no network calls.

Readability metrics use the classic Flesch formulas with a syllable-count
heuristic (vowel-group counting with silent-e correction).

Expected-section completeness covers the six canonical doc sections:
overview, install, usage, examples, API/reference, troubleshooting.

``analyze_quality`` blends all signals into a ``DocQuality`` result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.analysis.signals import DocAnalysisSignals

# ---------------------------------------------------------------------------
# Section completeness vocabulary
# ---------------------------------------------------------------------------

_EXPECTED_SECTIONS: list[tuple[str, ...]] = [
    ("overview", "introduction", "about"),
    ("install", "setup", "installation"),
    ("usage", "getting started", "getting-started", "quickstart", "quick start"),
    ("examples", "example", "tutorial"),
    ("api", "reference", "spec"),
    ("troubleshooting", "faq", "questions", "support"),
]

_SECTION_LABELS: list[str] = [
    "Overview",
    "Installation",
    "Usage",
    "Examples",
    "API/Reference",
    "Troubleshooting",
]

# ---------------------------------------------------------------------------
# Syllable heuristic
# ---------------------------------------------------------------------------

_VOWELS = frozenset("aeiouy")
_STRIP_PUNCT = re.compile(r"[^a-z]")


def _count_syllables(word: str) -> int:
    """Approximate syllable count for *word* via vowel-group counting."""
    w = _STRIP_PUNCT.sub("", word.lower())
    if not w:
        return 1
    count = 0
    prev_vowel = False
    for ch in w:
        is_v = ch in _VOWELS
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    # Common: silent terminal 'e' in a multi-syllable word
    if w.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


# ---------------------------------------------------------------------------
# Readability (Flesch / Flesch-Kincaid)
# ---------------------------------------------------------------------------

_SENT_RE = re.compile(r"[.!?]+")


def _tokenise(text: str) -> tuple[list[str], int]:
    """Return (words, sentence_count)."""
    words = text.split()
    sentences = [s for s in _SENT_RE.split(text) if s.strip()]
    return words, max(1, len(sentences))


def flesch_reading_ease(text: str) -> float:
    """Flesch Reading Ease score (higher → easier).

    Guards for empty text (returns 0.0).
    """
    words, sentence_count = _tokenise(text)
    if not words:
        return 0.0
    word_count = len(words)
    syllables = sum(_count_syllables(w) for w in words)
    return (
        206.835
        - 1.015 * (word_count / sentence_count)
        - 84.6 * (syllables / word_count)
    )


def flesch_kincaid_grade(text: str) -> float:
    """Flesch-Kincaid Grade Level (approximate school-grade reading level).

    Guards for empty text (returns 0.0).
    """
    words, sentence_count = _tokenise(text)
    if not words:
        return 0.0
    word_count = len(words)
    syllables = sum(_count_syllables(w) for w in words)
    return (
        0.39 * (word_count / sentence_count) + 11.8 * (syllables / word_count) - 15.59
    )


# ---------------------------------------------------------------------------
# Completeness
# ---------------------------------------------------------------------------


def completeness_score(heading_paths: list[list[str]]) -> float:
    """Fraction [0..1] of the six canonical sections present.

    Matched via case-insensitive substring over all heading text across
    all heading paths.
    """
    all_headings = [h.lower() for path in heading_paths for h in path]
    found = 0
    for synonyms in _EXPECTED_SECTIONS:
        if any(syn in h for h in all_headings for syn in synonyms):
            found += 1
    return round(found / len(_EXPECTED_SECTIONS), 3)


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

_H1_RE = re.compile(r"^# .+", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{1,6} ", re.MULTILINE)
_FENCE_RE = re.compile(r"```|~~~")


def structure_score(text: str) -> float:
    """Structure quality score [0..1].

    Four equal-weight checks:
    1. H1/title present.
    2. At least one fenced code block.
    3. Reasonable heading count (2–10).
    4. No paragraph exceeds 300 words.
    """
    if not text.strip():
        return 0.0

    score = 0.0

    if _H1_RE.search(text):
        score += 1.0

    if _FENCE_RE.search(text):
        score += 1.0

    heading_count = len(_HEADING_RE.findall(text))
    if 2 <= heading_count <= 10:
        score += 1.0

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs or all(len(p.split()) <= 300 for p in paragraphs):
        score += 1.0

    return round(score / 4.0, 3)


# ---------------------------------------------------------------------------
# Placeholders
# ---------------------------------------------------------------------------

_PLACEHOLDER_PATTERNS = [
    re.compile(r"\btodo\b"),
    re.compile(r"\bfixme\b"),
    re.compile(r"\btbd\b"),
    re.compile(r"coming soon"),
    re.compile(r"lorem ipsum"),
    re.compile(r"\bwip\b"),
]


def count_placeholders(text: str) -> int:
    """Count TODO, FIXME, TBD, 'coming soon', 'lorem ipsum', WIP occurrences."""
    lower = text.lower()
    return sum(len(p.findall(lower)) for p in _PLACEHOLDER_PATTERNS)


# ---------------------------------------------------------------------------
# Word count
# ---------------------------------------------------------------------------


def word_count(text: str) -> int:
    """Simple whitespace-token word count."""
    return len(text.split())


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class DocQuality:
    """Aggregated quality signals for one document."""

    quality_score: float  # weighted blend [0..1]
    readability: float  # Flesch Reading Ease
    grade_level: float  # Flesch-Kincaid grade
    completeness_score: float  # [0..1] fraction of expected sections present
    structure_score: float  # [0..1]
    word_count: int
    placeholder_count: int
    issues: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level analyzer
# ---------------------------------------------------------------------------

_THIN_THRESHOLD = 100  # words — below this the doc is flagged as thin


def analyze_quality(sig: DocAnalysisSignals) -> DocQuality:
    """Compute ``DocQuality`` from pre-gathered ``DocAnalysisSignals``.

    ``quality_score`` is a weighted blend in [0..1]:
    - 25 % readability (FRE normalised to 0–100 range → 0–1)
    - 25 % section completeness
    - 25 % structure
    - 10 % reading-level quality (low FK grade → better for docs)
    - −10 % placeholder penalty
    - −5 %  thinness penalty
    """
    text = sig.content
    wc = word_count(text)
    fre = flesch_reading_ease(text)
    fkg = flesch_kincaid_grade(text)
    comp = completeness_score(sig.heading_paths)
    struct = structure_score(text)
    ph = count_placeholders(text)

    issues: list[str] = []

    # Thinness
    if wc < _THIN_THRESHOLD:
        issues.append(f"thin: {wc} words")

    # Placeholders
    if ph > 0:
        issues.append(f"{ph} placeholder{'s' if ph > 1 else ''}")

    # Missing expected sections (only meaningful when doc has enough content)
    if wc >= _THIN_THRESHOLD:
        all_headings = [h.lower() for path in sig.heading_paths for h in path]
        for label, synonyms in zip(_SECTION_LABELS, _EXPECTED_SECTIONS):
            if not any(syn in h for h in all_headings for syn in synonyms):
                issues.append(f"missing {label} section")

    # Hard readability flag
    if wc > 0 and fre < 30:
        issues.append("very hard to read (Flesch < 30)")

    # Structure flag
    if struct < 0.5:
        issues.append("poor structure: missing H1 or code blocks")

    # --- Score components ---
    # Normalise FRE to [0,1]: typical docs range 0–100.
    fre_norm = max(0.0, min(1.0, fre / 100.0))

    # Grade-level quality: docs ideally at/below ~12th grade; penalty ramps above.
    fkg_norm = max(0.0, min(1.0, 1.0 - fkg / 20.0))

    # Placeholder penalty: each occurrence costs 5 %, capped at 100 %.
    ph_penalty = min(1.0, ph * 0.05)

    # Thinness penalty: proportional distance below the threshold.
    thin_penalty = max(0.0, 1.0 - wc / _THIN_THRESHOLD) if wc < _THIN_THRESHOLD else 0.0

    raw = (
        0.25 * fre_norm
        + 0.25 * comp
        + 0.25 * struct
        + 0.10 * fkg_norm
        - 0.10 * ph_penalty
        - 0.05 * thin_penalty
    )
    quality_score = round(max(0.0, min(1.0, raw)), 3)

    return DocQuality(
        quality_score=quality_score,
        readability=round(fre, 3),
        grade_level=round(fkg, 3),
        completeness_score=comp,
        structure_score=struct,
        word_count=wc,
        placeholder_count=ph,
        issues=issues,
    )
