import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ManifestCommandTests(unittest.TestCase):
 def test_local_manifest_command_verifies_current_checkout(self):
  result = subprocess.run(
   [sys.executable, 'scripts/verify_manifest.py'], cwd=ROOT,
   capture_output=True, text=True,
  )
  self.assertEqual(result.returncode, 0, result.stderr)
  expected=len(json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())['files_sha256'])
  self.assertIn(f'Verified {expected} manifest entries.', result.stdout)
