# One package, three ways to run the same code

| Mode | What runs where | Needs | Install |
|---|---|---|---|
| **Local** | the 73 algorithms, the object model, the datasets and the MCP server on your machine; Open3D, SimpleITK and PyVista installed next to the package | no account, no network except the dataset downloads you ask for | `pip install "pardesline[all]"` |
| **Cloud** | the same 73 algorithms on the hosted GPU platform, plus sharing, browser viewers, image-to-3D | a PardesLine account (`pl.login()`) | `pip install pardesline` |
| **Mixed** | your pipeline written once; each call runs locally when the library is installed, remotely otherwise | both | either |

The algorithm names, the parameters and the object model are identical in
the three modes: `scan.downsample(voxel_size=0.02)` is the same line on a
laptop without a GPU and on the platform.

### Open3D, SimpleITK and PyVista: direct access, or through the cloud

The native libraries are not hidden behind the package; they are part of it.

```python
import pardesline as pl

scan = pl.load("scan.ply")  # a typed Object with frame, units, licence, provenance
pcd = scan.to_open3d()  # open3d.geometry.PointCloud (or TriangleMesh)
poly = scan.to_pyvista()  # pyvista.PolyData
img = pl.load("ct.mha").to_sitk()  # SimpleITK.Image - DICOM folders accepted
arr = scan.to_numpy()  # points (N, 3), vertices, or voxels (z, y, x)

pl.o3d, pl.pv, pl.sitk, pl.np  # the real libraries, when they are installed
```

- With `[local]` / `[medical]` installed, `pl.o3d` **is** `open3d`, `pl.sitk`
  **is** `SimpleITK`, `pl.pv` **is** `pyvista`: write ordinary Open3D or
  SimpleITK code on the objects pardesline loaded, and hand the results back
  (`os.fspath(obj)` is the file path, so every library reader accepts an Object).
- Without them, after `pl.login()`, the same four names become the **cloud
  mirrors** of the 0.1 client: the call is recorded and executed on the
  platform, the result comes back when you ask for it (`.numpy()`,
  `.to_file()`). No Open3D, VTK or ITK to install, no 3D environment to set
  up - the use case
  [pardesline-use-cases/01](https://github.com/1904jonathan/pardesline-use-cases)
  runs a full registration + label transfer + Poisson pipeline that way.
- Either way the object keeps its frame, units, labels and licence, and
  records every step it went through (`obj.provenance`).

# Cloud (optional)

The hosted platform adds sharing, GPU methods (image → 3D, 2D AI), browser
viewers and a node editor. The 0.1.x client is unchanged, under `pardesline.cloud`
and at the top level; `pl.o3d` / `pl.pv` / `pl.sitk` become its server-side
mirrors when the libraries are not installed locally (see
[One package, three ways to run the same code](#one-package-three-ways-to-run-the-same-code)):

```python
pl.login()  # email + one-time code
remote = pl.upload(surface)  # an Object or a path
pl.share(remote, to="colleague@lab.org")
remote.view()  # link to the 3D viewer
```
