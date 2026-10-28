# Security and operating limits
## Trust boundaries
The registry, immutable test source, application code, Python runtime, Docker executable/daemon, and selected local image are trusted. Logs and model output are not. No request accepts a filesystem path, shell command, arbitrary test, image name or replacement payload. The app never executes model-suggested commands.

Edits are restricted to one exact virtual path `src/solution.py`; original SHA-256 must match. Since there is no user repository filesystem ingestion and container files are authored fresh, traversal, absolute paths and symlink targets cannot select host files. Tests, workflows, manifests and binary source are rejected. A restrictive AST policy excludes imports, introspection, dynamic execution and arbitrary calls. This is not a formal Python security boundary: resource exhaustion and logic errors remain possible, so patches must not execute on the host.

The policy rejects `while` loops because it cannot prove their termination. Direct
recursion is also rejected by the call allowlist: `solve` is not an allowed call,
and nested functions are rejected. `for` loops remain allowed to preserve the
fixture language (including the recorded first-position repair), so large or
data-dependent iteration is **not** statically bounded by policy.
Execution-time CPU, memory, PID and wall-clock limits in the Docker verifier are
the remaining containment for that work; they do not make the syntax policy a
general execution-safety guarantee. The verifier itself revalidates a structured
proposal before starting a container, even if a caller already checked policy.

Logs are bounded before sanitation, stripped of ANSI/control characters, assigned stable line IDs and redacted for common tokens/key-value credentials. This is **not comprehensive secret detection**. Only synthetic fixtures are accepted; arbitrary private logs are deliberately unsupported. Meta receives source and sanitized logs, not environment secrets or immutable tests. Credentials are server environment only and never included in prompts/packets/errors. Provider error bodies are not returned or logged.

## Verification
Optional Docker is explicit operator opt-in, pinned to a local image ID, never auto-pulled. Isolated runs use no network, no mounted host paths, no Docker socket, no passed credentials, nonroot UID/GID, read-only root, dropped capabilities, no-new-privileges, memory/CPU/PID limits, bounded tmpfs and wall-clock time. Source/tests are sent as JSON on stdin; fixed trusted runner writes source inside the container and passes the unchanged test contract as a Python argument. Tests execute separately before/after and cannot be replaced by the model. Container cleanup is attempted after failures/timeouts.

Containers are not equivalent to hardware VMs. A malicious runtime/kernel or daemon lies outside this prototype's guarantees. Use only a dedicated trusted test daemon, not a production workload host. A policy rejection can never be verified. Unavailable Docker never triggers host subprocess execution of the patch.

## Deployment is out of scope
Bind 127.0.0.1 only. Host/origin checks, strict inputs and CSP reduce local browser hazards; this is not authentication, tenancy isolation, rate limiting or hardened deployment. Preview storage is bounded in-memory and not durable. Only one verification runs at a time per application process; extra requests receive 429. Use a single server worker. Before public hosting add authentication, per-user isolation, quotas, cancellation, audit persistence, hardened execution service, fuzzing, dependency scanning and operational review.

## Known limitations
Small pure-Python allowlist rejects many legitimate repairs. Citation existence is checked, not semantic correctness. Synthetic replay outputs are hand-authored. Tests can be incomplete. Source dates and hashes establish build provenance, not independent authorship attestation. Limited before/after evidence exists only for the named authored fixtures recorded in `VALIDATION.md`; it is not proof for arbitrary repairs. Live provider performance remains unavailable until explicitly authorized and measured.
