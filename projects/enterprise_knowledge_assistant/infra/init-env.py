"""Create private local development configuration with independent random secrets; never overwrite an existing file."""

import argparse
import os
import secrets
from pathlib import Path


def main() -> None:
    """Fill only CHANGE_ME placeholders; leave provider mode/key/model explicitly opt-in and print no secrets."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".env"))
    args = parser.parse_args()
    template = Path(__file__).resolve().parents[1] / ".env.example"
    lines = []
    for line in template.read_text().splitlines():
        if line.endswith("=CHANGE_ME"):
            key = line.split("=", 1)[0]
            line = key + "=" + secrets.token_hex(32)
        lines.append(line)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write("\n".join(lines) + "\n")
    print(
        "Private development configuration created; stub mode makes no provider calls."
    )


if __name__ == "__main__":
    main()
