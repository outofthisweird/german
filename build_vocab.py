#!/usr/bin/env python3
"""Convert raw vocabulary JSONL into cards.jsonl format."""

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional
import re


ARTICLE_MAP = {"m": "der", "f": "die", "n": "das"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert raw vocabulary JSONL into cards.jsonl format",
    )
    parser.add_argument("input", help="Path to raw.jsonl input file")
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help=(
            "Path to output cards.jsonl file. If omitted, the output path is derived "
            "from the input path by replacing the first occurrence of 'raw' with 'card'."
        ),
    )
    return parser.parse_args()


def normalize_answer(text: str) -> str:
    """Normalize an answer string by trimming, lowering, and collapsing spaces."""
    return re.sub(r"\s+", " ", text.strip().lower())


def split_senses(translations: List[str]) -> List[List[str]]:
    """Split translations into sense-specific lists based on '|' separators."""
    has_pipe = any("|" in item for item in translations)
    if not has_pipe:
        return [translations]

    senses: List[List[str]] = []
    for item in translations:
        if "|" in item:
            for part in item.split("|"):
                senses.append([part.strip()])
        else:
            senses.append([item])
    return senses


def derive_output_path(input_path: str) -> str:
    """Derive output path by replacing the first 'raw' with 'card' in the filename.

    If the filename does not contain 'raw', append '_card' before the suffix.
    """

    path = Path(input_path)
    name = path.name

    if "raw" in name:
        new_name = name.replace("raw", "card", 1)
    else:
        stem = path.stem
        suffix = path.suffix
        new_name = f"{stem}_card{suffix}" if suffix else f"{stem}_card"

    return str(path.with_name(new_name))


def build_entry(
    idx: int,
    lemma: str,
    gender: Optional[str],
    translations: List[str],
    level: str,
    topic: str,
    language: str,
) -> dict:
    article = ARTICLE_MAP.get(gender) if gender is not None else None
    full_form = f"{article} {lemma}" if article else None

    prompt = ", ".join(translations)

    accepted = (
        [normalize_answer(full_form)] if full_form is not None else [normalize_answer(lemma)]
    )

    return {
        "id": idx,
        "lemma": lemma,
        "gender": gender,
        "full_form": full_form,
        "translations_ko": translations,
        "prompt_ko": prompt,
        "accepted_answers_de": accepted,
        "level": level,
        "topic": topic,
        "language": language,
    }


def process_lines(lines: Iterable[str]) -> List[dict]:
    entries: List[dict] = []
    current_id = 1

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

        try:
            lemma = data["lemma"]
            gender = data.get("gender")
            translations = data["translations_ko"]
            level = data["level"]
            topic = data["topic"]
            language = data["language"]
        except KeyError as exc:
            raise ValueError(f"Missing required field {exc.args[0]!r} on line {line_number}") from exc

        if not isinstance(translations, list):
            raise ValueError(f"translations_ko must be a list on line {line_number}")

        for sense_translations in split_senses(translations):
            entry = build_entry(
                current_id,
                lemma=lemma,
                gender=gender,
                translations=sense_translations,
                level=level,
                topic=topic,
                language=language,
            )
            entries.append(entry)
            current_id += 1

    return entries


def write_output(entries: List[dict], output_path: str) -> None:
    try:
        with open(output_path, "w", encoding="utf-8") as outfile:
            for entry in entries:
                json.dump(entry, outfile, ensure_ascii=False)
                outfile.write("\n")
    except OSError as exc:
        raise OSError(f"Failed to write output file: {exc}") from exc


def main() -> None:
    args = parse_args()

    output_path = args.output or derive_output_path(args.input)

    try:
        with open(args.input, "r", encoding="utf-8") as infile:
            entries = process_lines(infile)
    except OSError as exc:
        print(f"Failed to read input file: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    try:
        write_output(entries, output_path)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
