#!/usr/bin/env bash
# Regenerate PNG and SVG from the Mermaid sources in this directory using
# @mermaid-js/mermaid-cli (npm). Graphviz `dot` does not consume Mermaid syntax.
set -euo pipefail
RepoRoot="$(cd "$(dirname "$0")/../.." && pwd)"
DiagDir="${RepoRoot}/docs/architecture"
cd "${RepoRoot}"
for base in architecture-overview architecture-user-client; do
  npx --yes @mermaid-js/mermaid-cli \
    -i "${DiagDir}/${base}.mmd" \
    -o "${DiagDir}/${base}.png" \
    -b white \
    -s 2
  npx --yes @mermaid-js/mermaid-cli \
    -i "${DiagDir}/${base}.mmd" \
    -o "${DiagDir}/${base}.svg" \
    -b white \
    -s 2
done
echo "Wrote PNG and SVG under ${DiagDir}/"
