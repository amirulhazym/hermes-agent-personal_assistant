---
name: test-isolation-hygiene
description: "Use when tests differ across isolation, CI, full runs, or live candidate boundaries."
version: 1.1.0
author: Jane
license: MIT
created: 2026-08-13
tags: ["testing", "python", "unittest", "isolation", "determinism"]
metadata:
  hermes:
    tags: [testing, python, unittest, isolation, determinism]
    related_skills: [debugging-and-error-recovery, test-driven-development, verification-before-completion]
---

# Test Isolation Hygiene

## When to Use

- A test suite passes when run alone but fails when run after other modules
  (module-cache / env-leak suspicion).
- Tests pass during the day but fail after midnight (wall-clock dependence).
- Tests mutate `HOME` / `HERMES_HOME` / `os.environ` and later modules break.
- Any suite whose tests import modules that read `Path.home()` or env at
  import time.

## Candidate-review boundary

When this skill is used during an independent review of an unstaged candidate, snapshot the candidate before testing: `git status --short --branch`, `git rev-parse HEAD`, and the exact path-scoped `git diff --full-index`. Keep all tests read-only against a temporary `HOME`/`HERMES_HOME`; never stage, commit, deploy, or copy candidate files into live runtime state. Re-check Git identity/status after testing. If another process commits or mutates the candidate during the review, invalidate claims tied to the earlier worktree state, record the new SHA, and rerun the affected checks before reporting final evidence. For the complete review sequence, see `references/unstaged-candidate-review.md`.



`os.environ['HOME'] = ...` at import time leaks into EVERY later module
imported by the same process. A later test's lazy import (an import executed
inside a function, not at module top) reads the leaked value and silently
resolves the wrong paths — no error, just wrong behaviour.

**Fix pattern** — set env only around the import, restore in `finally`:

```python
def load_module(home: Path):
    orig_home = os.environ.get('HOME')
    orig_hermes = os.environ.get('HERMES_HOME')
    os.environ['HOME'] = str(home.parent)
    os.environ['HERMES_HOME'] = str(home)
    try:
        sys.modules.pop('target_module', None)
        spec = importlib.util.spec_from_file_location('target_isolated', ...)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        # restore both keys (pop if they were absent)
        ...
```

## Rule 2: Hardcode live/read-only fixture paths — never `Path.home()` in a test module

A module-level `LIVE = Path.home() / ".hermes"` is evaluated at import time;
if an earlier test module mutated HOME, your "live" path silently points at a
stale temp dir and fixture copies fail or load garbage. Use the explicit
absolute path (e.g. `Path("/home/ubuntu/.hermes")`) like sibling test files
do. (In unittest the loader imports ALL modules before running any test —
import order follows module name, so earlier modules' import-time env
mutations affect later modules' module-level constants.)

## Rule 3: Freeze the wall clock in handler/integration tests

`datetime.now()` in production code makes tests time-of-day dependent:
"jam 6.08am" parses as a FUTURE time (rejected by future-time guards) once
the real clock passes midnight. The suite is green all day and red at 00:05.

**Fix pattern** — a datetime subclass with frozen `now()`:

```python
class _FrozenNow(datetime):
    FROZEN = datetime(2026, 8, 12, 18, 0)  # late enough that all test times are past
    @classmethod
    def now(cls, tz=None):
        return cls.FROZEN

# per test:
with mock.patch.object(handler_module, "datetime", _FrozenNow):
    handler_module.handle(...)
```

Pick FROZEN late in the day (e.g. 18:00) so morning AND afternoon test
messages are all in the past relative to it.

## Rule 4: Lazy imports inside functions need the module pre-imported under the right env

If production code does `from helper import f` INSIDE a function (lazy), the
import runs at call time — after your setUp env context has exited. The
helper's module-level path constants (`TAPER_FILE = Path.home() / ...`) were
captured at ITS import time, which may be another test's HOME.

**Fix pattern** — in setUp, inside the env context, import the helper
explicitly BEFORE anything calls it lazily:

```python
with mock.patch.dict(os.environ, {"HOME": str(home)}, clear=False):
    for mod in list(sys.modules):
        if mod == "prod_module" or mod.startswith("prod_module."):
            del sys.modules[mod]
    import helper_module  # noqa: F401 — captured under correct HOME
    import prod_module
```

Do NOT pop the helper from sys.modules in setUp if production imports it
lazily — the fresh import will happen later under the WRONG env.

## Rule 5: Host-vs-CI parity — gitignored fixtures break fresh clones

A suite that is GREEN on the host but RED on GitHub Actions (or any fresh
runner) with no code difference is almost always fixture-path parity: tests
copy operational data files (`med-schedule.json`, `dexa_taper.json`, ...) at
setUp from a path that only exists on the host. Those files are often
gitignored BY DESIGN (private operational data must not enter a public
repo — `.gitignore` rules like `med-*.json`). A fresh CI clone has neither
file, so `shutil.copy2`/`copytree` in setUp raises FileNotFoundError and the
whole class errors out — while the host run passes because the files exist
locally. Symptoms in CI: `FileNotFoundError: [Errno 2] .../med-schedule.json`
in setUp, or a guard/manifest job failing with hash mismatch.

**Fix pattern (this repo's established convention)** — gate the whole class:

```python
_LIVE_FIXTURES = (ROOT / "med-schedule.json").exists()

@unittest.skipUnless(_LIVE_FIXTURES, "live runtime fixtures not present (CI skips)")
class TestX(unittest.TestCase):
```

CI reports `OK (skipped=N)`; the VPS host keeps running the real
integration path with live data. Never fabricate fake fixtures in the repo
to make CI run them — the data is gitignored for privacy.

## Pitfalls

- A "passes in isolation, fails in full run" pair is a module-state problem:
  bisect by running the failing module after each other module until the
  minimal combination reproduces (e.g. `unittest A B` fails, `unittest B`
  passes).
- Same for "passes before midnight, fails after": it is a wall-clock flake,
  not a merge/regression. Verify by freezing time, not by re-running.
- Phase-sensitive assertions can hide the bug: a test expecting 3mg fails
  while the 4mg sibling passes when the lookup silently fell back to a
  static/other-phase value. When one date-boundary test fails but its
  neighbours pass, suspect a path/date-resolution fallback, not the values.
- Test files that copy fixtures from a "live" path must copy from the same
  explicit path used by sibling tests, or a test-order permutation breaks
  only one of them.
- "Green on host, red on CI" is NOT a flake and NOT fixable by re-running:
  the host has gitignored operational files the runner lacks. A local run
  with live fixtures present is not a CI proxy — verify with a clean clone
  (see Verification).
- A clone made BEFORE committing the fix still reproduces the old failure —
  always re-clone from HEAD after every commit before declaring CI-ready.
- Changing any tracked source file listed in a source-coverage manifest
  (sha256-pinned) without refreshing its hash fails the guard job with
  "hash mismatch for source=..." even when the code change is correct.
  Refresh the manifest in the SAME push as the code change.
- **Partial source closure is a harness boundary, not a code verdict:** if a broad suite collects the candidate's partial tree but imports missing packages/modules from a live or donor checkout, collection `ImportError`s are `HARNESS-INVALID`. Preserve the raw errors and stop that gate; do not call the candidate broken or green. Run the affected isolated tests separately, and reproduce unrelated failures on the exact clean baseline before changing scope.
- **Candidate/live state is separate:** a candidate PASS proves candidate bytes only. Before a runtime cutover, record the exact candidate SHA, live-file hashes, running-process PID/start time, and reload evidence independently. A commit or on-disk copy is not proof that the running process loaded it. See `references/stale-live-runtime-and-harness-gates.md` for the reusable evidence matrix and classification sequence. For the fork-migration partial-index harness (missing `providers/`/`run_agent.py` in this workdir — 8 collection ImportErrors, donor `PYTHONPATH` + donor venv fix, 1387-collected full-run evidence), see `references/fork-migration-partial-index-harness-2026-08-21.md`.


- Run the full module list in the same order as CI: `python3 -B -m unittest <all modules>`.
- Run the failing module twice: once isolated, once after each sibling —
  minimal reproduction pair documented in the fix.
- After fixing, the suite must be wall-clock independent: freeze-time tests
  make midnight irrelevant.
- **Local CI simulation (the only honest proxy for runner failures):**
  commit first, then fresh clone + empty HOME + the CI python version, and
  run the EXACT CI command lines:

  ```bash
  git commit ...   # clone is from HEAD — uncommitted patches aren't exercised
  rm -rf /tmp/ci-clone && git clone . /tmp/ci-clone
  cd /tmp/ci-clone
  HOME=/tmp/ci-home python3.12 -m unittest <exact CI module list>
  HOME=/tmp/ci-home python3.12 -m unittest discover -s <dir> -p 'test_*.py'
  ```
  Expect `OK (skipped=N)` for gated suites, not failures. Match the python
  version pinned in ci.yml (3.12 ≠ 3.11 — try both).
- **Manifest guard:** `bash scripts/guard/manifest-validate.sh <manifest.json> $(git rev-parse HEAD)` must print PASS before push.
- **Real CI status without admin rights (public repos):** the REST API is
  readable unauthenticated for metadata — `GET /repos/{owner}/{repo}/actions/runs?head_sha=<sha>`
  (status/conclusion) and `.../actions/runs/{id}/jobs` (per-step conclusions
  — pinpoints the failing step). Job LOGS (`.../actions/jobs/{id}/logs`)
  return 403 "Must have admin rights" without auth — don't rely on them;
  reproduce the failing step locally instead.
- Worked example with exact transcripts: references/ci-host-parity-2026-08-13.md
