#!/usr/bin/env bash
# Measures the cost optimizations against a baseline on the full benchmark.
# Needs an API key in backend/.env and Docker running. Each pass costs roughly $1-3
# with gpt-4.1; the script prints the comparison table at the end.
set -euo pipefail
cd "$(dirname "$0")/../backend"
ac=.venv/bin/agentcollab

echo "== Baseline: every optimization off"
AGENTCOLLAB_RESPONSE_CACHE=false AGENTCOLLAB_LIGHT_ROLES= $ac eval --label baseline

echo "== Cheaper model for the reviewer and security agents"
AGENTCOLLAB_RESPONSE_CACHE=false AGENTCOLLAB_LIGHT_ROLES=reviewer,security \
  $ac eval --label light-models

# The response cache only helps when identical requests repeat, so it's measured on a rerun:
# the first pass fills it, the second shows what a rerun of the same tasks costs.
if [[ "${MEASURE_CACHE:-0}" == "1" ]]; then
  echo "== Response cache: first pass, then a rerun"
  AGENTCOLLAB_RESPONSE_CACHE=true AGENTCOLLAB_LIGHT_ROLES=reviewer,security \
    $ac eval --label cache-first
  AGENTCOLLAB_RESPONSE_CACHE=true AGENTCOLLAB_LIGHT_ROLES=reviewer,security \
    $ac eval --label cache-rerun
  $ac eval-compare baseline light-models cache-first cache-rerun
else
  $ac eval-compare baseline light-models
fi
