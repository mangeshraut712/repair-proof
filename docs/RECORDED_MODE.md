# Recorded Meta proof mode
A repeatable demonstration of two prior real Meta proposals, without another API call.

## Use
1. Start the local app with the normal direct dependencies. No key or live switch is needed.
2. Select `inclusive-total` or `first-position`, then **Recorded Meta proof**.
3. Preview shows **Recorded prior Meta response — no API call**, actual stored parsed proposal, fresh independent policy check, model and artifact/proposal hashes.
4. Expand **Historical recorded proof — not current verification** to inspect the prior before=1/after=0 Docker record and recorded usage estimate.
5. Current execution starts **NOT RUN**. Only an enabled, available local sandbox can perform a new verification. Otherwise it remains preview-only. Historical success never changes current execution status.
6. Download JSON/Markdown: provenance and historical record travel with the review packet.

Authored replay remains a distinct handwritten example mode; Live Meta remains separately operator-gated and may cost money. The bounded live-evaluation runner is unchanged; recorded mode does not invoke it or consume its budget. Unsupported selected fixtures disable recorded Preview and explain the two-case limitation; the server also rejects unsupported IDs.

## Data integrity and limits
Only the fixed project file `docs/RECORDED_LIVE_PROOF.json` is read. It is bounded to32KiB, rejected if symlinked, and pinned to reviewed SHA-256 `eeb08ec01ab6c25b4862570f8bea2008369a5ae1248b143d74a683aa5ec8ea82`. No user path, upload or URL is accepted. Missing/tampered data disables availability and fails closed, never falls back to authored or live output.

Every record is independently parsed with the strict proposal schema, matched to a known fixture, checked against canonical proposal/source/log/test/replacement hashes, and rechecked by current patch policy. The historical semantic hashes must match the exact source, replacement and immutable tests. A changed artifact requires deliberate code review and digest update, not automatic trust of a supplied hash. Digest checks establish consistency with this source release, not a provider signature or independent authenticity attestation.

Raw HTTP bodies, provider response IDs and wall-clock response timestamps were not retained and remain explicitly unavailable/null. Do not fabricate them. Prior output is schema-validated parsed JSON exported from the completed authorized ledger, not a full provider transcript. Prior Docker evidence proves only the two named synthetic cases; it is not a fresh run or general accuracy benchmark. Current metrics remain null in recorded mode; prior usage lives only under `recorded_proof.usage_estimate`.

All model/provenance fields render with `textContent`, not HTML. Markdown packets enclose the JSON in a dynamically sized fence and download as attachments. Backend tests cover no-network operation, both records, unsupported IDs, missing/tampered/symlinked artifacts, source/test/schema/policy mismatches, current-vs-historical verification, and untrusted Markdown content. Browser helper scenarios are updated. Separate actual managed desktop-browser QA passed both recordings, unsupported-selection guard, history/current separation, downloads and selection-reset behavior. A separate isolated local 375×812 recorded-mode QA also passed; the optional mocked-API script remains unexecuted. Changing fixture or mode clears the current packet and download URLs, then requires a new Review, preventing stale provenance confusion.
