from __future__ import annotations
import contextlib
import hashlib
import io
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

class GuardTests(unittest.TestCase):
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
