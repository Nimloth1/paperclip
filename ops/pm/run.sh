#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PAPERCLIP_HOME="$PROJECT_ROOT/.paperclip"
export PAPERCLIP_CONFIG="$PAPERCLIP_HOME/instances/default/config.json"
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export NODE_OPTIONS="--max-old-space-size=2048"
export NODE_ENV=production
export TRUST_PROXY=loopback
export PAPERCLIP_PUBLIC_URL="https://pm-haofengmac-mini.taile41bfa.ts.net:8822"
export PAPERCLIP_TELEMETRY_ENABLED=false
export PAPERCLIP_MIGRATION_PROMPT=never
export PAPERCLIP_MIGRATION_AUTO_APPLY=true
export PAPERCLIP_OPEN_ON_LISTEN=false
export NO_COLOR=1
unset OPENAI_API_KEY OPENROUTER_API_KEY ANTHROPIC_API_KEY MINIMAX_API_KEY DEEPSEEK_API_KEY XAI_API_KEY

if [[ ! -r "$PAPERCLIP_HOME/service.env" ]]; then
  echo "Missing private Paperclip environment: $PAPERCLIP_HOME/service.env" >&2
  exit 1
fi
set -a
source "$PAPERCLIP_HOME/service.env"
set +a

cd "$PROJECT_ROOT/.paperclip-runtime"
exec /opt/homebrew/bin/node --input-type=module -e 'const { startServer } = await import("@paperclipai/server"); await startServer();'
