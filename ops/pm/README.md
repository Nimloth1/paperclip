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

## Existing Cursor Desktop conversation pilot

`cursor-progress.py` observes one existing conversation, **Paperclip 列项目任务**,
and links it to the human-assigned task GON-2. This is a local, one-way progress
bridge, separate from the read-only Assistant MCP connection. It does not import
other conversations, register Cursor as an execution agent, or let Paperclip
drive the existing desktop conversation. Continue working in Cursor normally.
One actual user-sent Desktop turn has passed acceptance: all three native Hooks
ran and created the three expected progress comments; the exact reply is visible
in Paperclip, the task ended In review, and replay changed nothing. This result
applies only to the selected conversation, not automatic collection of all chats.

The official Cursor user hooks at `~/.cursor/hooks.json` call the script on
`beforeSubmitPrompt`, `afterAgentResponse`, and `stop`. Cursor watches this file
and reloads it. Every hook checks the private conversation ID before reading
credentials, state or message content. Other conversations are ignored. No
thinking hooks, shell/tool hooks, background polling or model API calls are added.
The already-approved local administrator CLI credential authorizes REST writes;
it is not copied into the hooks file or given to the model through MCP. This
credential has administrator authority: the restriction to one task is enforced
by this script, **not by a separate least-privilege server credential**. Cursor's
MCP consent remains read-only. This is a single-session pilot, not a hardened
multi-user connector.

The private binding and small outbox live in `.paperclip/cursor-progress/`.
Only bounded visible request/reply excerpts are synchronized. Common credential
patterns are redacted; this is not comprehensive DLP, and sensitive conversations
must not be added without reviewing what is transmitted. The selected source
contains only the known Paperclip read-only acceptance conversation. Original
transcripts and the live Cursor database are never modified or backed up.

| Observed event | Paperclip status | Meaning |
| --- | --- | --- |
| User submits a prompt | In progress | A new turn was submitted; not proof of subsequent model activity |
| Assistant emits a response | In progress | Visible response excerpt saved; await the turn-end event |
| Turn completes | In review | This turn ended; a human still decides whether the task is complete |
| Turn aborts | Todo | Interrupted, awaiting continuation |
| Turn errors | Blocked | Cursor reported an error |

Historical bootstrap is explicitly marked historical, including any old empty
project/task lists. The bridge never infers a completion percentage or marks
Done. Closed tasks are not reopened, and changes to the task's project/company,
source marker or assignment to an execution agent stop synchronization. There
is no crash watchdog: inspect the latest event timestamp rather than treating
In progress as a live heartbeat.

Task creation checks its exact source marker. Updates use stable comment request
IDs; a server-committed response lost in transit is reconciled before retry.
An unchanged replay leaves the task, comments and local state untouched. A
small bounded outbox retains failed events for the next event or manual flush:

```sh
python3 -B ops/pm/cursor-progress.py flush
python3 -B -m unittest discover -s ops/pm -p test_cursor_progress.py -v
```

Hooks emit valid nonblocking JSON and never inject an automatic follow-up. On
failure the Hooks output reports a safe error classification, without raw
payloads or credentials. A pending outbox alone does not schedule retries;
there is no background daemon. The pilot caps input/state files at 1 MiB,
pending events at 32, private data at 10 MiB, and sampled self peak RSS at
128 MiB, and preserves 50 GiB free on the SSD. The private binding/outbox stay
until this pilot is accepted or removed. No new dependencies are installed.

To disable the bridge, remove only the three command entries referring to
`ops/pm/cursor-progress.py` from `~/.cursor/hooks.json`, preserving any other
hooks. Keep the source and task for audit or remove this pilot's small private
binding/outbox after deciding how to retain GON-2. No Paperclip service restart,
Cursor chat migration or OAuth revocation is required.

Official event schemas: https://cursor.com/docs/hooks

## Claude Desktop progress bridge (trial, not yet connected)

`claude-progress.py` is written and unit-tested against a fake API only; it is
**not installed** and has no credential yet. Design: Claude Code's official
`UserPromptSubmit`, `Stop` and `StopFailure` hooks call it; it maps `cwd` to a
listed project (`.claude/worktrees/...` folds into the main repo; unlisted
folders are ignored before any file, credential or state is read) and appends
one comment per event to that project's single long-lived "进展" task, creating
it on first activity. Prompts keep ~200 characters, replies ~800, redacted with
the same patterns as the Cursor pilot. No model summarises anything. Status
mirrors the latest event across all conversations of the project; done or
cancelled tasks are never reopened.

It reads only `.paperclip/claude-progress/auth.json` (a dedicated
`paperclip:write` credential, no `configure`) and never falls back to the
administrator credential. Least privilege is script-enforced, as no
comment-only scope exists on the server. Conversation title is not in the hook
payload, so comments label conversations by session-ID prefix.

Tests: `python3 -B -m unittest discover -s ops/pm -p test_claude_progress.py -v`

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
