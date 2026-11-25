"""Verify the tracked Repair Proof source set against SOURCE_MANIFEST.json.

Run with --write after changing tracked files to refresh files_sha256.
"""
import hashlib
import json
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEX_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class ManifestError(Exception):
 pass


def tracked_paths(root: Path) -> set[str]:
 try:
  result = subprocess.run(
   ['git', '-C', str(root), 'ls-files', '-z'],
   check=True, capture_output=True,
  )
 except (OSError, subprocess.CalledProcessError) as error:
  raise ManifestError('Unable to read the tracked source set.') from error
 return {item.decode('utf-8') for item in result.stdout.split(b'\0') if item}


def manifest_entries(root: Path) -> dict[str, str]:
 try:
  data = json.loads((root / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
 except (OSError, json.JSONDecodeError) as error:
  raise ManifestError('Unable to read SOURCE_MANIFEST.json.') from error
 entries = data.get('files_sha256') if isinstance(data, dict) else None
 if not isinstance(entries, dict):
  raise ManifestError('SOURCE_MANIFEST.json must contain a files_sha256 object.')
 return entries


def verify(root: Path) -> int:
 root = root.resolve()
 entries = manifest_entries(root)
 expected = tracked_paths(root) - {'SOURCE_MANIFEST.json'}
 manifest_paths = set(entries)
 failures = []
 if missing := sorted(expected - manifest_paths):
  failures.append('missing=' + ','.join(missing))
 if extra := sorted(manifest_paths - expected):
  failures.append('extra=' + ','.join(extra))
 for relative, digest in entries.items():
  candidate = Path(relative) if isinstance(relative, str) else None
  source = root / candidate if candidate else None
  if not candidate or candidate.is_absolute() or '..' in candidate.parts:
   failures.append(f'unsafe path={relative!r}')
  elif not isinstance(digest, str) or not HEX_DIGEST.fullmatch(digest):
   failures.append(f'invalid digest={relative}')
  elif source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(root):
   failures.append(f'invalid file={relative}')
  elif hashlib.sha256(source.read_bytes()).hexdigest() != digest:
   failures.append(f'digest mismatch={relative}')
 if failures:
  raise ManifestError(
   'Manifest verification failed: ' + '; '.join(failures)
   + '\nIf these changes are intended, run: python scripts/verify_manifest.py --write'
  )
 return len(entries)


def write(root: Path) -> int:
 """Rewrite files_sha256 from the tracked files, keeping the other manifest fields."""
 root = root.resolve()
 path = root / 'SOURCE_MANIFEST.json'
 if path.is_symlink() or not path.is_file():
  raise ManifestError('SOURCE_MANIFEST.json must be a regular file, not a symlink.')
 try:
  data = json.loads(path.read_text(encoding='utf-8'))
 except (OSError, json.JSONDecodeError) as error:
  raise ManifestError('Unable to read SOURCE_MANIFEST.json.') from error
 if not isinstance(data, dict):
  raise ManifestError('SOURCE_MANIFEST.json must contain a JSON object.')
 entries = {}
 for relative in sorted(tracked_paths(root) - {'SOURCE_MANIFEST.json'}):
  source = root / relative
  if source.is_symlink() or not source.is_file():
   raise ManifestError(f'Refusing to hash non-regular tracked path: {relative}')
  entries[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
 data['files_sha256'] = entries
 # Write a sibling temp file and rename it over the manifest, so a failed write
 # (full disk, interrupt) leaves the previous manifest intact.
 fd, temp_name = tempfile.mkstemp(dir=root, prefix='.SOURCE_MANIFEST.', suffix='.tmp')
 try:
  with os.fdopen(fd, 'w', encoding='utf-8') as handle:
   handle.write(json.dumps(data, indent=2) + '\n')
  os.chmod(temp_name, path.stat().st_mode & 0o777)
  os.replace(temp_name, path)
 except BaseException:
  Path(temp_name).unlink(missing_ok=True)
  raise
 return len(entries)


def main(argv: list[str] | None = None) -> int:
 args = sys.argv[1:] if argv is None else argv
 if args not in ([], ['--write']):
  print('usage: verify_manifest.py [--write]', file=sys.stderr)
  return 2
 if args == ['--write']:
  try:
   count = write(ROOT)
  except ManifestError as error:
   print(error, file=sys.stderr)
   return 1
  print(f'Wrote {count} manifest entries.')
  return 0
 try:
  count = verify(ROOT)
 except ManifestError as error:
  print(error, file=sys.stderr)
  return 1
 print(f'Verified {count} manifest entries.')
 return 0


if __name__ == '__main__':
 raise SystemExit(main())
