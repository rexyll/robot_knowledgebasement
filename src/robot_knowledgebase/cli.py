"""Command-line utilities for inspecting and chunking local Markdown files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from robot_knowledgebase import __version__
from robot_knowledgebase.ingest import chunk_document, load_markdown


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="robot-kb",
        description="Utilities for the Robot Knowledge Basement.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_parser = commands.add_parser("inspect", help="Inspect a Markdown knowledge file.")
    inspect_parser.add_argument("path", type=Path)

    chunk_parser = commands.add_parser("chunk", help="Split a Markdown file into text chunks.")
    chunk_parser.add_argument("path", type=Path)
    chunk_parser.add_argument("--chunk-size", type=int, default=1000)
    chunk_parser.add_argument("--overlap", type=int, default=150)

    return parser


def main() -> None:
    """Run the CLI."""
    args = _build_parser().parse_args()
    document = load_markdown(args.path)

    if args.command == "inspect":
        print(
            json.dumps(
                {
                    "document_id": document.document_id,
                    "title": document.title,
                    "source": document.source,
                    "characters": len(document.content),
                    "metadata": document.metadata,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    chunks = chunk_document(document, chunk_size=args.chunk_size, overlap=args.overlap)
    print(
        json.dumps(
            [
                {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            ],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
