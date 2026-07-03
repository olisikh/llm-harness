#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${script_dir}/.venv"
python_bin="${venv_dir}/bin/python"
pip_bin="${venv_dir}/bin/pip"
helper_py="${script_dir}/edge_tts_read.py"

if [[ ! -d "${venv_dir}" ]]; then
  python3 -m venv "${venv_dir}"
fi

if [[ ! -x "${python_bin}" ]]; then
  echo "error: missing python in ${venv_dir}" >&2
  exit 1
fi

if ! "${python_bin}" - <<'PY' >/dev/null 2>&1
import edge_tts, langid
PY
then
  "${pip_bin}" install -q --upgrade pip
  "${pip_bin}" install -q edge-tts langid
fi

exec "${python_bin}" "${helper_py}" "$@"
