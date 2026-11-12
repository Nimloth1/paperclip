#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PAPERCLIP_HOME="$PROJECT_ROOT/.paperclip"
export PAPERCLIP_CONFIG="$PAPERCLIP_HOME/instances/default/config.json"
export PAPERCLIP_TELEMETRY_ENABLED=false
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
unset OPENAI_API_KEY OPENROUTER_API_KEY ANTHROPIC_API_KEY MINIMAX_API_KEY DEEPSEEK_API_KEY XAI_API_KEY
unset NODE_TLS_REJECT_UNAUTHORIZED

if [[ $# -eq 0 ]]; then
  set -- mcp proxy --url "https://pm-haofengmac-mini.taile41bfa.ts.net:8822/mcp/paperclip"
fi

cd "$PROJECT_ROOT/.paperclip-runtime"
exec /opt/homebrew/bin/node --max-old-space-size=256 \
  --import "$PROJECT_ROOT/ops/pm/tailnet-dns.mjs" \
  "$PROJECT_ROOT/.paperclip-runtime/node_modules/paperclipai/dist/index.js" "$@"
