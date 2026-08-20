from __future__ import annotations
import contextlib
import hashlib
import io
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(HERE/'scripts'/'guard'))
import manifest_validate  # noqa: E402
import secret_scan  # noqa: E402

_PII_SPEC = importlib.util.spec_from_file_location(
    'pii_review', HERE / 'scripts' / 'guard' / 'pii-review.py'
)
if _PII_SPEC is None or _PII_SPEC.loader is None:
    raise RuntimeError('unable to load pii-review.py')
pii_review = importlib.util.module_from_spec(_PII_SPEC)
_PII_SPEC.loader.exec_module(pii_review)

class GuardTests(unittest.TestCase):
    def test_pii_review_allows_email_like_manifest_path_metadata(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            subprocess.run(['git', 'init', '-q'], check=True)
            subprocess.run(['git', 'config', 'user.email', 'owner@example.invalid'], check=True)
            subprocess.run(['git', 'config', 'user.name', 'guard-tests'], check=True)
            manifest = Path('docs/reconciliation') / 'hermes-runtime-tree-manifest.json'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"entries":[]}', encoding='utf-8')
            subprocess.run(['git', 'add', str(manifest)], check=True)
            subprocess.run(['git', 'commit', '-qm', 'base'], check=True)
            email = b'alice' + b'@' + b'private.test'
            manifest.write_text(
                '{"source":"contributors/emails/' + email.decode() + '",'
                '"destination":"/runtime/contributors/emails/' + email.decode() + '"}',
                encoding='utf-8',
            )
            subprocess.run(['git', 'add', str(manifest)], check=True)
            subprocess.run(['git', 'commit', '-qm', 'path metadata'], check=True)
            findings = pii_review.scan_diff('HEAD^..HEAD')
            self.assertEqual(findings, [])
            os.chdir(old)

    def test_pii_review_flags_email_in_manifest_content_field(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            subprocess.run(['git', 'init', '-q'], check=True)
            subprocess.run(['git', 'config', 'user.email', 'owner@example.invalid'], check=True)
            subprocess.run(['git', 'config', 'user.name', 'guard-tests'], check=True)
            manifest = Path('docs/reconciliation') / 'hermes-runtime-tree-manifest.json'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"entries":[]}', encoding='utf-8')
            subprocess.run(['git', 'add', str(manifest)], check=True)
            subprocess.run(['git', 'commit', '-qm', 'base'], check=True)
            email = b'alice' + b'@' + b'private.test'
            manifest.write_bytes(
                b'{"source":"safe.py","metadata":"contact ' + email + b'"}'
            )
            subprocess.run(['git', 'add', str(manifest)], check=True)
            subprocess.run(['git', 'commit', '-qm', 'content metadata'], check=True)
            findings = pii_review.scan_diff('HEAD^..HEAD')
            self.assertEqual(findings, [(str(manifest), 'email-like')])
            os.chdir(old)

    def test_first_push_base_uses_tip_first_parent(self):
        result = subprocess.run(
            [sys.executable, str(HERE / 'scripts' / 'guard' / 'ci-base-sha.py'),
             '0' * 40, 'tip-sha'],
            check=True, capture_output=True, text=True,
        )
        self.assertEqual(result.stdout.strip(), 'tip-sha^')

    def test_normal_push_base_is_unchanged(self):
        result = subprocess.run(
            [sys.executable, str(HERE / 'scripts' / 'guard' / 'ci-base-sha.py'),
             'before-sha', 'tip-sha'],
            check=True, capture_output=True, text=True,
        )
        self.assertEqual(result.stdout.strip(), 'before-sha')

    def test_undeterminable_base_fails_closed(self):
        result = subprocess.run(
            [sys.executable, str(HERE / 'scripts' / 'guard' / 'ci-base-sha.py'),
             '0' * 40, ''],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_secret_findings_return_rule_without_secret_bytes(self):
        secret=b'sk-' + b'A'*32
        result=list(secret_scan.findings('fixture.txt',secret))
        self.assertEqual(result,[('fixture.txt','openai-key')])
        rendered=' '.join(f'{p}:{r}' for p,r in result)
        self.assertNotIn(secret.decode(),rendered)

    def test_secret_scanner_does_not_treat_short_values_as_secret(self):
        self.assertEqual(list(secret_scan.findings('x',b'sk-short')),[])

    def test_manifest_positive_and_negative_cases(self):
        old=os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            subprocess.run(['git','init','-q'],check=True)
            subprocess.run(['git','config','user.email','owner@example.invalid'],check=True)
            subprocess.run(['git','config','user.name','guard-tests'],check=True)
            Path('good.txt').write_text('safe\n',encoding='utf-8')
            subprocess.run(['git','add','good.txt'],check=True)
            subprocess.run(['git','commit','-qm','fixture'],check=True)
            sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
            digest=hashlib.sha256(b'safe\n').hexdigest()
            good={'schema_version':1,'candidate_sha':'PENDING_OWNER_RELEASE','entries':[{'source':'good.txt','source_sha256':digest,'kind':'source-only','destination':None}]}
            Path('good.json').write_text(json.dumps(good),encoding='utf-8')
            self.assertEqual(manifest_validate.validate('good.json',sha),0)
            bad=dict(good); bad['entries']=[dict(good['entries'][0],source_sha256='0'*64)]
            Path('bad-hash.json').write_text(json.dumps(bad),encoding='utf-8')
            self.assertEqual(manifest_validate.validate('bad-hash.json',sha),1)
            bad2={'schema_version':1,'entries':[dict(good['entries'][0],extra='must-fail')]}
            Path('bad-row.json').write_text(json.dumps(bad2),encoding='utf-8')
            self.assertEqual(manifest_validate.validate('bad-row.json',sha),1)
            Path('bad-json.json').write_text('{not-json',encoding='utf-8')
            self.assertEqual(manifest_validate.validate('bad-json.json',sha),1)
            os.chdir(old)

if __name__=='__main__': unittest.main()
