# The MCP server for AI agents

`pardesline mcp` exposes the datasets, the object model and the 73 algorithms
to any Model Context Protocol client, on the user's machine, without an
account. Twelve tools (`list_datasets`, `describe_dataset`, `list_samples`,
`load_sample`, `scan_dataset`, `confirm_dataset`, `export_dataset`,
`list_methods`, `describe_method`, `run_method`, `describe_object`, `to_mesh`),
three resources and a `start_here` prompt. Questions the package will not
guess (licence, units, array layout) come back as JSON for the agent to relay
to the human.

```bash
pip install "pardesline[mcp]"
pardesline mcp                                            # stdio
pardesline mcp --transport streamable-http --port 8765    # http://127.0.0.1:8765/mcp
```

| Client | Configuration |
|---|---|
| Claude Code | `claude mcp add pardesline -- pardesline mcp` (the repo ships a `.mcp.json`) |
| Claude Desktop, Cursor | `"mcpServers": {"pardesline": {"command": "pardesline", "args": ["mcp"]}}` |
| Gemini CLI | the same block in `~/.gemini/settings.json` |
| Codex CLI | `[mcp_servers.pardesline] command = "pardesline" args = ["mcp"]` in `~/.codex/config.toml` |

If `pardesline` is not on your PATH, the command is `python -m pardesline.mcp_server`.

The `skills/` folder holds twenty skills, grounded in the code and checked
by the test suite (every module, method, parameter and dataset they mention
must exist). Nine teach the package: `using-pardesline` (start here),
`catalog-and-run`, `object-model`, `datasets-and-manifests`,
`scanning-private-folders`, `medical-volumes`, `cloud-client`, `mcp-server`,
`contributing-algorithms`. Eleven are **expert guides with reference scripts**
for the domains the package serves, written for engineers who build the
pipelines, and served to any MCP client through `list_skills` / `get_skill`:

| Skill | What it carries | Runnable script |
|---|---|---|
| `3d-representations` | points vs meshes vs voxels vs splats: memory, architectures, the conversion matrix and its pitfalls | - |
| `point-cloud-registration` | RANSAC + FPFH + ICP, every parameter from one voxel size, metrics that lie, CPD | `registration_eval.py` (pose error on a known transform) |
| `multimodal-rigid-registration` | CT/MR with Mattes MI in SimpleITK: initialiser, optimizer scales, pyramid, validation by TRE | `rigid_ct_mr.py` (RIRE pair, metric trace, checkerboard) |
| `atlas-label-transfer` | labelled atlas -> unlabelled scan: registration, nearest-structure labels, per-label surfaces and volumes | `atlas_label_transfer.py` (99 % label agreement on a synthetic scan) |
| `pointnet-segmentation` | PointNet / PointNet++ step by step, data contract, training recipe | `make_point_dataset.py` (label maps -> labelled clouds), `pointnet_seg.py` (PyTorch) |
| `dinov3-dense-features` | Gram anchoring, frozen backbones, ViTDet pyramid + Faster R-CNN, medical transfer limits | `dinov3_features.py`, `dinov3_faster_rcnn.py` |
| `jepa-pretraining` | latent prediction instead of reconstruction, 3-D tokenisation, masking, collapse diagnostics | `jepa3d_pretrain.py` (3-D ViT, EMA target, block masks) |
| `vae-anomaly-detection` | normal-only training, residual maps, thresholds, honest limits | `vae_anomaly.py` (train / score / AUROC) |
| `gaussian-splatting` | the primitive, the five-step initialisation, PLY layout, training, medical uses | `points_to_gaussians.py` (any cloud -> 3DGS PLY) |
| `medical-segmentation-models` | nnU-Net, TotalSegmentator, transformers, preprocessing, inference, evaluation | `prepare_nnunet_dataset.py` (any dataset -> nnU-Net raw) |
| `evaluation-metrics-3d` | Dice / HD95 / NSD, chamfer / F-score, TRE, folding, AP, AUROC, PSNR, and how to report them | `metrics3d.py` |

Install them as a plugin (it also registers the MCP server):

```
/plugin marketplace add pardesline/pardesline
/plugin install pardesline@pardesline
```
