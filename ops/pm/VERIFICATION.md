# Deployment verification — 2026-11-12

## Delivered

- Fork: `https://github.com/Nimloth1/paperclip`, default branch `master`.
- Checkout: `/Volumes/ssd/projects/t/paperclip`; upstream remote retained.
- Runtime: official `paperclipai@2026.1106.0` and matching server package.
- Persistent host LaunchAgent: `com.maeglin.paperclip`.
- API/UI: `http://127.0.0.1:8822/`, authenticated private mode.
- Tailscale Serve HTTPS 8822, preserving the existing HTTP 8800 proxy.
- Existing PM KeepAlive Healthchecks probe includes the service's label and
  `/api/health`; no additional scheduled job or notification channel created.

## Actual checks

- Fork confirmed against the correct upstream parent; initial checkout was
  0 ahead / 0 behind origin and had no open PRs.
- Runtime package versions checked; instance configuration validated against the
  published configuration schema.
- Shell syntax and LaunchAgent plist validation passed.
- Host loopback `/api/health` returned `status=ok`, `authenticated/private`,
  `bootstrap_pending`.
- Headless Google Chrome loaded the first-admin page, with no page script errors.
- Cross-host HTTPS health request from UU passed with certificate validation
  and the hostname explicitly resolved to PM's real Tailscale IP. The certificate
  was issued successfully through Tailscale.
- The host's regular fake-IP DNS path for this name failed; global DNS/proxy
  settings were left unchanged. Use loopback on PM until that path is resolved.
- The new host health-probe entry returned healthy. The aggregate probe was
  triggered through its existing LaunchAgent and reported `status=ok ok=35/35`.
- The service was restarted through its own LaunchAgent. The PID changed and
  `/api/health` returned `status=ok` again after startup.
- The running Paperclip process was checked for ambient provider-key variable
  names; none of the explicitly cleared provider API variables remained.

## Measured resources

- Installation: 410.1 seconds; sampled aggregate process RSS peak 873.5 MiB.
- Installed dependencies: approximately 2.7 GiB on external SSD. The task's
  rebuildable npm download cache was removed after verification, recovering
  approximately 1,515.9 MiB according to free-space delta.
- Embedded database after initialization: approximately 87 MiB.
- Idle observation: 438.7 seconds, covering the scheduler and a PostgreSQL
  checkpoint cycle, using the host `proc-disk-writes.py` snapshots and diff.
- Node plus observed PostgreSQL descendants wrote 274,432 bytes (0.2617 MiB)
  in that window, approximately 0.0503 GiB/day if that idle rate persists.
- Whole-host writes were larger: external SSD 134.83 MiB, internal Data
  322.15 MiB, VM 521.19 MiB in that window. Concurrent applications and swap
  were present; those totals are not attributed to Paperclip. Process counters
  are not a claim of complete physical-volume attribution.

These are idle-pilot measurements, not a forecast for active agent workloads,
attachments, or future database growth. No paid model task was started.

## Desktop setup follow-up

The user completed registration and first-instance-admin claim. Health now
reports `bootstrapStatus=ready`.

- Added a Paperclip-only CLI DNS pin; real HTTPS health returned 200 with normal
  TLS verification. An unrelated `localhost` DNS lookup retained its ordinary
  behavior.
- The shared stdio proxy returned a valid MCP initialize response.
- Added `paperclip` to Claude Desktop, Codex Desktop, and Cursor configuration.
  Parsed comparisons proved existing settings/servers were preserved. Config
  files are mode 600; small rollback backups stay private and ignored.
- `codex mcp get paperclip --json` confirmed the enabled stdio command and args.

Administrator CLI consent is complete: `/api/cli-auth/me` confirms instance-admin
access. The existing organization is `Gondolin`; no duplicate was created.
Assistant connections (`enablePublicMcp`) were enabled through the authenticated
settings API. Other experimental settings were preserved.

Cursor now selects an isolated credential home through
`PAPERCLIP_MCP_CLIENT=cursor`. Both default and Cursor proxy modes pass stdio
initialization. Claude and Codex have no approved MCP credential. Cursor's
read-only OAuth device consent is complete. `paperclip_connection` confirms only
`paperclip:read` and `offline_access` for Gondolin. The official CLI proxy returned
successful project and task lists, both empty. Credential mode is 600; the default
shared MCP home still has zero credentials.

The initial full-scope grant was revoked and the old token returned HTTP 401.
A first read-only helper attempt omitted required protocol metadata during its
post-consent check, so it did not persist the token. That attempt may leave an
unused read-only connection entry in Paperclip; it is not used by any desktop.
The corrected helper uses the official proxy for MCP calls. No upstream app
source or packaged runtime was patched.

The catalog still advertises 37 tools for read-only connections. A configuration
call against a nonexistent project was denied for missing `paperclip:configure`
before any mutation. No project, task, agent or model execution was started.

The user's first Cursor report confirmed reads through the same official proxy,
but explicitly said the native `user-paperclip` namespace was unavailable. Native
logs still showed zero tools, including after toggling the server. This was not
counted as native-call acceptance.

Cursor's launch args now explicitly include `mcp proxy --url` and the canonical
MCP URL. This created a fresh native connection. At 17:40:50 local time, native
logs changed from zero tools to `tools=37, status=connected`; the MCP filesystem
writer published all 37 definitions to the active chat workspaces. No client
restart, new consent, application patch or additional permission was used.

Native-call acceptance is complete. The user reported that a new Cursor chat
used the native `user-paperclip` tools successfully, without terminal or script
substitution: `paperclip_connection` identified Nimloth1 and Gondolin with only
`paperclip:read` and `offline_access`; `paperclip_list_projects` returned an empty
list; `paperclip_search_tasks` with limit 100 and offset 0 returned an empty list.
This user-confirmed native read, together with the inspected native discovery
logs and direct proxy checks above, qualifies the Cursor read-only integration.

Claude/Codex authorization and native checks remain deferred. Initialization and
a recognized config alone are not evidence of authorized task access.

## Project import and mobile pilot

- Imported 109 projects from local PM Git repositories and Codex-registered
  directories; nine duplicate paths were combined. No other host was scanned.
- Verified zero imported lead-agent assignments, execution workspaces or
  execution policies. Actual progress is unverified and initially Backlog.
- Created GON-1 as a human-assigned Backlog task under the Paperclip project,
  with no agent assignee. The existing agent remains paused.
- Rerunning `--apply --demo-task` created zero projects and zero tasks, skipped
  all 109 projects and reused GON-1. All project/task update timestamps and both
  private plan/result manifest modification times were unchanged.
- The importer sampled self peak RSS at 33.5 MiB for initial import and 33.3 MiB
  on the no-op rerun, within the 128 MiB budget. SSD free space was 466.8 GiB
  before import, above the enforced 50 GiB reserve. Private import metadata and
  the mobile screenshot total approximately 154 KiB before write snapshots.
- Cursor's unchanged read-only proxy sees all 109 imported projects and GON-1.
- Headless Chrome at 390×844 loaded the production HTTPS sign-in page with
  status 200, no page errors and scroll width equal to viewport width (390).
  Browser-side manifest fetch returned 200, name Paperclip, display `browser`.
  An initial manifest check through Playwright's separate Node request client
  failed because it did not inherit Chromium's process-only DNS rule; this was
  not evidence of a phone/service outage. The browser-side request passed.
- Actual phone sign-in/task creation and standalone PWA installation remain
  unqualified. The deployed manifest differs from the source checkout; the
  packaged runtime was not patched to change installation behavior.
- A 329.5-second host write observation covered the import, no-op rerun,
  read checks and a PostgreSQL checkpoint cycle. The persistent Paperclip Node
  and observed PostgreSQL descendants wrote 2,768,896 bytes (2.64 MiB), including
  the one-time import. This is not an idle-rate or daily-write projection.
  Whole-host volume deltas were much larger (SSD 483.39 MiB, Data 142.57 MiB,
  VM 353.19 MiB) with concurrent applications and swap; these are not attributed
  to Paperclip. Short-lived importer/browser children may exit between the
  snapshots, so this is not complete physical-write attribution. Only the
  task's small private snapshot pair and summary were retained.

No upstream application source was changed, so the upstream full test suite and
source build were not run. This evidence qualifies the pinned packaged runtime
and host deployment only.

## Existing Cursor Desktop conversation progress pilot

The selected existing conversation is **Paperclip 列项目任务**. Its small JSONL
transcript contains the user's previously confirmed native MCP acceptance turn
and a `turn_ended: success` record. A point lookup of its metadata key in Cursor's
read-only SQLite connection confirmed the existing title and completed status;
there was no database-wide content scan, copy or mutation. The existing 4.4 GB
database was not exported. Only this conversation is allowlisted.

- Created the human-assigned task GON-2 under the existing Paperclip project.
  Its source marker and original request link it to that conversation; the
  first comment is explicitly historical, not a current project-count report.
- The first task-creation request timed out after two seconds, but the server
  had committed it. A read-only reconciliation found the source-marked GON-2;
  bootstrap then reused it rather than creating another task. First-time setup
  now allows a 20-second timeout, while normal Hooks use short calls and a small
  retry outbox. No automatic blind POST retry was introduced.
- Replayed historical bootstrap twice. Both returned `unchanged: true`;
  GON-2 remained In review with one comment and its original
  `updatedAt=2026-11-12T09:48:05.100Z`. The private state modification time was
  unchanged. The timed no-op run took 0.07 seconds, peak RSS 31,817,728 bytes
  (30.34 MiB), and reported zero block output operations.
- Installed three native user Hooks. Cursor 3.29.9's existing Hooks channel
  logged a configuration reload and `Loaded 3 user hook(s) for steps:
  beforeSubmitPrompt, afterAgentResponse, stop` at 09:48:07 UTC. The private
  `~/.cursor/hooks.json` was previously absent and is mode 600. Existing
  Claude-compatible or project hooks were not edited.
- Ten focused standard-library tests passed: unrelated conversations leave no
  state and read no credentials; submitted/replied/stopped turns map to the
  intended states; replay creates no duplicate or state rewrite; offline events
  recover in order; a committed-but-lost response does not duplicate comments;
  late responses cannot regress a completed turn; closed/reassigned tasks are
  protected; abortion and error do not claim completion; basic secret redaction
  and length bounds work; hook failures return valid allow JSON without logging
  prompt contents; a full outbox is not overwritten.
- A desktop Accessibility check found the selected chat's known native MCP
  response. The attempted read-only acceptance prompt stopped **before typing
  or sending** because the input had an existing draft. The draft was left
  untouched, and the user was asked to send one harmless turn in that existing
  chat. At this point live events were unqualified; discovery, historical
  bootstrap and fixture tests were not counted as live acceptance. The user
  later sent that turn, and the real-event result is recorded below.
- Cursor's OAuth scope was not expanded. The write bridge reads the existing
  approved administrator CLI credential, so its single-task scope is a local
  code restriction, not a new server-side least-privilege token. No credential
  was copied into Hooks, source or Git. The only execution agent, 丞相, remains
  paused and GON-2 has no agent assignee.
- A 390.2-second host observation covered bootstrap, no-op checks and a database
  checkpoint. Persistent Paperclip Node and observed PostgreSQL descendants
  wrote 1,257,472 bytes (1.20 MiB). Short-lived bridge children are not included
  in those endpoint snapshots; the separate timed no-op check above covers the
  bridge's no-change behavior. Private pilot files were about 20 KiB before
  the final snapshots. This bootstrap window is not a daily-write forecast.
  Whole-host volume writes were SSD 7,319.02 MiB, Data 164.55 MiB, VM zero.
  Unrelated pre-existing Python processes wrote approximately 1,559 MiB and
  sftp 193 MiB; a substantial remaining physical-volume gap is unattributed
  (endpoint counters miss exited/root writers and mmap attribution). These
  host totals are not assigned to Paperclip or claimed fully reconciled.

No upstream application/runtime source, execution adapters, scheduled tasks or
services were changed. Full source build and upstream application suites were
not run for this standalone PM integration script.

### Real Desktop turn acceptance — 2026-11-12 21:27 JST

The user sent the requested harmless message in the same existing Cursor
conversation and reported receiving a reply. Read-only inspection then found:

- The original local transcript has the new user request, the exact assistant
  reply `CURSOR_PAPERCLIP_SYNC_OK`, and `turn_ended: success`.
- Cursor's native Hooks output records this script on `beforeSubmitPrompt`,
  `afterAgentResponse`, and `stop`. All three returned exit code 0; their
  durations were 353 ms, 160 ms and 240 ms respectively.
- Paperclip's API has three new comments from those events. Submission was
  saved at 12:27:02.159 UTC, response at 12:27:05.072 UTC, and stop at
  12:27:05.315 UTC. The response comment contains the exact acceptance reply.
  The task now has four comments including the older historical bootstrap.
  Its final state is In review, with no execution-agent assignee. The local
  event queue is empty. No manual flush or synthetic event was used to produce
  these three live comments.
- A subsequent explicit replay of the same real stop event emitted `{}` and
  preserved the task timestamp, task status, four-comment count, and local
  state modification time. This replay verifies deduplication; it is separate
  from the original automatic Desktop events.
- The existing execution agent remains paused. No bridge code, OAuth grant,
  scheduled task, or service configuration changed during this acceptance.
  New write measurements were not taken retroactively for events that had
  already happened. The earlier bootstrap resource measurement is not presented
  as a measurement of this live turn.

This qualifies **one-way, event-driven progress reporting for this allowlisted
existing Cursor Desktop conversation**. It does not qualify automatic discovery
of other conversations, Claude/Codex Desktop integration, two-way control,
mobile approval, or any native Paperclip Desktop-session import feature. PR #1
remains a draft for this deliberately narrow pilot; it has not been merged or
expanded to other conversations.
