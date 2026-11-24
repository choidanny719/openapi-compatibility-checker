import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .document import DocumentError, load
from .rules import compare


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check changes to an OpenAPI 3.0 contract")
    parser.add_argument("base", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        findings = compare(load(args.base), load(args.candidate))
    except DocumentError as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for f in findings:
            print(f"{f.severity.upper()}  {f.location}  {f.message}")
        if not findings:
            print("No compatibility findings.")
    if any(f.severity == "breaking" for f in findings):
        return 1
    return 3 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
