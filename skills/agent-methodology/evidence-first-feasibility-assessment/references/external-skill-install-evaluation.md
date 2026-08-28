# External Skill / Plugin Evaluation — Hermes Recipe

Use this reference when evaluating a GitHub-hosted agent skill or plugin before installing it into a live Hermes profile.

## Required evidence split

Do not collapse these into one claim:

- Installation route: the manager fetched, scanned, and wrote the expected files.
- Activation route: the agent exposes the skill/command and loads it in a fresh session.
- User outcome: the skill improves the user's actual task performance without losing correctness, safety, provenance, or required detail.

The first can be live-tested in a temporary home. The second normally needs a fresh-session test. The third needs a controlled A/B comparison.

## Hermes temporary-install recipe

Use a disposable `HERMES_HOME`; never use the active profile for the first install test:

```bash
rm -rf /tmp/hermes-skill-test
mkdir -p /tmp/hermes-skill-test
HERMES_HOME=/tmp/hermes-skill-test hermes skills inspect <identifier>
HERMES_HOME=/tmp/hermes-skill-test hermes skills install <identifier> --yes
HERMES_HOME=/tmp/hermes-skill-test hermes skills list
find /tmp/hermes-skill-test/skills -maxdepth 4 -type f -printf '%P\\n' | sort
cat /tmp/hermes-skill-test/skills/.hub/lock.json
```

For a direct GitHub source, prefer a commit-pinned raw URL when reproducibility is more important than automatic updates:

```text
https://raw.githubusercontent.com/<owner>/<repo>/<commit-sha>/path/to/SKILL.md
```

After installation, hash the source entry file and installed entry file:

```bash
sha256sum /tmp/source/SKILL.md /tmp/hermes-skill-test/skills/<name>/SKILL.md
cmp -s /tmp/source/SKILL.md /tmp/hermes-skill-test/skills/<name>/SKILL.md
```

Record the scanner's raw `Verdict`, any findings, the final `Decision`, the installed file list, `source`, `identifier`, `trust_level`, `scan_verdict`, and `content_hash` from `.hub/lock.json`.

## 2026-07-31 worked evidence

Artifact: `ayghri/i-have-adhd`, Hermes entry file `skills/i-have-adhd/SKILL.md`.

Upstream state checked:

- Main commit: `34f746dda9664fb5ea52149be5dbab2adc6e60d3`
- No GitHub latest release was returned (HTTP 404), so `main` is a moving target.
- The skill declares `disable-model-invocation: true`; this supports an on-demand-first recommendation, but does not prove live activation in WhatsApp.

Registry identifier test:

```text
hermes skills install ayghri/i-have-adhd/skills/i-have-adhd --yes
```

Observed raw result:

```text
Running security scan...
Verdict: SAFE
  MEDIUM supply_chain SKILL.md:40 "Good: Run npm install jsonwebtoken..."
Decision: ALLOWED — Allowed (community source, safe verdict)
Installed: i-have-adhd
Files: SKILL.md, agents/gemini.toml, agents/openai.yaml
```

Direct commit-pinned URL test:

```text
hermes skills install https://raw.githubusercontent.com/ayghri/i-have-adhd/34f746dda9664fb5ea52149be5dbab2adc6e60d3/skills/i-have-adhd/SKILL.md --yes
```

Observed raw result:

```text
Verdict: SAFE
Decision: ALLOWED — Allowed (community source, safe verdict)
Installed: i-have-adhd
Files: SKILL.md
```

The source clone, registry installation, and pinned URL installation produced the same entry-file SHA-256:

```text
cae8c063977214b372c6897b7c93ac8faa573214a8635896f767e3bac092adf8
```

Interpretation:

- `INSTALLATION VALIDATED` for both routes in an isolated temporary Hermes home.
- The scan's medium finding must be reported exactly; do not silently call it a clean scan. It points at a literal example command in the Markdown and is not, by itself, evidence of executable malicious behavior.
- `ACTIVATION UNTESTED` unless a fresh Hermes session exposes the slash command and loads the skill.
- `USER OUTCOME UNTESTED` unless representative user tasks are run with and without the skill.
- For output-style skills, test direct answers, coding edits, debugging, long explanations, partial-success reports, safety/destructive requests, and ambiguity. Check that concise formatting does not remove evidence, citations, rollback points, or safety gates.

## Rollback

For a live Hermes install, verify the installed name first, then remove only that skill:

```bash
hermes skills list
hermes skills uninstall <name>
```

Do not remove or edit `SOUL.md`, `AGENTS.md`, or other persistent instruction files as part of an on-demand install. Always-on enablement is a separate approved change.
