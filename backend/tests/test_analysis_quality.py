"""Pure unit tests for quality.py — no DB, no Azure, no network.

Constructs ``DocAnalysisSignals`` literals directly and asserts on
representative cases: a well-structured doc vs a thin placeholder-filled doc.
"""

from __future__ import annotations

from app.analysis.signals import DocAnalysisSignals
from app.analysis.quality import (
    DocQuality,
    analyze_quality,
    completeness_score,
    count_placeholders,
    flesch_kincaid_grade,
    flesch_reading_ease,
    structure_score,
    word_count,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sig(
    content: str,
    heading_paths: list[list[str]] | None = None,
) -> DocAnalysisSignals:
    return DocAnalysisSignals(
        doc_id="test/doc.md",
        repo="test",
        path="doc.md",
        content=content,
        heading_paths=heading_paths or [],
        commit_sha="abc123",
        commit_date=None,
        last_verified_sha=None,
    )


# ---------------------------------------------------------------------------
# Representative documents
# ---------------------------------------------------------------------------

GOOD_DOC = """\
# Overview

This guide explains how to install and use the tool in your project.

## Installation

Run `pip install mytool` to get started with the package.

## Usage

```python
import mytool
result = mytool.run()
print(result)
```

## Examples

Here is a simple end-to-end example showing the main workflow.

## API Reference

See `mytool.Client` for the full API surface and configuration options.

## Troubleshooting

If you get errors, check the logs and verify the configuration.
"""

GOOD_HEADING_PATHS = [
    ["Overview"],
    ["Installation"],
    ["Usage"],
    ["Examples"],
    ["API Reference"],
    ["Troubleshooting"],
]

THIN_DOC = "TODO: add content here."

# ---------------------------------------------------------------------------
# flesch_reading_ease
# ---------------------------------------------------------------------------


def test_fre_nonempty_returns_float():
    fre = flesch_reading_ease("The cat sat on the mat.")
    assert isinstance(fre, float)
    assert -50.0 < fre < 150.0


def test_fre_empty_returns_zero():
    assert flesch_reading_ease("") == 0.0


def test_fre_whitespace_only_returns_zero():
    assert flesch_reading_ease("   \n\t  ") == 0.0


def test_fre_simple_sentence_higher_than_complex():
    simple = flesch_reading_ease("The cat sat on the mat.")
    complex_ = flesch_reading_ease(
        "The epistemological ramifications of multidimensional phenomenological "
        "investigation necessitate comprehensive interdisciplinary methodological "
        "reconsideration."
    )
    # simpler text should score higher (easier to read)
    assert simple > complex_


# ---------------------------------------------------------------------------
# flesch_kincaid_grade
# ---------------------------------------------------------------------------


def test_fkg_empty_returns_zero():
    assert flesch_kincaid_grade("") == 0.0


def test_fkg_returns_float():
    grade = flesch_kincaid_grade("The cat sat on the mat.")
    assert isinstance(grade, float)


# ---------------------------------------------------------------------------
# completeness_score
# ---------------------------------------------------------------------------


def test_completeness_all_sections_present():
    paths = [
        ["Overview"],
        ["Installation"],
        ["Usage"],
        ["Examples"],
        ["API Reference"],
        ["Troubleshooting"],
    ]
    assert completeness_score(paths) == 1.0


def test_completeness_empty_returns_zero():
    assert completeness_score([]) == 0.0


def test_completeness_partial_between_zero_and_one():
    paths = [["Overview"], ["Installation"]]
    score = completeness_score(paths)
    assert 0.0 < score < 1.0


def test_completeness_case_insensitive():
    # mixed-case synonyms should still match
    paths = [
        ["INTRODUCTION"],
        ["SETUP"],
        ["QUICKSTART"],
        ["EXAMPLES"],
        ["REFERENCE"],
        ["FAQ"],
    ]
    assert completeness_score(paths) == 1.0


def test_completeness_nested_headings():
    # Heading path may have multiple levels; all heading text is searched.
    paths = [["Getting Started", "Installation Guide"]]
    score = completeness_score(paths)
    assert score > 0.0


# ---------------------------------------------------------------------------
# structure_score
# ---------------------------------------------------------------------------


def test_structure_good_doc_above_half():
    assert structure_score(GOOD_DOC) > 0.5


def test_structure_empty_returns_zero():
    assert structure_score("") == 0.0


def test_structure_whitespace_returns_zero():
    assert structure_score("   ") == 0.0


def test_structure_scores_in_range():
    for text in [GOOD_DOC, THIN_DOC, "# Title\n\nSome text."]:
        s = structure_score(text)
        assert 0.0 <= s <= 1.0


# ---------------------------------------------------------------------------
# count_placeholders
# ---------------------------------------------------------------------------


def test_placeholders_zero_for_clean_doc():
    assert count_placeholders("This is a clean document.") == 0


def test_placeholders_detects_all_patterns():
    text = "TODO fix this. FIXME broken. TBD. Coming soon. Lorem ipsum. WIP"
    assert count_placeholders(text) >= 5


def test_placeholders_case_insensitive():
    assert count_placeholders("todo") >= 1
    assert count_placeholders("FIXME") >= 1
    assert count_placeholders("COMING SOON") >= 1


# ---------------------------------------------------------------------------
# word_count
# ---------------------------------------------------------------------------


def test_word_count_basic():
    assert word_count("hello world foo") == 3


def test_word_count_empty():
    assert word_count("") == 0


def test_word_count_whitespace_only():
    assert word_count("   \n\t  ") == 0


# ---------------------------------------------------------------------------
# analyze_quality — integration
# ---------------------------------------------------------------------------


def test_analyze_quality_returns_dataclass():
    result = analyze_quality(_sig(GOOD_DOC, GOOD_HEADING_PATHS))
    assert isinstance(result, DocQuality)


def test_analyze_quality_good_doc():
    result = analyze_quality(_sig(GOOD_DOC, GOOD_HEADING_PATHS))
    assert result.quality_score > 0.3
    assert result.word_count > 10
    assert result.placeholder_count == 0


def test_analyze_quality_thin_doc_issues():
    result = analyze_quality(_sig(THIN_DOC))
    assert any("thin" in issue for issue in result.issues)
    assert result.placeholder_count >= 1


def test_analyze_quality_thin_lower_than_good():
    thin_result = analyze_quality(_sig(THIN_DOC))
    good_result = analyze_quality(_sig(GOOD_DOC, GOOD_HEADING_PATHS))
    assert thin_result.quality_score < good_result.quality_score


def test_analyze_quality_scores_in_range():
    for content, paths in [(GOOD_DOC, GOOD_HEADING_PATHS), (THIN_DOC, [])]:
        result = analyze_quality(_sig(content, paths))
        assert 0.0 <= result.quality_score <= 1.0
        assert 0.0 <= result.completeness_score <= 1.0
        assert 0.0 <= result.structure_score <= 1.0


def test_analyze_quality_placeholder_reduces_score():
    clean = "This document explains how the system works in detail.\n" * 20
    dirty = clean + "\nTODO FIXME TBD WIP coming soon lorem ipsum"
    clean_sig = _sig(clean)
    dirty_sig = _sig(dirty)
    assert (
        analyze_quality(clean_sig).quality_score
        >= analyze_quality(dirty_sig).quality_score
    )
