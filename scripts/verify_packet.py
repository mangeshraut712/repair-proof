#!/usr/bin/env python3
"""Check a downloaded Repair Proof JSON review packet without network access."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repair_proof.packet_verifier import PacketVerificationError, verify_packet_file


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packets', type=Path, nargs='*', help='One or more JSON review packets to verify')
    parser.add_argument('--dir', type=Path, dest='directory', help='Directory containing JSON review packets')
    args = parser.parse_args(argv)

    paths = list(args.packets)
    if args.directory:
        if not args.directory.is_dir():
            print(f'ERROR: {args.directory} is not a directory', file=sys.stderr)
            return 2
        paths.extend(sorted(args.directory.glob('*.json')))

    if not paths:
        parser.error('Specify at least one packet file or --dir.')

    if len(paths) == 1 and not args.directory:
        path = paths[0]
        try:
            verify_packet_file(path)
            print(
                'PASS: packet is internally consistent with this source release. '
                'This does not prove provider authenticity, fresh execution, or general repair correctness.'
            )
            return 0
        except PacketVerificationError as error:
            print(f'INVALID: {error}', file=sys.stderr)
            return 1

    failed = 0
    for path in paths:
        try:
            verify_packet_file(path)
            print(
                f'PASS [{path}]: packet is internally consistent with this source release. '
                'This does not prove provider authenticity, fresh execution, or general repair correctness.'
            )
        except PacketVerificationError as error:
            print(f'INVALID [{path}]: {error}', file=sys.stderr)
            failed += 1

    if failed:
        print(f'\nFAILED: {failed}/{len(paths)} packets failed verification.', file=sys.stderr)
        return 1
    print(f'\nPASS: All {len(paths)} packets verified successfully.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
