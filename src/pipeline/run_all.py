import subprocess
import sys

STEPS = [
    ["python", "src/pipeline/ingest.py"],
    ["python", "src/pipeline/transform.py"],
    ["python", "src/pipeline/build_gold.py"],
    ["python", "src/pipeline/quality.py"],
]

def main():
    for cmd in STEPS:
        print("\n==>", " ".join(cmd))
        r = subprocess.run(cmd)
        if r.returncode != 0:
            sys.exit(r.returncode)
    print("\nALL DONE ✅")

if __name__ == "__main__":
    main()
