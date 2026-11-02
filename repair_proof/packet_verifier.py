"""Offline consistency checks for bounded JSON review packets.

This verifier checks a packet against the checked-in fixture registry and,
when applicable, the pinned recorded-proof artifact. It deliberately does not
claim provider authenticity, a fresh model result, execution, or general
repair correctness.
"""
import json
import os
import stat

from pydantic import ValidationError

from .fixtures import FIXTURES
from .patch_policy import sha, validate
from .recorded import RecordedError, load_records
from .sanitize import evidence
from .schemas import Proposal


MAX_PACKET_BYTES = 65536
NOT_RUN = {
    'status': 'not_run',
    'reason': 'No code has been executed. Policy acceptance is not repair proof.',
}
RECORDED_PROVENANCE = (
    'Recorded prior Meta response — no API call. Model: muse-spark-1.3. '
    'Stored parsed proposal, not a raw HTTP response. Historical Docker results '
    'are not current verification.'
)
REPLAY_PROVENANCE = (
    'Replay — newly authored expected proposal, NOT a Meta model response. '
    'Logs are synthetic fixture evidence.'
)


class PacketVerificationError(ValueError):
    """The downloaded packet is not consistent with this source release."""


def _fail(label):
    raise PacketVerificationError(label)


def _require_equal(actual, expected, label):
    if actual != expected:
        _fail(label)


def _replay_proposal(fixture, lines):
    return Proposal(
        diagnosis=fixture.diagnosis,
        evidence_ids=[lines[2]['id']],
        edits=[{
            'path': 'src/solution.py',
            'original_sha256': sha(fixture.source),
            'replacement': fixture.replacement,
        }],
    )


def _require_packet_id(value):
    if not isinstance(value, str) or len(value) != 32:
        _fail('Packet ID is invalid')
    try:
        int(value, 16)
    except ValueError:
        _fail('Packet ID is invalid')


def _validate_metrics(mode, metrics):
    if not isinstance(metrics, dict):
        _fail('Packet metrics are invalid')
    required = {'latency_ms', 'input_tokens', 'output_tokens', 'cost_usd'}
    if set(metrics) != required:
        _fail('Packet metrics are invalid')
    if mode == 'recorded':
        _require_equal(
            metrics,
            {'latency_ms': None, 'input_tokens': None, 'output_tokens': None, 'cost_usd': None},
            'Recorded packet metrics are invalid',
        )
        return
    latency = metrics['latency_ms']
    if isinstance(latency, bool) or not isinstance(latency, int) or not 0 <= latency <= 60000:
        _fail('Replay latency is invalid')
    _require_equal(
        {key: metrics[key] for key in required - {'latency_ms'}},
        {'input_tokens': None, 'output_tokens': None, 'cost_usd': None},
        'Replay packet metrics are invalid',
    )


def verify_packet(packet):
    """Raise PacketVerificationError unless an unexecuted preview is consistent."""
    if not isinstance(packet, dict):
        _fail('Packet must be a JSON object')
    mode = packet.get('mode')
    if mode not in {'replay', 'recorded'}:
        _fail('Only recorded and authored replay packets are supported')
    required = {
        'id', 'fixture', 'mode', 'provenance', 'evidence', 'proposal', 'policy',
        'verification', 'metrics', 'integrity',
    }
    if mode == 'recorded':
        required.add('recorded_proof')
    if set(packet) != required:
        _fail('Packet fields are invalid')
    _require_packet_id(packet['id'])

    fixture_data = packet.get('fixture')
    if not isinstance(fixture_data, dict):
        _fail('Packet fixture is invalid')
    fixture_id = fixture_data.get('id')
    fixture = FIXTURES.get(fixture_id)
    if fixture is None:
        _fail('Packet fixture is not registered')
    _require_equal(
        fixture_data,
        {
            'id': fixture.id,
            'title': fixture.title,
            'category': fixture.category,
            'holdout': fixture.holdout,
        },
        'Packet fixture metadata is invalid',
    )
    lines = evidence(fixture.log)
    _require_equal(packet.get('evidence'), lines, 'Packet evidence is invalid')
    try:
        proposal = Proposal.model_validate(packet.get('proposal'))
    except ValidationError:
        _fail('Packet proposal is invalid')
    _require_equal(packet['proposal'], proposal.model_dump(), 'Packet proposal is invalid')
    _require_equal(
        packet.get('integrity'),
        {
            'source_sha256': sha(fixture.source),
            'test_sha256': sha(fixture.test_source),
            'replacement_sha256': sha(proposal.edits[0].replacement),
        },
        'Packet integrity hashes are invalid',
    )
    _require_equal(
        packet.get('policy'),
        validate(fixture.source, proposal, {line['id'] for line in lines}),
        'Packet policy verdict is invalid',
    )
    _require_equal(packet.get('verification'), NOT_RUN, 'Current verification is invalid')
    _validate_metrics(mode, packet.get('metrics'))

    if mode == 'replay':
        _require_equal(packet.get('provenance'), REPLAY_PROVENANCE, 'Replay provenance is invalid')
        _require_equal(proposal, _replay_proposal(fixture, lines), 'Replay proposal is invalid')
        return

    _require_equal(packet.get('provenance'), RECORDED_PROVENANCE, 'Recorded provenance is invalid')
    try:
        records = load_records()
    except RecordedError as error:
        raise PacketVerificationError('Pinned recorded proof is unavailable') from error
    record = records.get(fixture_id)
    if record is None:
        _fail('Recorded proof is unavailable for this fixture')
    _require_equal(proposal, record['proposal'], 'Recorded proposal is invalid')
    _require_equal(packet.get('recorded_proof'), record['proof'], 'Recorded proof is invalid')


def verify_packet_file(path):
    """Read one bounded regular JSON file and return only after verification."""
    try:
        metadata = os.lstat(path)
    except OSError as error:
        raise PacketVerificationError('Packet file is unavailable') from error
    if not stat.S_ISREG(metadata.st_mode):
        _fail('Packet file must be a regular file')
    if metadata.st_size <= 0 or metadata.st_size > MAX_PACKET_BYTES:
        _fail('Packet file exceeds the size limit')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise PacketVerificationError('Packet file is unavailable or unsafe') from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            _fail('Packet file must be a regular file')
        if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
            _fail('Packet file changed during opening')
        if opened.st_size <= 0 or opened.st_size > MAX_PACKET_BYTES:
            _fail('Packet file exceeds the size limit')
        chunks = []
        remaining = MAX_PACKET_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(8192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        if len(raw) != opened.st_size or len(raw) > MAX_PACKET_BYTES:
            _fail('Packet file exceeds the size limit')
        packet = json.loads(raw.decode('utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PacketVerificationError('Packet file is not valid UTF-8 JSON') from error
    finally:
        os.close(descriptor)
    verify_packet(packet)
