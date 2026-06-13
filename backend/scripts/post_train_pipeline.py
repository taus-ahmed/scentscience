"""
Run calibration then audit in sequence — call this right after test_model.py finishes.
  python scripts/post_train_pipeline.py
"""
import subprocess, sys
from pathlib import Path

base = Path(__file__).parent

def run(script: str) -> int:
    print(f"\n{'='*60}\nRunning: {script}\n{'='*60}")
    result = subprocess.run(
        [sys.executable, str(base / script)],
        cwd=str(base.parent),
    )
    return result.returncode

if __name__ == "__main__":
    rc1 = run("calibrate_longevity.py")
    if rc1 != 0:
        print(f"calibrate_longevity.py failed (rc={rc1}), aborting.")
        sys.exit(rc1)
    rc2 = run("model_audit2.py")
    sys.exit(rc2)
