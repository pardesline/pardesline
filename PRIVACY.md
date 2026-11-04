# Privacy

pardesline is a Python package, a command-line tool, a set of skills and a
local MCP server. Everything runs on the user's machine. There is no
pardesline account, no telemetry and no server operated by PardesLine behind
the open-source package.

## What the package reads

- Files the user names: local 3D files, DICOM folders, label maps, manifests.
  They are read to run the requested operation and never leave the machine.
- Public datasets the user asks for, downloaded from their owners' hosts
  (Hugging Face, S3 buckets, TCIA, OpenNeuro, Zenodo, project web servers)
  into the local cache (`~/.cache/pardesline` or `PARDESLINE_CACHE`). Those
  hosts see the same request any browser would make.
- `HF_TOKEN`, read from the environment only when a gated Hugging Face
  dataset is requested, and sent only to huggingface.co. The token is never
  stored by pardesline.

## What the package writes

- Files the user asks for (results, exports, manifests) and their
  `.pardesline.json` sidecars (frame, units, labels, licence, provenance).
- The download cache above.

## What the package sends

Nothing, except the dataset downloads above and, when the user installs the
optional `[cloud]` extra and calls the PardesLine platform client with their
own API key, the requests they make to that platform. The platform's own
privacy terms apply to that use; the local package, the skills and the MCP
server do not use it.

## Personal data

The package does not collect personal data. Medical files a user points it at
may contain personal data in their headers (DICOM patient fields); pardesline
reads them to process the file, does not store them outside the files the
user asked for, and does not transmit them.

## Contact

Questions: open an issue at https://github.com/pardesline/pardesline/issues.
Security reports follow [SECURITY.md](SECURITY.md).
