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

Nothing, except the dataset downloads above and, when the user signs in to
the PardesLine platform (`pl.login()` or `PARDESLINE_API_KEY`), the requests
they make to it: the platform client (`pl.upload`, `pl.share`, `pl.send`...,
to https://appbeta.pardesline.com) and, when Open3D, PyVista or SimpleITK is
not installed, the `pl.o3d` / `pl.pv` / `pl.sitk` calls, which then run on the
platform (a warning says so). A user who is not signed in gets a
`MissingDependency` error for those names, and no request is made. The
platform's own privacy terms apply to that use. The MCP server never calls the
platform.

## The hosted, read-only MCP server (Hugging Face Space)

The Claude plugin directory edition (`plugins/pardesline`) and the Space at
https://huggingface.co/spaces/Jtabet/pardesline connect to a read-only MCP
server hosted on Hugging Face: https://jtabet-pardesline.hf.space/gradio_api/mcp/.
Its six tools list and describe the bundled datasets, the algorithms and the
expert guides. They take a dataset, algorithm or guide name, or a filter, as
arguments, and return public catalogue text. They accept no files, run no
algorithm and download no dataset. PardesLine stores nothing from these calls.
Hugging Face hosts the Space and its own privacy policy
(https://huggingface.co/privacy) applies to the requests it receives.

## Personal data

The package does not collect personal data. Medical files a user points it at
may contain personal data in their headers (DICOM patient fields); pardesline
reads them to process the file, does not store them outside the files the
user asked for, and does not transmit them.

## Contact

Questions: open an issue at https://github.com/pardesline/pardesline/issues.
Security reports follow [SECURITY.md](SECURITY.md).
