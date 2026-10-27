"""Opt-in container verification. Never executes a proposed patch on the host.

A local digest-pinned Python image must be provisioned separately. This module
never pulls/builds images, forwards credentials, or mounts host directories.
"""
import json
import os
import re
import shutil
import subprocess
import uuid

# Fixed trusted driver; model output is only JSON data written to solution.py.
# The immutable test contract is supplied as an argument, not a writable file.
_DRIVER = r'''
import json, os, pathlib, resource, subprocess, sys
payload = json.loads(sys.stdin.read(131073))
if set(payload) != {"source", "tests"}:
    raise ValueError("invalid input")
root = pathlib.Path("/work/src")
root.mkdir(parents=True, exist_ok=True)
(root / "solution.py").write_text(payload["source"], encoding="utf-8")
resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONPATH": str(root),
       "HOME": "/work", "PYTHONDONTWRITEBYTECODE": "1"}
try:
    # Regular files plus RLIMIT_FSIZE bound output without unbounded pipe buffers.
    with open("/work/output", "w+b") as output:
        p = subprocess.run([sys.executable, "-B", "-c", payload["tests"]],
            cwd="/work", env=env, stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT, timeout=8)
        output.seek(0)
        text = output.read(12000).decode("utf-8", "replace")
    print(json.dumps({"exit_code": p.returncode, "output": text}))
except subprocess.TimeoutExpired:
    print(json.dumps({"error": "test execution timed out"}))
'''


def _environment():
    # Deliberately drop DOCKER_HOST, DOCKER_CONFIG, MODEL_API_KEY, and all other
    # ambient settings. Docker targets its default local socket, never a remote.
    return {'PATH': os.defpath}


def _run(docker, image, source, tests):
    name = 'repair-proof-' + uuid.uuid4().hex
    command = [docker, 'run', '--rm', '-i', '--name', name, '--pull=never',
               '--network', 'none', '--read-only', '--user', '65534:65534',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
               '--cpus', '1', '--memory', '128m', '--memory-swap', '128m',
               '--pids-limit', '32', '--log-driver', 'none',
               '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=8m,mode=1777',
               '--entrypoint', 'python', image, '-I', '-B', '-c', _DRIVER]
    try:
        result = subprocess.run(command, input=json.dumps({'source': source, 'tests': tests}),
                                capture_output=True, text=True, timeout=20,
                                env=_environment(), check=False)
    except (subprocess.TimeoutExpired, OSError):
        # Timeout of the Docker client is not proof that its container stopped.
        try:
            subprocess.run([docker, 'rm', '-f', name], capture_output=True,
                           text=True, timeout=5, env=_environment(), check=False)
        except (subprocess.TimeoutExpired, OSError):
            pass
        return {'error': 'sandbox timed out or could not start; cleanup requested'}
    if result.returncode != 0:
        return {'error': 'sandbox infrastructure failed'}
    try:
        if len(result.stdout) > 20000:
            raise ValueError('oversized output')
        report = json.loads(result.stdout)
        if set(report) != {'exit_code', 'output'} or type(report['exit_code']) is not int or not isinstance(report['output'], str):
            raise ValueError('invalid report')
        # Process termination signals are not valid test failures.
        if report['exit_code'] not in (0, 1):
            raise ValueError('abnormal process exit')
        return report
    except (ValueError, TypeError):
        return {'error': 'sandbox returned no valid test result'}


def verify(fixture, replacement, enabled=False):
    """Verify a stored, policy-approved replacement with unchanged authored tests.

    Caller must independently validate policy before invoking this function.
    An unavailable runtime is a truthful preview-only outcome, never success.
    """
    if not enabled:
        return {'status': 'unavailable', 'reason': 'Sandbox disabled; preview only. No tests executed.'}
    image = os.environ.get('RP_SANDBOX_IMAGE', '')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image):
        return {'status': 'unavailable', 'reason': 'A preloaded digest-pinned RP_SANDBOX_IMAGE is required.'}
    docker = shutil.which('docker')
    if not docker:
        return {'status': 'unavailable', 'reason': 'Docker is unavailable; no host execution fallback.'}
    if len(replacement.encode()) > 32768 or len(fixture.test_source.encode()) > 32768:
        return {'status': 'unverified', 'reason': 'Sandbox input exceeds size bounds.'}
    try:
        inspection = subprocess.run([docker, 'image', 'inspect', image, '--format', '{{.Id}}'],
                                    capture_output=True, text=True, timeout=5,
                                    env=_environment(), check=False)
        if inspection.returncode != 0 or inspection.stdout.strip() != image:
            return {'status': 'unavailable', 'reason': 'Pinned sandbox image is not available locally. No pull attempted.'}
    except (OSError, subprocess.TimeoutExpired):
        return {'status': 'unavailable', 'reason': 'Local sandbox image could not be inspected.'}
    before = _run(docker, image, fixture.source, fixture.test_source)
    if 'error' in before:
        return {'status': 'unverified', 'reason': before['error'], 'before': before}
    after = _run(docker, image, replacement, fixture.test_source)
    if 'error' in after:
        return {'status': 'unverified', 'reason': after['error'], 'before': before, 'after': after}
    proved = before['exit_code'] == 1 and after['exit_code'] == 0
    return {'status': 'verified' if proved else 'unverified',
            'reason': 'Failed before and passed after against unchanged authored tests.' if proved else 'The required failed-before / passed-after transition was not observed.',
            'before': before, 'after': after}
