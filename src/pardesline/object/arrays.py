"""Raw arrays (``.npy``, ``.npz``, ``.bin``) read through a declared layout.

A raw array says nothing about what its numbers mean: KITTI's ``.bin`` is
float32 ``(N,4)`` x, y, z, reflectance; a KITTI-360 chunk is ``coord.npy``
``(N,3)``; an occupancy grid is ``(L,W,H)`` class ids. The layout comes from
the manifest (or from the caller); nothing here guesses it. Decoded data is
materialised in a standard file (PLY for points, MetaImage for grids) so the
catalog ops - which read files - run unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from ..errors import ManifestError, MissingDependency

if TYPE_CHECKING:
    from ..data.manifest import Layout

__all__ = [
    "ARRAY_EXTS",
    "array_to_points",
    "array_to_volume",
    "decode_points",
    "is_array_file",
    "load_array",
    "write_ply",
]

# Raw arrays: the file says nothing about what the numbers mean. A role that
# points at one of these must carry a ``layout``; the package never guesses it.
ARRAY_EXTS = frozenset({".npy", ".npz", ".bin", ".raw"})

_XYZ = ("x", "y", "z")
_RGB = ("r", "g", "b")
_RGB_LONG = ("red", "green", "blue")
_NORMALS = ("nx", "ny", "nz")


def is_array_file(path: str | os.PathLike) -> bool:
    """True for ``.npy``, ``.npz``, ``.bin`` and ``.raw`` files.

    Numbers that need a layout to mean anything.
    """

    low = str(path).lower()
    return any(low.endswith(ext) for ext in ARRAY_EXTS)


def _layout(layout: Layout | dict[str, Any] | None, where: str) -> Layout:
    from ..data.manifest import Layout  # local import: data imports object, not the reverse

    if layout is None:
        raise ManifestError(
            f"{where}: a raw array needs a layout (dtype, shape, columns / key); the package never "
            "guesses one. Pass layout={'dtype': 'float32', 'shape': '(N,4)', "
            "'columns': ['x','y','z','reflectance']} or declare it in the manifest role."
        )
    return layout if isinstance(layout, Layout) else Layout.model_validate(layout)


def load_array(path: str | os.PathLike, layout: Layout | dict[str, Any] | None) -> np.ndarray:
    """Read the array exactly as the layout says. ``.npy``/``.npz`` carry
    their own dtype and shape (checked against the layout); ``.bin``/``.raw``
    need ``dtype`` and a ``shape`` whose last dimensions are fixed."""
    p = Path(path)
    lay = _layout(layout, p.name)
    low = p.name.lower()
    if low.endswith(".npy"):
        arr = np.load(p, allow_pickle=False, mmap_mode="r")
    elif low.endswith(".npz"):
        with np.load(p, allow_pickle=False) as z:
            keys = list(z.files)
            key = lay.key
            if key is None:
                if len(keys) != 1:
                    raise ManifestError(f"{p.name} holds {keys}; the layout must say which 'key' to read.")
                key = keys[0]
            if key not in keys:
                raise ManifestError(f"{p.name} has no array {key!r}; available: {keys}")
            arr = np.asarray(z[key])
    else:  # headerless
        if not lay.dtype:
            raise ManifestError(f"{p.name}: a headerless array needs layout.dtype (e.g. 'float32').")
        dims = lay.dims()
        fixed = [d for d in dims if d is not None]
        if len(fixed) != len(dims) - 1 or dims[0] is not None:
            raise ManifestError(
                f"{p.name}: layout.shape must be '(N,k[,m...])' with one open leading dimension, "
                f"got {lay.shape!r}"
            )
        flat = np.fromfile(p, dtype=np.dtype(lay.dtype))
        width = int(np.prod(fixed)) if fixed else 1
        if flat.size % width:
            raise ManifestError(
                f"{p.name}: {flat.size} values of {lay.dtype} do not split into rows of {fixed}; "
                "the layout does not match this file."
            )
        arr = flat.reshape((-1, *fixed), order=lay.order)
    if lay.dtype and low.endswith((".npy", ".npz")) and np.dtype(lay.dtype) != arr.dtype:
        # a declared dtype on a self-describing file is a cross-check, not a cast
        raise ManifestError(f"{p.name}: file dtype {arr.dtype} differs from layout.dtype {lay.dtype}")
    dims = lay.dims()
    if dims:
        if arr.ndim != len(dims):
            raise ManifestError(f"{p.name}: file shape {arr.shape} does not match layout.shape {lay.shape}")
        for got, want in zip(arr.shape, dims, strict=True):
            if want is not None and got != want:
                raise ManifestError(
                    f"{p.name}: file shape {arr.shape} does not match layout.shape {lay.shape}"
                )
    return arr


def decode_points(
    path: str | os.PathLike, layout: Layout | dict[str, Any] | None
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """``(xyz float64 (N,3), attributes)`` from a points array. Columns are
    taken from the layout; without ``columns`` the first three are x, y, z
    and the rest are kept as ``col_<i>``."""
    p = Path(path)
    lay = _layout(layout, p.name)
    arr = np.asarray(load_array(p, lay))
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ManifestError(f"{p.name}: points need an (N,k>=3) array, got {arr.shape}")
    cols = list(lay.columns or [])
    if cols and len(cols) != arr.shape[1]:
        raise ManifestError(f"{p.name}: layout lists {len(cols)} columns but the array has {arr.shape[1]}")
    if not cols:
        cols = list(_XYZ) + [f"col_{i}" for i in range(3, arr.shape[1])]
    low = [c.lower() for c in cols]
    try:
        ix = [low.index(c) for c in _XYZ]
    except ValueError:
        raise ManifestError(f"{p.name}: layout.columns must name x, y and z; got {cols}") from None
    xyz = arr[:, ix].astype(np.float64, copy=False)
    attrs: dict[str, np.ndarray] = {}
    for i, name in enumerate(low):
        if i in ix:
            continue
        attrs[name] = np.asarray(arr[:, i])
    if lay.scale is not None:
        for key in list(attrs):
            if key in _RGB or key in _RGB_LONG or key in ("intensity", "reflectance"):
                attrs[key] = attrs[key].astype(np.float64) * lay.scale
    return xyz, attrs


def write_ply(path: str | os.PathLike, xyz: np.ndarray, attrs: dict[str, np.ndarray] | None = None) -> Path:
    """Binary little-endian PLY with x y z (double), optional colours
    (uchar red green blue), normals (nx ny nz) and one float property per
    other attribute. No dependency: pure NumPy."""
    attrs = dict(attrs or {})
    n = int(xyz.shape[0])
    fields: list[tuple[str, str, np.ndarray]] = [
        ("x", "double", xyz[:, 0]),
        ("y", "double", xyz[:, 1]),
        ("z", "double", xyz[:, 2]),
    ]
    rgb = None
    for names in (_RGB, _RGB_LONG):
        if all(k in attrs for k in names):
            rgb = np.stack([np.asarray(attrs.pop(k), dtype=np.float64) for k in names], axis=1)
            break
    if rgb is not None:
        if rgb.max() <= 1.0:
            rgb = rgb * 255.0
        rgb = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
        for i, name in enumerate(_RGB_LONG):
            fields.append((name, "uchar", rgb[:, i]))
    if all(k in attrs for k in _NORMALS):
        for k in _NORMALS:
            fields.append((k, "double", np.asarray(attrs.pop(k), dtype=np.float64)))
    for k, v in attrs.items():
        v = np.asarray(v)
        if v.ndim != 1 or v.shape[0] != n:
            continue  # not a per-point scalar
        if v.dtype.kind in "iu":
            fields.append((k, "int", v.astype(np.int32)))
        else:
            fields.append((k, "float", v.astype(np.float32)))
    dtype = np.dtype(
        [
            (name, {"double": "<f8", "float": "<f4", "uchar": "u1", "int": "<i4"}[typ])
            for name, typ, _ in fields
        ]
    )
    rec = np.empty(n, dtype=dtype)
    for name, _typ, col in fields:
        rec[name] = col
    header = ["ply", "format binary_little_endian 1.0", f"element vertex {n}"]
    header += [f"property {typ} {name}" for name, typ, _ in fields]
    header.append("end_header")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fp:
        fp.write(("\n".join(header) + "\n").encode("ascii"))
        fp.write(rec.tobytes())
    return out


def array_to_points(
    path: str | os.PathLike, layout: Layout | dict[str, Any] | None, out_path: str | os.PathLike
) -> dict[str, Any]:
    """Materialise a points array as PLY. Returns a provenance step."""
    xyz, attrs = decode_points(path, layout)
    out = write_ply(out_path, xyz, attrs)
    return {
        "step": "convert",
        "op": "array_to_points",
        "input": str(path),
        "output": str(out),
        "n_points": int(xyz.shape[0]),
        "attributes": sorted(attrs),
        "exact": True,
    }


def array_to_volume(
    path: str | os.PathLike, layout: Layout | dict[str, Any] | None, out_path: str | os.PathLike
) -> dict[str, Any]:
    """Materialise a dense grid as MetaImage (``.mha``). The layout's
    ``spacing`` / ``origin`` (in the role's units) set the geometry; without
    them the grid gets unit spacing at the origin and the caller is told so."""
    try:
        import SimpleITK as sitk
    except ImportError:
        raise MissingDependency("SimpleITK", "medical") from None
    p = Path(path)
    lay = _layout(layout, p.name)
    arr = np.asarray(load_array(p, lay))
    if arr.ndim != 3:
        raise ManifestError(f"{p.name}: a grid needs a 3-D array, got shape {arr.shape}")
    if arr.dtype == np.bool_:
        arr = arr.astype(np.uint8)
    elif arr.dtype.kind in "iu" and arr.dtype.itemsize > 4:
        arr = arr.astype(np.int32)
    # the layout's shape is (L,W,H) == (x,y,z); SimpleITK wants (z,y,x) in memory
    img = sitk.GetImageFromArray(np.ascontiguousarray(np.transpose(arr, (2, 1, 0))))
    geometry_known = bool(lay.spacing)
    if lay.spacing:
        img.SetSpacing([float(s) for s in lay.spacing])
    if lay.origin:
        img.SetOrigin([float(o) for o in lay.origin])
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(out))
    return {
        "step": "convert",
        "op": "array_to_volume",
        "input": str(p),
        "output": str(out),
        "shape": [int(s) for s in arr.shape],
        "spacing": list(lay.spacing) if lay.spacing else None,
        "origin": list(lay.origin) if lay.origin else None,
        "geometry_known": geometry_known,
        "exact": True,
    }
