# PM deployment

This checkout is the user's fork of `paperclipai/paperclip`. Its upstream source
is on `master`; the running service uses the official, pinned npm release
`paperclipai@2026.1106.0`, not a development build of this checkout. Editing the
source does not change the running service until a source deployment is built.

## Local layout

- Checkout: `/Volumes/ssd/projects/t/paperclip`
- Published runtime: `.paperclip-runtime/` (ignored by Git)
- Dependencies: `/Volumes/ssd/frontend/t/paperclip/runtime/node_modules`, linked
  at `.paperclip-runtime/node_modules`
- npm download cache: `/Volumes/ssd/frontend/t/paperclip/npm-cache`
- Configuration: `.paperclip/instances/default/config.json` (private, ignored)
- Signing secrets: `.paperclip/service.env` (mode 600, ignored)
- Embedded PostgreSQL: `.paperclip/instances/default/db` on loopback port 54329
- Attachments: `.paperclip/instances/default/data/storage`
- Service logs: `.paperclip/logs/`

`runtime-package.json` records the release pin, and `runtime-package-lock.json`
records its resolved npm closure. They are separate from the upstream pnpm
workspace. Only the embedded-PostgreSQL hydration and published server scripts
were explicitly approved; optional unrelated native build scripts stay blocked.
The instance, its credentials,
runtime dependencies, logs, caches and database must never be committed.

## Service

The macOS LaunchAgent is `com.maeglin.paperclip`. Install the checked-in plist
in `~/Library/LaunchAgents/`, then bootstrap it in the user's GUI domain. The
service runs `run.sh`; it does not rely on a chat-owned terminal process.

```sh
launchctl list | rg 'com\.maeglin\.paperclip$'
curl --fail --silent http://127.0.0.1:8822/api/health
```

Use `launchctl kickstart -k gui/$(id -u)/com.maeglin.paperclip` to restart this
service. Stop it with `launchctl bootout gui/$(id -u)/com.maeglin.paperclip`.
Do not stop unrelated Node or PostgreSQL processes by name.

The service is authenticated and private, with its origin bound to
`127.0.0.1:8822`. Tailscale Serve provides the authenticated canonical origin at
`https://pm-haofengmac-mini.taile41bfa.ts.net:8822/`, accessible only inside the
tailnet. It preserves the existing portal proxy on port 8800. Use this HTTPS
origin for assistant OAuth and mobile access; the loopback UI and health URL
remain available on the Mac. PM currently resolves the Tailscale DNS name to a
proxy fake IP. The HTTPS origin was verified from UU with a fixed real Tailscale
address and normal certificate validation; PM's automatic DNS/proxy path remains
unverified. Do not change global proxy/DNS rules as part of this deployment.
Complete first-admin registration in the browser before connecting assistants.
Ambient model-provider API keys are cleared from the service environment;
only explicitly configured credentials should be used by future agents.
Telemetry and update checks are disabled. Automatic
database backups are disabled for the initial empty pilot; this deployment does
not yet provide recovery backups for research data.

## Desktop connections

After first-admin registration, create the desired organization and enable
Settings → Experimental → Assistant connections (MCP). Use Connectors →
Assistant Connection (MCP) to generate client-specific setup instructions.

The MCP resource is `/mcp/paperclip`. Connect Codex Desktop and Cursor with
Streamable HTTP and browser authorization. Claude Desktop's remote connectors
originate in Anthropic's cloud, so they cannot reach a private Tailscale address;
use the documented local stdio proxy for a private deployment. Reading setup
instructions alone does not install an MCP connection.

Start verification with `paperclip_connection` and project/task listing. A new
MCP connection neither imports all desktop chat history nor starts monitoring
or agent execution. Assistant connections are an upstream experimental feature.

Official references:

- https://docs.paperclip.ing/experimental/assistant-connections/
- https://docs.paperclip.ing/reference/cli/mcp/
- https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp

## Monitoring and resource budget

PM's existing Healthchecks KeepAlive probe should include this LaunchAgent and
its `/api/health` endpoint. Register the HTTP port in the host's port registry.

The initial installation is bounded to 3.5 GiB of aggregate process RSS, 5 GiB of
additional SSD space and ten minutes. Preserve at least 50 GiB of free SSD
space. Rebuildable npm cache may be removed after the installation is verified;
the database, attachments and signing secrets are not disposable caches.

Before handing off a deployment, measure a complete idle scheduler cycle with
the host's `proc-disk-writes.py`. Separate one-time installation and database
initialization writes from the steady-state service write rate.
