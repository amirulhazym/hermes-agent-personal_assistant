# Live one-shot system check — delta vs baseline

Recurring pattern when the user asks "recheck our system usage" or quotes an
old monitoring report ("check ketiga 20:18 MYT") and asks how things look
now. Verified live 2026-08-11 on the Tencent Lighthouse VPS (2 vCPU / 1.9Gi RAM).

## Step 0 — Identify the baseline

If the user pastes an old report, locate its source session FIRST with
`session_search` (search distinctive phrases like "perubahan angin",
"session reconciliation", model names, threshold values). The old report
sets the baseline numbers to compare against. Do not answer without knowing
either the baseline or the user's reference point.

## Step 1 — Batch independent probes into parallel calls

Two terminal calls in one batch cover 90% of the report:

Call A (resource snapshot):
```
echo "== TIME =="; TZ=Asia/Kuala_Lumpur date "+%A %Y-%m-%d %H:%M %Z"
echo "== LOAD =="; uptime; nproc
echo "== MEM =="; free -m
echo "== DISK =="; df -h / /tmp 2>/dev/null
echo "== INODES =="; df -i /
echo "== TMP =="; du -sh /tmp; du -sh /tmp/<artifact>*
```

Call B (processes / health):
```
echo "== TOP RSS =="; ps -eo pid,ppid,rss,etime,comm --sort=-rss | head -15
echo "== OLD PID =="; ps -p <previous-gateway-pid> -o pid,ppid,rss,etime,cmd 2>/dev/null || echo "PID <prev> GONE"
echo "== NEW BINDS =="; ss -tlnp
echo "== PROC COUNT =="; ps -e --no-headers | wc -l
```

## Gateway restart detection (never assume from memory)

- `ps -p <old_pid>` — if GONE, the gateway restarted since the last check.
- Find the new PID: `pgrep -af 'hermes_cli.main gateway'`. New PID + `etime`
  ≈ elapsed uptime since restart.
- Confirm restart evidence: `~/.hermes/logs/gateway-exit-diag.log` mtime and
  `gateway.log` rotation (agent.log.1 etc.) timestamps.
- WA bridge node is usually a CHILD of the gateway (PPID = gateway PID) —
  check `ss -tlnp` for the node listing port 3000 and its PID.

## Memory pressure attribution — leak vs active work

Before concluding "memory leak", run the parent chain:

```
ps -o pid,ppid,rss,etime,cmd -p <suspicious-pid>
ps -o pid,ppid,rss,etime,cmd --ppid <parent-pid>
```

- New child processes (playwright driver, LSP servers) with recent etime =
  active work by another session, NOT a leak. RAM will release when the
  session settles — say that instead of recommending intervention.
- Same PID + RSS growing across checks with no new children = real leak
  candidate.
- Threshold anchors: MemAvailable < 500MB = alert threshold (see
  system-self-monitor SKILL.md). Report margin vs threshold, don't just give
  the number.

## Health endpoints

- WA bridge: `curl -s -m 5 http://127.0.0.1:3000/health` →
  `{"status":"connected","queueLength":N,"uptime":s}`. queueLength 0 =
  no backlog. Note the bridge's own uptime (it restarts independently of the
  gateway).

## Disk delta attribution

- Inode count delta (`df -i`) tells created-vs-deleted: inodes up = new
  files, inodes down = cleanup happened.
- `du -sh /tmp/* | sort -rh | head -8` attributes the delta to specific
  artifacts (update staging folders, snapshot dirs, leftover test dirs).
- Distinguish durable vs reclaimable: active-work artifacts vs long-standing
  leftovers (claude-code-templates, hermes-fix, pdfenv, searxng_test).

## Reporting format (user-tested, WhatsApp)

Header per section, emoji-per-status, raw numbers with arrow deltas
(`668Mi → 1.08Gi`), explicit verdict on any open question from the previous
report, and a closing line that intervention waits for the user's word —
observation-only is the default stance. See 2026-08-11 session for the
worked example (memory pressure resolved as predicted once the other
session's work settled; gateway had restarted — PID changed).