---
name: cloud-client
description: >-
  The optional hosted side of pardesline (`pardesline.cloud`, also reachable as
  `pl.login`, `pl.upload`, `pl.share`...): sign in with email + one-time code or a
  `pl_` key, upload local files or Objects, share with another account in one line,
  run the same 73 methods on the platform (`remote.run(module, method, **params)`),
  GPU methods (image to 3D with Trellis, 2D image AI), browser viewers and public
  share links, projects and saved workflows, the `pl.o3d / pl.pv / pl.sitk / pl.np`
  server-side mirrors when the libraries are not installed locally, quotas and typed
  errors. Use when the user wants to share a result, needs a GPU, has no native
  libraries installed, or mentions appbeta.pardesline.com, an API key or a quota.
---

# The cloud client

Everything else in pardesline runs locally; this module talks to
`https://appbeta.pardesline.com` (override with `PARDESLINE_BASE_URL`). It is
the unchanged 0.1.0 client, now under `pardesline.cloud`; the top-level
helpers forward to a default `Client`.

## Sign in

```python
import pardesline as pl

pl.login()  # email + one-time code in the terminal; key stored in ~/.pardesline/token
pl.login("pl_...")  # a project / API key
pl.whoami()
pl.me()  # account, plan, quotas
pl.logout()
```

Non-interactive: set `PARDESLINE_API_KEY` (CI, notebooks). `PARDESLINE_TOKEN_PATH`
moves the token file. Access requires a trial or a subscription with the API
add-on; GPU methods need the GPU add-on (`pl.GpuAddonRequired`).

## Files and sharing

```python
remote = pl.upload("surface.ply")  # a path or a local pl.Object -> RemoteObject
remote = pl.upload_bytes(data, "scan.ply")
pl.share(remote, to="colleague@lab.org", message="first pass")
pl.send("scan.ply", to="colleague@lab.org")  # upload + share in one call
pl.inbox()
pl.list_files("mine" | "shared" | "all")
obj = pl.read("alice@lab.org/scan.ply")  # by owner/name or by id
obj.download("local.ply")
obj.read_bytes()
obj.download_url(ttl=3600)
obj.share_link()  # public, revocable, login-free viewer link
obj.view()  # URL of the 3D viewer; Volume.view(moving=...) opens the registration studio
pl.view(a, b)
pl.view_registration(fixed, moving, method="rigid")
pl.delete(obj)
```

`RemoteObject` subclasses mirror the local kinds (`PointCloud`, `Mesh`,
`Volume` with `.info()`, `Transform`, `Image`, `Archive`), chosen from the
server's geometry type or the extension.

## Compute on the platform

```python
small = remote.run(
    "point_cloud_processing", "voxel_downsample", voxel_size=0.02
)  # waits, returns a RemoteObject
reg = ct_remote.run("simpleitk_registration", "rigid", moving=mr_remote, num_iterations=200)
job = remote.run("point_cloud_reconstruction", "poisson", wait=False)
job.wait()
job.result()
remote.methods()
remote.params("poisson")
remote.describe("poisson")
remote.poisson(depth=9)
remote.decimate(target_reduction=0.5)  # same aliases as local objects
client = pl.Client()
client.modules.list()
client.modules.describe("sdf", "compute_sdf")
client.samples.list(kind="medical")
client.samples.use("sitk_training_001_ct")  # 77 platform samples
client.pipelines.run([{"module": "...", "method": "...", "params": {...}}, ...], input=remote)
client.jobs.list(status="running")
```

Unknown parameters are rejected client-side from the live catalog
(`/api/v1/modules`) with the accepted list, like the local runner.

## GPU methods (hosted only)

```python
glb = pl.gpu.generate_3d("photo.jpg")  # Trellis image -> 3D (.glb), NVIDIA L4, cold starts of minutes
out = pl.gpu.process_image("photo.jpg", "depth_estimation")  # 2D AI methods: pl.gpu.image_methods()
pl.gpu.gen3d_methods()
```

## Projects and workflows

```python
p = client.projects.create("knee study", module="simpleitk_registration")
p.workflow()
p.save_workflow(graph)
p.run(remote)  # the node-editor DAG, run server-side
client.projects.list()
p.delete()
```

## Library mirrors when nothing is installed locally

`pl.o3d`, `pl.pv`, `pl.sitk`, `pl.np` are the real libraries when importable.
Without them they become lazy, server-executed mirrors (an op-graph sent in one
request): `pcd = pl.o3d.io.read_point_cloud(remote); pl.o3d.geometry.PointCloud.voxel_down_sample(pcd, 0.02)`.
Only whitelisted library roots and public attribute names are reachable;
results come back as values or as RemoteObjects.

## Errors (`pardesline.cloud.errors`, all `PardesLineError` with `.code`, `.status`, `.detail`)

`AuthError` (401: run `pl.login()`), `Forbidden`, `NotFound`, `Conflict`,
`QuotaExceeded` (402: `.quota`, `.used`, `.limit`, `.resets_at`, upgrade
link), `GpuAddonRequired`, `TooLarge`, `RateLimited` (429), `PlatformLocked`
(503 kill-switch), `TransferError`. Free plan quotas: 1 GB storage, 30
files, 10 shares, 1000 API calls per month, 3 projects.

## CLI

`pardesline login | logout | whoami | upload PATH | send PATH EMAIL | inbox |
ls [--scope] | download REF [OUT] [--extract] | share FILE_ID EMAIL`.
