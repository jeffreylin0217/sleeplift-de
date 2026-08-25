from __future__ import annotations

import subprocess
import sys

STEPS = [
    "src/pipeline/ingest.py",
    "src/pipeline/transform.py",
    "src/pipeline/build_gold.py",
    "src/pipeline/quality.py",
]


def main() -> None:
    for script in STEPS:
        cmd = [sys.executable, script]
        print("\n==>", " ".join(cmd))
        result = subprocess.run(cmd)
        if result.returncode != 0:
            sys.exit(result.returncode)
    print("\nPIPELINE COMPLETE")


if __name__ == "__main__":
    main()
