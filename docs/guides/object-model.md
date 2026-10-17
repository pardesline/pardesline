---
title: "The object model: PointCloud, Mesh, Volume, LabelMap"
description: "`pl.Object` and its subclasses (PointCloud, Mesh, Volume, LabelMap, Transform, Image, RawArray for .npy/.npz/.bin read through a declared layout): what a l"
---

# The object model: PointCloud, Mesh, Volume, LabelMap

# The object model

```python
import pardesline as pl

ct = pl.load("ct.mha")  # Volume
ct.kind  # "volume"
ct.frame.describe()  # "LPS, mm (file)"   <- read from the header
ct.frame.affine  # 4x4 index->world, from origin/spacing/direction
ct.info()  # {"size": (512,512,29), "spacing": (...), "pixel_type": "16-bit signed integer", ...}
ct.license.describe()  # "unknown licence" until declared
```

## Kinds and classes (by extension; `.nii.gz` aware; a DICOM folder is a Volume)

| Class | kind | extensions |
|---|---|---|
| `PointCloud` | pointcloud | .ply .pcd .xyz .txt .pts .las .laz |
| `Mesh` | mesh | .stl .obj .off .glb .gltf .vtp (a .ply with faces still loads as PointCloud; `to_open3d()` returns the mesh) |
| `Volume` | volume | .vti .vtu .vtk .mha .mhd .nrrd .nii .nii.gz .dcm (file or folder) |
| `LabelMap` | labels | any volume with `labels` declared, a `kind: labels` sidecar, a `labels` role, or `Volume.segment()` / `as_labels()` |
| `Transform` | transform | .tfm .h5 .hdf5 .mat |
| `Image` | image | .png .jpg .tif .bmp |
| `RawArray` | array | .npy .npz .bin .raw: numbers without meaning until a `layout` says what they are (see below) |
| `Object` | file | anything else |

## Raw arrays: a layout, never a guess

```python
raw = pl.load("sweep.bin")  # RawArray; .to_numpy() / ops raise until a layout is declared
sweep = raw.as_points(dtype="float32", shape="(N,4)", columns=["x", "y", "z", "reflectance"])  # PointCloud
sweep = pl.load("sweep.bin", layout={"dtype": "float32", "shape": "(N,4)", "columns": [...]})  # same
grid = pl.load(
    "occ.npz", layout={"key": "occ_label", "shape": "(200,200,16)", "spacing": [0.4] * 3}, kind="labels"
)
occ = raw.as_volume(labels={1: "car"}, key="occ_label", shape="(200,200,16)")  # LabelMap
```

`shape` `"(N,k)"` means points (columns name x, y, z and attributes),
`"(a,b,c)"` a dense grid (x, y, z order; `spacing` / `origin` in the role's
units, else unit spacing with a warning); `dtype` is required for headerless
`.bin`; `key` picks the array in an `.npz`; `scale` rescales colours. The
layout is kept in `obj.layout`, saved in the sidecar, and `with_layout(...)`
amends it. Before any op or hand-off the array is **materialised once** into
a standard file through the layout (PLY for points, MetaImage for grids):
`obj._op_input()`, `to_open3d()`, `to_sitk()`, `info()` use it, and
`obj.save("sweep.ply")` writes that standard file instead of the raw one.
A `.bin` with a wrong layout fails with "do not split into rows" or "does not
match layout.shape", never with silent garbage.

## Frame: file > format > manifest > user, never a guess

`obj.frame` is a `Frame(axes, units, affine, crs, source)`.

- Volumes readable by SimpleITK (.mha .mhd .nrrd .nii .nii.gz .dcm): `axes="LPS"`,
  `units="mm"`, `affine` from the header, `source="file"`. NIfTI RAS headers are
  converted by ITK, so the loaded data *is* LPS.
- glTF (.glb .gltf): `Y-up`, `m`, `source="format"`.
- Everything else: `axes=None`, `units=None` (`frame.known is False`). VTK grids
  (.vti) carry spacing/origin but no convention.
- Declaring: `obj.with_frame("Z-up", "mm")` returns a copy with `source="user"`;
  it fills unknowns and does **not** override what a header stated (a warning is
  logged if a manifest contradicts the file). Manifest roles fill frames with
  `source="manifest"`.
- `obj.units`, `obj.axes` are shortcuts.

## Labels and licence

```python
mask = pl.load("seg.nii.gz").with_labels({1: "liver", 2: "tumor"})  # -> LabelMap
mask.labels, mask.label_id("tumor")  # {1:'liver',2:'tumor'}, 2
obj = obj.with_license("CC-BY-4.0")  # or a dict / pl.License(...)
obj.license.spdx, obj.license.commercial, obj.license.known
```

`pl.License(spdx, commercial, source_url, note, requires_agreement, redistribution)`.

## Provenance and the sidecar

Every `run()` / conversion returns a **new** Object whose `provenance` is the
input's list plus one step dict (`step: "run"|"convert"|"load"`, module, method,
params as sent, input, moving, output, duration_s, pardesline version,
timestamp; for conversions `op`, `label`/`isovalue`, `exact`). Registration
outputs expose `obj.transform` (parsed `<output>.json`) and
`obj.registration_sidecar`.

`obj.save(dest)` copies the file (plus `.raw` sibling for `.mhd`, plus the
registration `.json`) and writes `<dest>.pardesline.json` with kind, frame,
labels, layout, licence, role and provenance. A raw array saved under a
standard extension (`.ply`, `.mha`) is decoded through its layout; a DICOM
folder saved as `.mha` is written as one volume. `pl.load(dest)` reads it back, so the
frame and labels survive a round trip. `dest` ending with `/` or an existing
folder keeps the file name. `sidecar=False` skips it.

## Running algorithms on an object

```python
cloud = pl.load("scan.ply").with_frame("sensor", "m")
clean = cloud.downsample(voxel_size=0.01).remove_outliers(nb_neighbors=20, std_ratio=2.0)
surf = clean.normals().poisson(depth=9).decimate(target_reduction=0.5)
surf.run("pyvista_mesh_processing.pv_fill_holes", hole_size=10.0)
```

`obj.run(method, /, *, moving=None, output=None, timeout=None, on_log=None,
on_progress=None, **params)`. `method` is `"module.method"`, a bare id that is
unique for the file type, or an alias. The result inherits `frame` (affine
dropped: ops write new geometry) and `license`; `labels` are not propagated.
`obj.methods()` lists the qualified names that accept the file; a DICOM
folder is materialised as `.mha` once before ops run on it.

Aliases (explicit methods): `downsample`, `remove_outliers`, `normals`,
`poisson`, `ball_pivoting`, `icp(moving)`, `ransac(moving)`, `decimate`,
`smooth`, `to_points`, `register(moving)`, `segment`.

## Conversions named after the job

| Call | On | What it does | Exact? |
|---|---|---|---|
| `Volume.segment()` | Volume | Otsu threshold (`otsu_threshold`) -> `LabelMap` with `{1: "foreground"}` | - |
| `Volume.segment(lower=, upper=)` | Volume | `manual_threshold` in intensity units -> `LabelMap` | - |
| `Volume.as_labels({1: "liver"})` | Volume | declare an existing volume a label map | - |
| `LabelMap.to_mesh(label=k)` | LabelMap | boundary of voxels == k, in world coordinates (spacing, origin, direction cosines applied), `.ply` | yes (in-process marching cubes at 0.5) |
| `LabelMap.to_mesh()` | LabelMap with a single named label | same, that label | yes |
| `Volume.to_mesh(isovalue=v)` | Volume | level set of a grey-level volume | parametric |
| `Mesh.to_points(num_points=5000)` | Mesh | Poisson-disk sampling (`mesh_to_pcd_poisson_disk`) | exact sampling |
| `PointCloud.to_mesh(depth=9, ...)` | PointCloud | Poisson reconstruction, density-trimmed (`poisson`) | lossy, parametric |
| `PointCloud.align(moving)` | PointCloud | RANSAC on FPFH then ICP (`ransac_icp_pipeline`); transform in `.transform` | - |
| `Volume.align(moving)` | Volume | rigid SimpleITK registration (`rigid`, GEOMETRY init) | - |
| `PointCloud.clean()` / `Mesh.clean()` | | `statistical_outlier_removal` / `pv_clean` | - |
| `PointCloud.segment(eps=, min_points=)` | PointCloud | DBSCAN clusters as colours (`dbscan_clustering`) | - |

Wording for surfaces from points: "a clean, density-trimmed surface", never
"watertight". `to_mesh` on a volume requires exactly one of `label` /
`isovalue`: the package never picks a level.

## Hand-offs

`obj.to_open3d()` (PointCloud or TriangleMesh), `obj.to_pyvista()`
(`pv.read`), `obj.to_sitk()` (SimpleITK image, DICOM folders accepted, VTI
through the PyVista adapter), `obj.to_numpy()` (points, vertices, or voxels
as (z, y, x)). `os.fspath(obj)` gives the path, so any library reader accepts
the object directly. Each raises `pl.MissingDependency` naming the extra.

<sub>Source: `skills/object-model/SKILL.md`, one of the twenty skills served by `pardesline mcp`; published on 2026-10-14.</sub>
