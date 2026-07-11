# Security Policy

## Reporting

Please report suspected vulnerabilities privately through GitHub Security Advisories for this repository. Do not include confidential source models in a public issue.

## Input trust boundary

AECCTX treats every source file, archive, embedded object, URI, parser response, and plugin as untrusted. Implementations must:

- avoid executing macros, scripts, active links, or source-provided commands;
- enforce archive traversal, decompression, size, recursion, memory, and timeout limits;
- isolate optional proprietary, GPL, native, or network-backed adapters;
- record parser and sanitization diagnostics;
- default to local processing and explicit network opt-in;
- avoid embedding source files or secrets unless policy explicitly allows it.

Security-sensitive implementation work must include malformed and adversarial fixtures.
