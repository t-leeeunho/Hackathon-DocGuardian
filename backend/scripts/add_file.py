"""Add a user file or pasted text into the live system (drop-off intake).

    python -m scripts.add_file path\\to\\notes.md
    python -m scripts.add_file --name quickstart.md --text "# Quickstart\n..."
"""

from __future__ import annotations

import argparse

from app.ingestion.intake import UnsupportedFormatError, ingest_content, ingest_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a user document (drop-off intake)")
    parser.add_argument("path", nargs="?", help="path to a text/markdown file")
    parser.add_argument("--name", help="logical name when using --text")
    parser.add_argument("--text", help="paste content directly instead of a file")
    parser.add_argument("--namespace", default="user", help="top-level namespace (default: user)")
    args = parser.parse_args()

    try:
        if args.text is not None:
            if not args.name:
                parser.error("--name is required when using --text")
            result = ingest_content(args.name, args.text, args.namespace)
        elif args.path:
            result = ingest_file(args.path, args.namespace)
        else:
            parser.error("provide a file path or --text with --name")
    except UnsupportedFormatError as exc:
        parser.error(str(exc))

    print(
        f"Added {result['doc_id']}: {result['chunks']} chunks, "
        f"{result['edges']} edges embedded and stored."
    )


if __name__ == "__main__":
    main()
