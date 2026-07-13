# Remote provider optional dependency review

ACX-26 uses `cryptography>=45,<50` only in the optional `remote` extra to parse an already received X.509 certificate and serialize its SubjectPublicKeyInfo for exact pin comparison. `cryptography` is distributed under Apache-2.0 OR BSD-3-Clause. It was already an optional signing/test dependency and is not imported by AECCTX core operations.

The reference remote worker and fixtures are original Apache-2.0 project code/data. No remote SDK, service client, private key, credential, GPL/commercial decoder or third-party AEC file is bundled. A provider operator remains responsible for decoder licenses, entitlement, service terms, jurisdiction, retention, deletion and billing.
