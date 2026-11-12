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

The first administrator has registered and claimed the instance, and approved
the official instance-admin CLI configuration grant. The selected organization
is `Gondolin`. Assistant connections (`enablePublicMcp`) are enabled. Use
Connectors → Assistant Connection (MCP) for client setup and connection revocation.

The three desktop configurations have a `paperclip` stdio entry pointing to
`/bin/bash /Volumes/ssd/projects/t/paperclip/ops/pm/mcp.sh`. Existing entries and
preferences were preserved. The wrapper runs the published CLI proxy with
`PAPERCLIP_HOME` set to a private credential directory. Cursor has
`env: { "PAPERCLIP_MCP_CLIENT": "cursor" }` in its entry, selecting
`.paperclip/clients/cursor/` and keeping its connection separate from the
default `.paperclip/` used by the other two clients. Claude and Codex currently
have no approved MCP credentials; authorizing Cursor does not authorize them.
The administrator CLI credential is separate from all MCP connection grants.

Cursor's args explicitly include `mcp proxy --url` and the canonical MCP URL
after the wrapper path. This recreated its native connection after it had cached
an empty tool catalog from the pre-authorization attempt. Cursor's native logs
then confirmed `tools=37, status=connected` and published the tool definitions
to its active chat workspaces. A terminal proxy call alone does not qualify a
native chat integration.

`tailnet-dns.mjs` pins only the Paperclip hostname to this Mac's Tailscale IPv4
address inside that CLI process, preserving hostname/certificate validation.
It does not change system DNS, hosts files, browser settings or other hosts.
Set `PAPERCLIP_TAILNET_ADDRESS` if the host's tailnet address deliberately changes.
The authenticated MCP resource remains the canonical HTTPS origin plus
`/mcp/paperclip`. Reading setup instructions or passing MCP initialization does
not establish an authorized connection.

Cursor's first authorization used the official CLI, which requests read, write,
configuration and offline access together. The user could not find the opt-out
in the deployed consent page. That broad grant was revoked; its old access token
was confirmed rejected with HTTP 401. No project/task mutation used that grant.

The working connection instead used the same server OAuth device endpoints with
an explicit scope of `paperclip:read offline_access`, client name `Cursor read-only`,
and the existing Gondolin company ID. The user approved it in the browser. The
one-time helper is private, ignored state at
`.paperclip/clients/cursor/read-only-device.mjs`; it stores the official CLI's
credential format. The official proxy handles subsequent requests and refresh.
Do not run the default CLI login for a read-only reconnection without reviewing
its requested scopes. Verify actual scopes with `paperclip_connection`.

An existing
Mac browser's proxy/DNS path may still need a per-browser resolution override;
the CLI's pin does not modify browser behavior. The official CLI stores MCP
credentials privately under the selected home directory's `mcp/` and serializes
refresh across client processes. No model-provider API key is used by this bridge.
A separate Chrome profile under `.paperclip/browser-cursor-consent/` was opened
with a process-only host resolver rule and no proxy for the official HTTPS
consent page. Its login session is private state; it must not be committed.

The catalog contains 37 tools, including mutation tools, even for read-only
connections. Tool visibility is not permission: the server enforces scopes when
called. A configuration operation against a nonexistent project was confirmed
denied with `paperclip:configure permission is required`, without modifying data.

Small private backups of the two pre-existing client configuration files live
under `.paperclip/client-config-backups/` (approximately 64 KiB total), solely for
rollback. Keep them until all three native clients have reloaded and passed a
read-only lookup; then remove them. They contain private configuration and must
not be copied into Git or reports. Cursor's previously absent global file was
created; the backup manifest records this distinction.

After OAuth approval and client reload, start verification with
`paperclip_connection` and project/task listing. A new
MCP connection neither imports all desktop chat history nor starts monitoring
or agent execution. Assistant connections are an upstream experimental feature.

Official references:

- https://docs.paperclip.ing/experimental/assistant-connections/
- https://docs.paperclip.ing/reference/cli/mcp/
- https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp

## Project inventory and mobile pilot

The initial import created 109 project records in Gondolin and merged nine
duplicate paths. Sources were local Git repositories under both PM project
roots plus existing local Codex project registrations. This is a PM inventory,
not an inventory of PW, remote hosts or every chat application. Same GitHub
repositories are combined; SSD and explicitly registered paths take precedence
over older clones/worktrees. GitHub URLs are restricted to plain owner/repository
locations; user information and URL parameters are not copied.

Projects contain names, source paths, sanitized repository links and import
markers. Their initial status is Backlog, with actual progress explicitly marked
unverified. The import creates no execution workspaces, lead-agent assignments,
environment variables or execution commands, and does not read source bodies or
chat content. The existing paused agent was left paused.

`import-projects.py` defaults to preview. It consumes a private snapshot of local
Codex project registrations at `.paperclip/import/codex-projects.json`:

```sh
python3 ops/pm/import-projects.py
python3 ops/pm/import-projects.py --apply --demo-task
```

The official administrator CLI credential authorizes the loopback REST requests;
Cursor's read-only credential is not expanded. Source markers and project
idempotency keys prevent duplicate records. An existing same-name project
without an import marker stops the batch for review. The bounded scanner stops
at Git roots, scans at most four directory levels and 2,000 directories, and
accepts at most 250 projects. Memory, free SSD space and private-manifest guards
run between operations. No full-directory or database backup is made. Keep the
small private plan/result manifests for provenance and a possible targeted rollback.

GON-1, **手机验收：查看项目目录并创建一条待办**, belongs to the Paperclip
project and is assigned to the human user with status Backlog and no agent.
It is a manual acceptance task and starts no execution. A rerun created no
projects/tasks, preserved all entity update timestamps and did not rewrite the
plan/result manifests.

Mobile users connect Tailscale to the same tailnet, then sign in at
`https://pm-haofengmac-mini.taile41bfa.ts.net:8822/`. The current production login
page passed a 390×844 browser check without horizontal overflow or page errors.
The deployed manifest says `display: browser`; standalone PWA installation is
not qualified, despite the checkout's newer manifest saying `standalone`.
Use the mobile browser for this pilot; a home-screen shortcut is optional.
An actual phone login and task-create interaction still require user acceptance.

To create a manual task, choose **New Task**, select its project, describe the
request and acceptance criteria, choose yourself (or no agent) as assignee,
and save it in **Backlog**. Creating a task does not itself start an existing
Cursor Desktop conversation. Autonomous execution requires a separately
configured, active execution agent and its normal budget/approval controls.

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
