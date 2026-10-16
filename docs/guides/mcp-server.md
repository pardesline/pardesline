---
title: "The MCP server"
description: "Run and use pardesline as a local MCP server (`pardesline mcp`, `pip install "pardesline[mcp]"`): the stdio / streamable-http transports, the configuration"
---

# The MCP server

# The pardesline MCP server

```bash
pip install "pardesline[mcp]"        # or [all]
pardesline mcp                        # stdio: what every MCP client spawns
pardesline mcp --transport streamable-http --port 8765   # http://127.0.0.1:8765/mcp
```

Everything runs on the user's machine, without a PardesLine account. The only
network traffic is the downloads the user asks for (one sample at a time).
Logs go to stderr (`PARDESLINE_LOG=DEBUG`); stdout is the protocol channel.

## Connecting a client

| Client | Configuration |
|---|---|
| Claude Code | `claude mcp add pardesline -- pardesline mcp` (or the repo's `.mcp.json`; the plugin declares the server too) |
| Claude Desktop | `claude_desktop_config.json`: `"mcpServers": {"pardesline": {"command": "pardesline", "args": ["mcp"]}}` |
| Cursor | `.cursor/mcp.json`: same `mcpServers` block |
| Gemini CLI | `~/.gemini/settings.json`: `"mcpServers": {"pardesline": {"command": "pardesline", "args": ["mcp"]}}` |
| Codex CLI | `~/.codex/config.toml`: `[mcp_servers.pardesline] command = "pardesline" args = ["mcp"]` |
| Any HTTP client | `pardesline mcp --transport streamable-http --port 8765`, endpoint `http://127.0.0.1:8765/mcp` |

When `pardesline` is not on PATH, use `python -m pardesline.mcp_server` as the
command (same arguments).

## Tools (all return JSON; errors are `{"error", "message", "code"}`)

| Tool | What it does |
|---|---|
| `list_datasets(tag?, scheme?, medical_only?)` | the 43 bundled manifests: name, source, licence, roles |
| `describe_dataset(ref, count_samples?)` | roles, licence, citation, layout of a bundled name or any `hf://`, `s3://`, `tcia://`, folder |
| `list_samples(ref, limit?, offset?, filters?)` | paged sample ids, roles, fields; nothing downloaded |
| `load_sample(ref, sample, role, standard?)` | downloads ONE file or DICOM series; returns `path`, `kind`, `frame`, `units`, `labels`, `license`, `provenance`, accepted `methods`, and `standard_path` (PLY / MetaImage) for raw arrays and DICOM folders |
| `scan_dataset(ref)` | draft manifest + `questions` for a private folder or unknown source |
| `confirm_dataset(ref, answers, save_to?)` | applies the human's answers, loads, saves the manifest |
| `export_dataset(ref, folder, take?, overwrite?)` | standard copy with sidecars and a manifest |
| `list_methods(extension?, category?)`, `describe_method(method)` | the catalog |
| `run_method(method, input_path, moving_path?, params?, output_path?, timeout?)` | one algorithm on a local file, parameters validated first |
| `describe_object(path, layout?, kind?)` | what a local 3D file knows about itself |
| `to_mesh(path, label?, isovalue?, output_path?)` | exact surface of a label map, or an isosurface |

Resources: `pardesline://datasets` (JSON list), `pardesline://manifest/{name}`
(one manifest), `pardesline://catalog`. Prompt: `start_here`.

## The question contract (for the agent)

`scan_dataset` and a premature `confirm_dataset` return
`{"error": "NeedsConfirmation", "questions": [{"field": "roles.sweep.layout", "message": ...}],
"how_to_answer": ...}`. Relay the questions to the human, collect the answers,
call `confirm_dataset(ref, answers)` once. Answer keys: `license` (SPDX id or
free text such as "internal, no redistribution"), `pairing`, `units` and
`frame` (one value or `{role: value}`), `labels` (`{role: {"1": "liver"}}`),
`types` (`{role: "points" | "mesh" | "volume" | "labels" | "image"}`), `layout`
(`{role: {"dtype", "shape", "columns", "key"}}`). Never invent a licence or a
layout; say "unknown" and let the human decide. Gated sources return a
`FetchError` naming the step the human must take (accept terms, set `HF_TOKEN`).

## Typical flow

1. `list_datasets(medical_only=true)` or `describe_dataset("tcia://Pancreas-CT")`.
2. `list_samples(ref, filters={"split": "Tr"})`.
3. `load_sample(ref, "la_007", "mask")` -> `path`, `labels={"1": "left_atrium"}`.
4. `to_mesh(path, label=1)` -> surface in LPS mm, or `run_method("pyvista_mesh_processing.pv_decimate", path, params={"target_reduction": 0.5})`.
5. Tell the user the licence (`license_text`) before they redistribute anything.

## Implementation facts

`src/pardesline/mcp_server.py`, FastMCP from the official `mcp` SDK (>= 1.2).
Tool bodies are synchronous (`impl_*` functions, testable without a server)
and run in a worker thread; `build_server()` registers them. Tests:
`tests/test_mcp_server.py` (in-process calls and a stdio round trip with the
real client).

<sub>Source: `skills/mcp-server/SKILL.md`, one of the twenty skills served by `pardesline mcp`; published on 2026-10-16.</sub>
