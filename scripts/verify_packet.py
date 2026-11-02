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
    parser.add_argument('packet', type=Path)
    args = parser.parse_args(argv)
    try:
        verify_packet_file(args.packet)
    except PacketVerificationError as error:
        print(f'INVALID: {error}', file=sys.stderr)
        return 1
    print(
        'PASS: packet is internally consistent with this source release. '
        'This does not prove provider authenticity, fresh execution, or general repair correctness.'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
