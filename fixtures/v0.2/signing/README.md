# ACX-20 signing conformance fixtures

Every key and signature in this directory is project-generated **TEST ONLY** material.
The private keys are deterministic corpus inputs, are not production identities or trust
roots, and MUST NOT be used outside tests. The corpus has no network, LLM, certificate,
timestamp or online revocation dependency.

Run `python fixtures/v0.2/signing/generate_fixtures.py --check` to prove byte stability.
