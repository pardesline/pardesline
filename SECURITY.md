# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.2.x (latest on PyPI) | yes |
| 0.1.x | no: the 0.1 client is superseded; upgrade |

## What counts as a security issue here

pardesline runs locally and downloads public data from URLs declared in manifests. Reports we want:

- A manifest or a loader that can be made to write outside the cache directory (path traversal in archive members, `..` in roles or sample ids).
- A checksum or size check that can be bypassed, so that a fetched file differs from what the manifest describes without an error.
- Code execution through data: a `.npz` loaded with pickling enabled, a PLY/STL/NIfTI reader reached with untrusted input in a way that crashes the interpreter, an MCP tool argument that reaches a shell.
- The MCP server exposing a file outside the skills folder or the cache (`get_skill`, `load_sample`, `export_dataset`).
- Secrets written to logs or sidecars (Hugging Face tokens, cloud credentials).

Bugs in the algorithms' numerical results are ordinary issues, not security reports.

## Reporting

Use GitHub's private vulnerability reporting on this repository ("Report a vulnerability" under the Security tab) so the report stays private until a fix ships. If that is not available to you, open an issue titled "Security: contact request" without details and a maintainer will reply with a private channel.

Please include: the version (`python -c "import pardesline; print(pardesline.__version__)"`), the operating system, the manifest or the input that triggers the problem, and what you observed.

## What to expect

- Acknowledgement within 7 days.
- A fix or a mitigation in the next patch release for confirmed reports, with credit in the CHANGELOG unless you prefer otherwise.
- Public disclosure after the fix is on PyPI.

## Design notes that matter for reviewers

- `.npz` files are loaded with `allow_pickle=False`; layouts are declared in manifests, never inferred from pickled metadata.
- Archive members are written under the dataset cache only after their path is checked to stay inside it; `._` and `.DS_Store` members are dropped.
- Downloads are verified against the manifest's SHA-512 or MD5 when present and against the archive index size otherwise; a mismatch deletes the file and raises.
- The MCP server logs to stderr only, refuses paths outside the skills folder and returns structured errors instead of crashing.
- No telemetry. The optional cloud client sends data only when you call its functions.
