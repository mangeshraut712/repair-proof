# Deployment status and pre-hosting checklist

## Current supported operation

Repair Proof is intentionally a **loopback-only, single-user prototype**. The
supported mode is offline Recorded or Authored replay on `127.0.0.1`; it is not
a hosted service and has no public application URL. The GitHub repository and
recorded demo are review artifacts, not a deployment target.

The optional Docker verifier is not a deployment container. It is an
operator-enabled local check that requires a trusted, already-local,
digest-pinned image. It never pulls an image, mounts host paths, forwards
credentials, or falls back to host execution. See [SECURITY.md](SECURITY.md).

## Local run and reproducibility

Use the direct pins in `requirements.txt`; the optional `requirements.lock`
does not claim portable clean-install validation. The supported commands are in
the [README](../README.md), with clean-install evidence and limits in
[CLEAN_INSTALL.md](CLEAN_INSTALL.md). Recorded and Authored replay need no
credential. Browser live inference is permanently disabled.

## Required before any public hosting

Public hosting is deliberately out of scope until a separate design and
security review establishes all of the following:

1. Authentication, authorization, and tenant isolation.
2. Per-user request limits, quotas, cancellation, and durable audit records.
3. A hardened remote execution service that is separate from the web process;
   no host execution fallback and no exposed Docker socket.
4. HTTPS/reverse-proxy policy, health checks, observability, incident response,
   privacy/retention controls, and an operational owner.
5. Dependency vulnerability review, fuzzing/abuse testing, secret-management
   design, and a release process for trusted execution images.
6. A re-evaluation of the policy boundary, which is defense in depth and not a
   general sandbox or correctness guarantee.

Do not create a public deployment, a homepage URL, or a production-readiness
claim merely because the local offline workflow and CI pass. Those checks are
important evidence, but they do not satisfy this checklist.
