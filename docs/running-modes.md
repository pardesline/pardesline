# Running pardesline on your machine

Everything runs locally: the 73 algorithms, the object model, the datasets and the MCP server.
There is no account, no PardesLine service behind the package, and no network traffic except the
public dataset downloads you ask for.

| Install | What you get |
|---|---|
| `pip install "pardesline[all]"` | everything below |
| `pip install "pardesline[local]"` | point clouds, meshes, SDF, LiDAR (Open3D, PyVista) |
| `pip install "pardesline[medical]"` | volumes, DICOM, registration, segmentation (SimpleITK, PyVista) |
| `pip install "pardesline[hf]"` | `pl.load("hf://...")` |
| `pip install "pardesline[mcp]"` | the MCP server (`pardesline mcp`) |
| `pip install pardesline` | catalog, object model, dataset manifests; no native library |

### Open3D, SimpleITK and PyVista: direct access

The native libraries are not hidden behind the package; they are part of it.

```python
import pardesline as pl

scan = pl.load("scan.ply")  # a typed Object with frame, units, licence, provenance
pcd = scan.to_open3d()  # open3d.geometry.PointCloud (or TriangleMesh)
poly = scan.to_pyvista()  # pyvista.PolyData
img = pl.load("ct.mha").to_sitk()  # SimpleITK.Image - DICOM folders accepted
arr = scan.to_numpy()  # points (N, 3), vertices, or voxels (z, y, x)

pl.o3d, pl.pv, pl.sitk, pl.np  # the real libraries
```

- With `[local]` / `[medical]` installed, `pl.o3d` **is** `open3d`, `pl.sitk`
  **is** `SimpleITK`, `pl.pv` **is** `pyvista`: write ordinary Open3D or
  SimpleITK code on the objects pardesline loaded, and hand the results back
  (`os.fspath(obj)` is the file path, so every library reader accepts an Object).
- Without them, any use of those names raises `MissingDependency` with the extra to install.
- The object keeps its frame, units, labels and licence, and records every step it went
  through (`obj.provenance`).

### From 0.5 and earlier

Versions 0.1 to 0.5 also shipped an optional client for the hosted PardesLine platform
(`pardesline.cloud`, `pl.login`, `pl.upload`, `pl.share`, the `login` / `upload` / `share`
commands, and a remote fallback for `pl.o3d` / `pl.pv` / `pl.sitk`). It was removed in 0.6: the
open-source package is independent of the platform. Code that used it can pin
`pardesline<0.6`.
