# Manifest-Gated Runtime → Source Port (reusable commands)

Topology from the worked session:
- Live runtime skills: `/home/ubuntu/.hermes/skills/...`
- Durable source clone: `/home/ubuntu/hermes-agent-personal_assistant-work`
- Manifest: `docs/reconciliation/v3-source-coverage-manifest.json`
- Validator: `scripts/guard/manifest-validate.sh <manifest.json> <release-sha>`
  → runs `scripts/guard/manifest_validate.py`, which recomputes
  `sha256(git show {release_sha}:{source})` per entry.

## 1. Enumerate + copy + hash + append manifest entries
```python
import json, hashlib
from pathlib import Path

REPO = Path("/home/ubuntu/hermes-agent-personal_assistant-work")
RUNTIME = Path("/home/ubuntu/.hermes/skills")

# runtime_subpath -> source_repo_subpath
pkgs = {
    "productivity/grill-me": "skills/productivity/grill-me",
    "productivity/grilling": "skills/productivity/grilling",
    "software-development/to-spec": "skills/software-development/to-spec",
    "software-development/setup-matt-pocock-skills": "skills/software-development/setup-matt-pocock-skills",
    "software-development/to-tickets": "skills/software-development/to-tickets",
    "software-development/tdd": "skills/software-development/tdd",
    "software-development/code-review": "skills/software-development/code-review",
    "software-development/implement": "skills/software-development/implement",
    "software-development/wayfinder": "skills/software-development/wayfinder",
}
manifest = REPO / "docs/reconciliation/v3-source-coverage-manifest.json"
obj = json.loads(manifest.read_text())
existing = {e["source"] for e in obj["entries"]}

new, problems = [], []
for rsub, ssub in pkgs.items():
    for f in sorted((REPO / ssub).rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(REPO))
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        rt = RUNTIME / rsub / str(f.relative_to(REPO / ssub))
        if rt.exists() and hashlib.sha256(rt.read_bytes()).hexdigest() != h:
            problems.append(f"HASH MISMATCH {rel}")
        if rel in existing:
            problems.append(f"DUPLICATE {rel}")
            continue
        new.append({"destination": None, "kind": "source-only",
                    "source": rel, "source_sha256": h})
assert not problems, problems
obj["entries"].extend(new)
# candidate_sha stays "PENDING_OWNER_RELEASE" — do NOT set to the commit
manifest.write_text(json.dumps(obj, indent=2) + "\n")
print("appended", len(new), "entries; total", len(obj["entries"]))
```

## 2. Stage + pre-commit privacy gates
```bash
cd /home/ubuntu/hermes-agent-personal_assistant-work
git add skills/productivity/grill-me skills/productivity/grilling \
        skills/software-development docs/reconciliation/v3-source-coverage-manifest.json
git diff --cached --name-only | wc -l          # expect 26 (25 files + manifest)
bash scripts/guard/secret-scan.sh --staged     # expect SECRET-SCAN PASS
```

PII heuristic (email/phone) over the new files:
```python
import re
from pathlib import Path
EMAIL = re.compile(rb"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
PHONE = re.compile(rb"(?<![A-Za-z0-9])\+[1-9](?:[ ()-]*[0-9]){7,14}(?![0-9])")
PH = {b"example.com", b"example.org", b"example.net", b"example.invalid", b"invalid"}
# scan each new file; flag any email w/ non-placeholder domain or any phone
```

## 3. Commit (local only) + post-commit validator gate
```bash
cd /home/ubuntu/hermes-agent-personal_assistant-work
git -c user.name="Hermes Operator" -c user.email="operator@local" commit -m "feat(skills): capture N approved skill packages (source-only)"
SHA=$(git rev-parse HEAD)
git status --porcelain=v1 | wc -l            # expect 0
bash scripts/guard/manifest-validate.sh docs/reconciliation/v3-source-coverage-manifest.json "$SHA"
# expect: MANIFEST-VALIDATE PASS: parsed=239 validated=239 release_sha=<SHA>
```

## 4. STOP — release approval required
AGENTS.md §5: `main` promotion requires one tested exact-SHA approval:
`APPROVE RELEASE <full-sha>`. No docs-only auto-promotion, no approval-per-command
loop, no force-push. Report the SHA and ask; do NOT push.

Distinct states to report: staged / committed-local / validated-at-SHA / pushed /
released-live. A local commit is never "released."
