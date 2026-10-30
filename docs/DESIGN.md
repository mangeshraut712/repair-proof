# Repair Proof — design and provenance
New standalone work authored 2026-10-27. No existing product code imported.
## Goal
Turn a bounded authored failing Python fixture into an evidence-linked repair proposal, independent policy verdict, and optionally an isolated before/after proof. A proposal is not proof.
## Decisions
FastAPI + dependency-free browser UI; direct Meta HTTP adapter only. Replay uses explicitly authored expected proposals, never claimed as model output. Live requires operator opt-in and MODEL_API_KEY; no live inference was authorized during the original build. A later, separately authorized two-fixture batch is recorded as historical evidence, not current inference. Registry-only inputs, bounded redacted evidence, strict structured output, exact original hashes, single source-file edits and AST allowlist. Immutable tests never sent as editable files. Untrusted model commands are never executed.
Alternatives: arbitrary repositories expand attack surface and provenance burden; remote execution adds expense and secrets. Both excluded. Docker is optional, never automatically installed; no host execution fallback.
## Security boundary
Policy is defense in depth, not an execution sandbox. Optional Docker verification uses nonroot, no network, no mounts, no credentials, read-only root, bounded tmpfs/CPU/memory/PIDs/time. Docker binary, daemon and locally installed configured image must be trusted. No image pull. If unavailable, stay preview-only. Local development service binds loopback; not a multi-user hosted service.
## Success and limits
20 authored cases (12 repairable / 8 adversarial), 4 marked holdouts. Holdouts excluded from default evaluation. Actual policy and evidence metrics; repair success only after real isolated executions. No model quality, token pricing, hackathon eligibility or deployment success claimed without evidence.
