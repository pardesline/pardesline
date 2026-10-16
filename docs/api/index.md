---
title: API reference — pardesline
description: The public Python API of pardesline: load, scan, datasets, describe, run, catalog, the Object classes, Dataset, Sample, Manifest and the MCP server, generated from the docstrings.
---

# API reference

The top-level namespace is the public API; everything below is reachable as `pardesline.<name>`.

| | |
|---|---|
| [Data](data.md) | `load`, `scan`, `datasets`, `Dataset`, `Sample`, `Manifest`, `Layout`, `License`, cache settings |
| [Objects](object.md) | `Object`, `PointCloud`, `Mesh`, `Volume`, `LabelMap`, `RawArray`, `Transform`, `Image`, `Frame` |
| [Catalog](catalog.md) | `catalog`, `modules`, `describe`, `Catalog`, `Module`, `Method`, `Parameter` |
| [Runner](runner.md) | `run`, `RunResult`, output directory |
| [MCP server](mcp_server.md) | `build_server`, the `impl_*` functions behind each tool |

::: pardesline
    options:
      members:
        - load
        - scan
        - datasets
        - describe
        - run
        - catalog
        - modules
        - cache_dir
        - set_cache_dir
        - output_dir
        - set_output_dir
      show_root_heading: false
      show_root_toc_entry: false
