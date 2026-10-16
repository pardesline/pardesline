---
title: MCP server for computer vision and medical imaging — give 3D datasets and algorithms to Claude, Cursor, Gemini CLI and Codex
description: pardesline mcp is a local Model Context Protocol server with 14 tools over 43 datasets, 73 algorithms and 20 expert guides. Setup in five lines for Claude Code, Claude Desktop, Cursor, Gemini CLI and Codex; what an agent can do with it.
---

# MCP server

`pardesline mcp` turns the package into a local [Model Context Protocol](https://modelcontextprotocol.io/) server: an agent can list and describe datasets, fetch one sample, run any catalog method with validated parameters, convert objects, export standard files and read the twenty expert guides. Nothing leaves the machine; there is no account.

## Setup

=== "Claude Code"

    ```bash
    pip install "pardesline[mcp]"
    claude mcp add pardesline -- pardesline mcp
    ```

    The repository also ships `.mcp.json` (picked up when you open the repo) and a Claude Code plugin manifest (`.claude-plugin/plugin.json`) that declares the server and the twenty skills.

=== "Claude Desktop / Cursor"

    ```json
    {
      "mcpServers": {
        "pardesline": { "command": "pardesline", "args": ["mcp"] }
      }
    }
    ```

    Claude Desktop: `claude_desktop_config.json`. Cursor: Settings → MCP → add server, or `.cursor/mcp.json` in the project.

=== "Gemini CLI"

    Add the same block to `~/.gemini/settings.json`.

=== "Codex"

    ```toml
    [mcp_servers.pardesline]
    command = "pardesline"
    args = ["mcp"]
    ```

=== "HTTP"

    ```bash
    pardesline mcp --transport streamable-http --port 8765     # http://127.0.0.1:8765/mcp
    ```

When `pardesline` is not on `PATH`, use `python -m pardesline.mcp_server` as the command.

## Tools

| Tool | What it does |
|---|---|
| `list_datasets(tag, scheme, medical_only)` | the 43 bundled manifests with title, licence, tags |
| `describe_dataset(ref, count_samples)` | roles, frames, units, labels, licence, citation of a bundled name, an `hf://` / `tcia://` / `s3://` URI, a manifest path or a folder |
| `list_samples(ref, limit, offset, **fields)` | sample ids and fields, paged |
| `load_sample(ref, sample, role, standard)` | fetches one role: path, kind, frame, units, labels, licence, provenance, the methods that accept it, and `standard_path` (PLY / MetaImage) for raw arrays and DICOM folders |
| `scan_dataset(ref)` | drafts a manifest for a folder or a Hub repo and returns the questions |
| `confirm_dataset(ref, answers, save_to)` | answers the questions, saves the manifest |
| `export_dataset(ref, folder, take, overwrite)` | standard files + sidecars + manifest |
| `list_methods(extension, module)` | the catalog, filtered by file type |
| `describe_method(method)` | parameters with type, default, range, description and rationale |
| `run_method(method, input, moving, output, params)` | runs one method; returns the output path and the recorded step |
| `describe_object(path)` | kind, frame, units, labels, sidecar of any file |
| `to_mesh(path, label, isovalue)` | label map or volume to a surface |
| `list_skills()`, `get_skill(name, file)` | the twenty expert guides and their scripts |

Resources: `pardesline://datasets`, `pardesline://manifest/{name}`, `pardesline://catalog`, `pardesline://skills`, `pardesline://skill/{name}`. Prompt: `start_here`.

## What an agent does with it

1. `list_datasets(tag="ct")` → picks `msd_task09_spleen`; `describe_dataset` tells it the mask has label 1 = spleen under CC-BY-SA 4.0.
2. `load_sample("msd_task09_spleen", 0, "ct")` fetches one 30 MB volume out of the 1.6 GB tar and says which methods accept it.
3. `get_skill("medical-volumes")` before touching HU windows; `describe_method("simpleitk_segmentation.manual_threshold")` for the parameters and why they are what they are.
4. `run_method(...)`, `to_mesh(...)`, `export_dataset(...)`: files on disk with sidecars, paths returned.

Questions the package will not guess (licence, units, label names, array layout) come back as structured JSON (`{"error": "NeedsConfirmation", "questions": [...]}`) for the agent to relay to the human, then `confirm_dataset`. Errors are returned as JSON too; the server never dies on a bad call. Logs go to stderr, never to the protocol channel.

## Contract and tests

The full tool contract, the error shapes and the client details are in [MCP reference](../mcp.md). `tests/test_mcp_server.py` exercises every tool in-process and runs a stdio round trip with the official MCP client, which is what every external client does.

The server is Apache-2.0 like the rest of the package; MCP registries can list it from the repository's `.mcp.json`.
