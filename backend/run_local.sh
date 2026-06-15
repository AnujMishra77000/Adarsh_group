#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "[error] .venv/bin/python not found. Create venv first:" >&2
  echo "  python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

# Prevent accidental imports from global/user site-packages.
export PYTHONNOUSERSITE=1
unset PYTHONPATH || true

echo "[info] Python executable: $(.venv/bin/python -c 'import sys; print(sys.executable)')"
.venv/bin/python - <<'PY'
import pydantic, pydantic_settings, uvicorn
print(f"[info] pydantic={pydantic.__version__} from {pydantic.__file__}")
print(f"[info] pydantic-settings={pydantic_settings.__version__} from {pydantic_settings.__file__}")
print(f"[info] uvicorn from {uvicorn.__file__}")
PY

exec .venv/bin/python -m uvicorn app.main:app \
  --reload \
  --reload-dir app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}"
