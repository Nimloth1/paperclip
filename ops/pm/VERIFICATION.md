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
