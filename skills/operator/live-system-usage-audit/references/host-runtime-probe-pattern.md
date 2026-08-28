# Host/runtime probe pattern

This reference is a reusable, read-only probe recipe for the
`live-system-usage-audit` skill. Adapt paths and service names to the target;
do not assume the current host, profile, or provider.

## 1. Snapshot header

Record:

- `TZ=<target-zone> date '+%A, %d %B %Y %H:%M:%S %Z (UTC%:z)'`
- `uname -a`
- `/etc/os-release` identity
- `uptime`
- scope and observation window

Use the user's target timezone for the report. Keep the host's timezone label
and the report timezone explicit if they differ.

## 2. Host resource batch

Run the smallest useful read-only set:

```bash
lscpu
free -h
swapon --show
df -hT
df -ih
vmstat -w 1 3
python3 -c "print(open('/proc/pressure/cpu').read().strip())"
python3 -c "print(open('/proc/pressure/memory').read().strip())"
python3 -c "print(open('/proc/pressure/io').read().strip())"
```

Use the portable `swapon --show` form first. Column/output flags vary by
version; a failed formatting variant is a probe failure, not evidence that swap
is absent. Retry with the simple command and preserve the initial error.

If installed, add a short `iostat -xz 1 3`. Interpret `vmstat`, PSI, and
`iostat` as different windows: current device utilization does not erase prior
pressure stalls, and PSI does not prove current saturation by itself.

## 3. Hermes/service batch

Use application status plus service-manager accounting:

```bash
hermes --version
hermes status --all
hermes gateway status
hermes sessions stats
hermes cron status
systemctl --user --failed --no-pager --no-legend
systemctl --user show hermes-gateway.service \
  -p MainPID -p ActiveState -p SubState -p ActiveEnterTimestamp \
  -p NRestarts -p CPUUsageNSec -p TasksCurrent -p TasksMax \
  -p MemoryCurrent -p MemoryPeak -p MemorySwapCurrent -p MemorySwapPeak \
  -p MemoryMax -p MemorySwapMax -p Restart -p OOMPolicy
ss -lntup
```

`hermes status --all` is the broad provider/channel inventory. If using
`hermes auth status`, supply its required provider argument; a usage error from
an omitted argument is not a provider-health result.

## 4. Cgroup accounting

Resolve the service cgroup without mutating the service:

```bash
CG=$(systemctl --user show hermes-gateway.service -p ControlGroup --value)
CGROOT="/sys/fs/cgroup${CG}"
for f in memory.current memory.peak memory.swap.current memory.swap.peak \
         memory.max memory.swap.max memory.events pids.current pids.max cpu.stat; do
  printf '%s=' "$f"
  cat "$CGROOT/$f" 2>&1 || true
  printf '\n'
done
```

When the agent's normal file tool is preferred, read the same files directly.
Do not call a flat `cgroup.procs` RSS sum the complete gateway footprint when
child cgroups exist. The service-manager `MemoryCurrent` and cgroup memory
files are the service-total evidence; per-process rows explain composition.

Always report both:

- main process RSS/VmSwap; and
- service/cgroup current and peak memory/swap.

Also check whether `MemoryMax`/`MemorySwapMax` are finite and inspect
`memory.events` for `oom`/`oom_kill`. A zero OOM counter means no recorded OOM,
not that the service has comfortable headroom.

## 5. Capability test pattern

For a capability that matters, collect configuration status and then run a
minimal real-path test. For the gateway's Playwright environment, resolve the
actual Hermes venv first:

```bash
PY="$HERMES_HOME/hermes-agent/venv/bin/python"
"$PY" -c 'from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); print("launched", b.version); b.close(); p.stop()'
```

Capture exit code and the decisive stderr line. Do not conclude from “browser
enabled” in a registry, from the existence of a Playwright driver, or from an
installed browser directory alone. Do not run an install or restart during this
snapshot.

The same pattern applies to providers and channels: a configured credential or
accepted scheduler request is not end-to-end success. Require the live response,
fresh execution metadata, or destination-side evidence appropriate to the
boundary.

## 6. Disk attribution

Start with filesystem authority:

```bash
df --block-size=1 -P /
df -ih /
du -x -B1 -d1 "$HOME"
du -x -B1 -d1 /var
```

If protected directories make `du` incomplete, preserve the permission errors
and label the ledger partial. For metadata-only recursive attribution, sum
`st_blocks * 512` without reading file contents. Keep these separate:

- apparent bytes;
- allocated bytes;
- filesystem `df` used/available;
- reclaim actually observed after an approved deletion.

A large `state.db`, cache, venv, backup, or evidence directory is a consumer,
not automatically a cleanup candidate. Growth requires at least two timestamped
measurements or an independent writer/growth trace.

## 7. Docker and protected resources

Run the inventory only if the current identity is authorised:

```bash
docker ps -a
 docker stats --no-stream
 docker system df
```

If the socket returns permission denied, record:

```text
DATA GAP — Docker service may be running, but container/image inventory was not
observable from this identity. Do not infer zero containers.
```

Do not add the user to the Docker group merely to complete an audit. Use an
approved read-only/root-assisted inspection later if container accounting is
required.

## 8. Log window and currentness

Use a bounded window:

```bash
journalctl --user -u hermes-gateway.service \
  --since '<start>' --until '<end>' --no-pager
```

Aggregate repeated signatures such as provider rotation, browser dependency
errors, stale-session recovery, restart events, and tool failures. Redact raw
payloads. Classify every signature as:

- reproduced by a current capability test;
- historical within the window;
- configuration-only;
- one-off watch item;
- unresolved.

Absence of a log signature is not proof of health when the path was not used.
A historical failure is not automatically a current failure.

## 9. Evidence ledger

For each claim record:

```text
ID:
Verdict: TRUE / FALSE / PARTIAL / WATCH / DATA GAP
Observation window:
Actual value:
Evidence command/path:
Raw exit/result:
Provenance: LIVE-VERIFIED / LOCAL-VERIFIED / HISTORICAL / DATA GAP
Interpretation:
What remains unproven:
Recommended next gate (no action implied):
```

Examples of honest classifications:

- `LIVE-VERIFIED — gateway active; service cgroup memory current measured`
- `PARTIAL — browser configured/enabled, direct launch failed`
- `HISTORICAL — provider rotation observed in bounded journal window; current health not proven`
- `DATA GAP — Docker socket denied; inventory unknown`
- `HYPOTHESIS — database is large; growth/leak not established`

## 10. WhatsApp-friendly final shape

Lead with:

```text
<timestamp MYT>
Verdict: <one-line operational conclusion>

Hardware:
- ...

Software/runtime:
- ...

Main risks:
1. ... — evidence ...
2. ... — evidence ...

Data gaps / failed probes:
- ...

No changes made: read-only snapshot only.
```

Use bullets rather than tables. Keep facts, interpretation, and proposed next
actions visibly separate.
