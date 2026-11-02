"""Verify the tracked Repair Proof source set against SOURCE_MANIFEST.json."""
import hashlib
import json
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
  raise ManifestError('Manifest verification failed: ' + '; '.join(failures))
 return len(entries)


def main() -> int:
 try:
  count = verify(ROOT)
 except ManifestError as error:
  print(error, file=sys.stderr)
  return 1
 print(f'Verified {count} manifest entries.')
 return 0


if __name__ == '__main__':
 raise SystemExit(main())
