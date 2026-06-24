"""Pure-logic tests for document summary extraction."""

from app.processing.summarize import extractive_summary, generate_summary


def test_extracts_first_paragraph_skipping_heading():
    md = "# Redis Migration\n\nHow to move from Redis to Garnet safely.\n"
    assert extractive_summary(md) == "How to move from Redis to Garnet safely."


def test_skips_front_matter_and_code_fences():
    md = "---\ntitle: x\n---\n# Title\n```\ncode block\n```\nReal description here.\n"
    assert extractive_summary(md) == "Real description here."


def test_truncates_long_text():
    md = "# T\n\n" + "word " * 100
    out = extractive_summary(md, max_len=40)
    assert len(out) <= 40
    assert out.endswith("…")


def test_heading_only_doc_falls_back_to_heading():
    assert extractive_summary("# Just A Heading") == "Just A Heading"


def test_empty_content():
    assert extractive_summary("") == ""


def test_generate_summary_without_ai_uses_extractive():
    md = "# T\n\nA concise description.\n"
    assert generate_summary(md, use_ai=False) == "A concise description."
