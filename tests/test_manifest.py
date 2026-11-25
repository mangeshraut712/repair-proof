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


def _load_verify_manifest():
 import importlib.util
 spec = importlib.util.spec_from_file_location('verify_manifest', ROOT / 'scripts' / 'verify_manifest.py')
 module = importlib.util.module_from_spec(spec)
 spec.loader.exec_module(module)
 return module


class ManifestWriteTests(unittest.TestCase):
 def setUp(self):
  import tempfile
  self.module = _load_verify_manifest()
  self.tmp = tempfile.TemporaryDirectory()
  self.root = Path(self.tmp.name)
  run = lambda *args: subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
  run('init', '-q')
  (self.root / 'a.txt').write_text('alpha\n', encoding='utf-8')
  (self.root / 'SOURCE_MANIFEST.json').write_text(
   json.dumps({'project': 'Demo', 'files_sha256': {}}, indent=2) + '\n', encoding='utf-8')
  run('add', 'a.txt', 'SOURCE_MANIFEST.json')
  self.run_git = run

 def tearDown(self):
  self.tmp.cleanup()

 def test_write_refreshes_digests_so_verify_passes_and_keeps_other_fields(self):
  with self.assertRaises(self.module.ManifestError) as caught:
   self.module.verify(self.root)
  self.assertIn('missing=a.txt', str(caught.exception))
  self.assertIn('verify_manifest.py --write', str(caught.exception))

  self.assertEqual(self.module.write(self.root), 1)
  self.assertEqual(self.module.verify(self.root), 1)
  data = json.loads((self.root / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
  self.assertEqual(data['project'], 'Demo')

  (self.root / 'a.txt').write_text('changed\n', encoding='utf-8')
  (self.root / 'b.txt').write_text('beta\n', encoding='utf-8')
  self.run_git('add', 'b.txt')
  with self.assertRaises(self.module.ManifestError):
   self.module.verify(self.root)
  self.assertEqual(self.module.write(self.root), 2)
  self.assertEqual(self.module.verify(self.root), 2)

 def test_write_is_byte_stable_for_the_committed_manifest(self):
  committed = (ROOT / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8')
  data = json.loads(committed)
  self.assertEqual(json.dumps(data, indent=2) + '\n', committed)
  self.assertEqual(list(data['files_sha256']), sorted(data['files_sha256']))

 def test_unknown_arguments_are_rejected(self):
  self.assertEqual(self.module.main(['--wrte']), 2)

 def test_write_refuses_a_symlinked_manifest(self):
  outside = self.root / 'outside.json'
  outside.write_text('{"keep": true}\n', encoding='utf-8')
  manifest = self.root / 'SOURCE_MANIFEST.json'
  manifest.unlink()
  manifest.symlink_to(outside)
  with self.assertRaises(self.module.ManifestError):
   self.module.write(self.root)
  self.assertEqual(outside.read_text(encoding='utf-8'), '{"keep": true}\n')

 def test_failed_write_keeps_the_previous_manifest(self):
  from unittest import mock
  manifest = self.root / 'SOURCE_MANIFEST.json'
  before = manifest.read_text(encoding='utf-8')
  with mock.patch.object(self.module.os, 'replace', side_effect=OSError('disk full')):
   with self.assertRaises(OSError):
    self.module.write(self.root)
  self.assertEqual(manifest.read_text(encoding='utf-8'), before)
  self.assertEqual(sorted(p.name for p in self.root.iterdir() if p.name.endswith('.tmp')), [])
