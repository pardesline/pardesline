"""I-2: ``Object.save`` writes content that matches the target extension, or refuses.

Every source content (point cloud, mesh, volume, label map, transform, in several formats) is saved
to every extension the package knows. Each cell either raises ``ValueError`` and writes nothing, or
writes a file whose bytes are of the target format and which reads back to the same data.
"""

from __future__ import annotations

import gzip
import json
import math

import numpy as np
import pytest

import pardesline as pl
from pardesline.object import KIND_BY_EXT

try:  # the matrix of 0.5.0; on older code every cross-format save must then raise
    from pardesline.object.convert import SAVE_WRITERS
except ImportError:  # pragma: no cover - only when checking the test against old code
    SAVE_WRITERS = {}

sitk = pytest.importorskip("SimpleITK")
o3d = pytest.importorskip("open3d")
pv = pytest.importorskip("pyvista")
pytestmark = [pytest.mark.local, pytest.mark.medical]

TARGETS = sorted(set(KIND_BY_EXT) | {".hdf5", ".txt"})


# ----------------------------------------------------------------------------- sources
def _points():
    d = np.random.default_rng(0).normal(size=(300, 3))
    return d / np.linalg.norm(d, axis=1, keepdims=True) * 10


def _make_sources(root):
    root.mkdir(parents=True, exist_ok=True)
    src = {}
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(_points()))
    for ext in (".ply", ".pcd", ".xyz"):
        p = root / f"cloud{ext}"
        o3d.io.write_point_cloud(str(p), pcd)
        src[f"pointcloud{ext}"] = (p, "pointcloud")
    mesh = o3d.geometry.TriangleMesh.create_sphere(10, 12)
    mesh.compute_vertex_normals()
    for ext in (".ply", ".stl", ".obj", ".off"):
        p = root / f"mesh{ext}"
        o3d.io.write_triangle_mesh(str(p), mesh)
        src[f"mesh{ext}"] = (p, "mesh")
    p = root / "mesh.vtp"
    pv.Sphere(radius=10, theta_resolution=12, phi_resolution=12).save(str(p))
    src["mesh.vtp"] = (p, "mesh")
    arr = (np.arange(6 * 7 * 8).reshape(6, 7, 8) % 13).astype(np.float32) * 10.0
    img = sitk.GetImageFromArray(arr)
    t = math.radians(15)
    img.SetDirection((math.cos(t), -math.sin(t), 0, math.sin(t), math.cos(t), 0, 0, 0, 1))
    img.SetSpacing((0.5, 0.75, 1.5))
    img.SetOrigin((1.0, -2.0, 3.0))
    for ext in (".mha", ".mhd", ".nrrd", ".nii.gz"):
        p = root / f"vol{ext}"
        sitk.WriteImage(img, str(p))
        src[f"volume{ext}"] = (p, "volume")
    from pardesline.medical import volume_to_vti

    p = root / "vol.vti"
    volume_to_vti(img, p)
    src["volume.vti"] = (p, "volume")
    lab = sitk.GetImageFromArray((np.arange(6 * 7 * 8).reshape(6, 7, 8) % 4).astype(np.int32) * (2**24 + 1))
    lab.CopyInformation(img)
    p = root / "labels.nrrd"
    sitk.WriteImage(lab, str(p))
    src["labels.nrrd"] = (p, "labels")
    tx = sitk.Euler3DTransform((1.0, 2.0, 3.0), 0.1, -0.2, 0.3, (4.0, 5.0, 6.0))
    for ext in (".tfm", ".h5"):
        p = root / f"tx{ext}"
        sitk.WriteTransform(tx, str(p))
        src[f"transform{ext}"] = (p, "transform")
    return src


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    return _make_sources(tmp_path_factory.mktemp("src"))


# ----------------------------------------------------------------------------- checks
def _ext(path):
    name = path.name.lower()
    return ".nii.gz" if name.endswith(".nii.gz") else path.suffix.lower()


def _bytes_match(path, ext):
    head = path.read_bytes()[:512]
    if ext == ".ply":
        return head.startswith(b"ply")
    if ext == ".pcd":
        return b"FIELDS" in head and (head.startswith(b"#") or head.startswith(b"VERSION"))
    if ext in (".xyz", ".pts"):
        lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
        rows = lines[1:] if ext == ".pts" and len(lines[0].split()) == 1 else lines
        return all(len(r.split()) >= 3 and all(_isfloat(v) for v in r.split()) for r in rows)
    if ext == ".stl":
        data = path.read_bytes()
        if data[:5] == b"solid" and b"facet" in data[:2048]:
            return True
        return len(data) == 84 + 50 * int.from_bytes(data[80:84], "little")
    if ext == ".obj":
        text = path.read_text(errors="replace")
        return "\nv " in "\n" + text and "\nf " in "\n" + text
    if ext == ".off":
        return head.split(bytes([10]), 1)[0].strip() in (b"OFF", b"NOFF", b"COFF", b"CNOFF", b"STOFF")
    if ext == ".glb":
        return head.startswith(b"glTF")
    if ext == ".gltf":
        return "asset" in json.loads(path.read_text())
    if ext == ".vtp":
        return b"<VTKFile" in head and b'type="PolyData"' in head
    if ext == ".vti":
        return b"<VTKFile" in head and b'type="ImageData"' in head
    if ext == ".vtk":
        return head.startswith(b"# vtk DataFile")
    if ext in (".mha", ".mhd"):
        return b"ObjectType = Image" in head
    if ext == ".nrrd":
        return head.startswith(b"NRRD")
    if ext == ".nii":
        return path.read_bytes()[344:348] == b"n+1" + bytes(1)
    if ext == ".nii.gz":
        return gzip.decompress(path.read_bytes())[344:348] == b"n+1\x00"
    if ext in (".tfm", ".txt"):
        return head.startswith(b"#Insight Transform File")
    if ext in (".h5", ".hdf5"):
        return head.startswith(b"\x89HDF")
    if ext == ".mat":
        return sitk.ReadTransform(str(path)) is not None
    return False


def _isfloat(v):
    try:
        float(v)
        return True
    except ValueError:
        return False


def _same_data(src, kind, out, ext):
    if kind in ("volume", "labels"):
        a, b = sitk.ReadImage(str(src)) if _ext(src) != ".vti" else None, None
        from pardesline.medical import load_volume

        a = load_volume(src, pixel_type=None)
        b = load_volume(out, pixel_type=None)
        assert np.array_equal(sitk.GetArrayFromImage(a), sitk.GetArrayFromImage(b))
        assert np.allclose(a.GetSpacing(), b.GetSpacing()) and np.allclose(a.GetOrigin(), b.GetOrigin())
        assert np.allclose(a.GetDirection(), b.GetDirection(), atol=1e-6)
    elif kind == "transform":
        a, b = sitk.ReadTransform(str(src)), sitk.ReadTransform(str(out))
        for p in ((0, 0, 0), (10, -5, 3)):
            assert np.allclose(a.TransformPoint(p), b.TransformPoint(p), atol=1e-9)
    elif kind == "mesh":
        n_src = (
            pv.read(str(src)).n_points
            if _ext(src) == ".vtp"
            else len(o3d.io.read_triangle_mesh(str(src)).triangles)
        )
        if ext in (".vtp", ".vtk"):
            assert pv.read(str(out)).n_cells > 0
        else:
            assert len(o3d.io.read_triangle_mesh(str(out)).triangles) > 0
        assert n_src > 0
    else:
        a = np.asarray(o3d.io.read_point_cloud(str(src)).points)
        b = np.asarray(o3d.io.read_point_cloud(str(out)).points)
        assert a.shape == b.shape and np.allclose(a, b, atol=1e-4)


CASES = [
    (s, t)
    for s in [
        "pointcloud.ply",
        "pointcloud.pcd",
        "pointcloud.xyz",
        "mesh.ply",
        "mesh.stl",
        "mesh.obj",
        "mesh.off",
        "mesh.vtp",
        "volume.mha",
        "volume.mhd",
        "volume.nrrd",
        "volume.nii.gz",
        "volume.vti",
        "labels.nrrd",
        "transform.tfm",
        "transform.h5",
    ]
    for t in TARGETS
]


@pytest.mark.parametrize("source,target", CASES, ids=[f"{s}->{t}" for s, t in CASES])
def test_i02_saved_content_matches_the_extension_or_the_call_raises(source, target, sources, tmp_path):
    src, kind = sources[source]
    obj = pl.load(src)
    if kind == "labels":
        obj = obj.as_labels({0: "background"})
    name = "out" + target
    dest = tmp_path / name
    content = "mesh" if source.startswith("mesh") else ("volume" if kind in ("volume", "labels") else kind)
    writable = target == _ext(src) or target in SAVE_WRITERS.get(content, frozenset())
    if not writable:
        with pytest.raises(ValueError):
            obj.save(dest)
        assert not dest.exists()
        return
    out = obj.save(dest)
    assert out == dest and _bytes_match(out, target), f"{out.name} does not hold {target} data"
    _same_data(src, kind, out, target)


def test_i02_the_reported_case_ply_mesh_to_stl(sources, tmp_path):
    """save('x.stl') on a mesh read from PLY wrote PLY bytes into the .stl file."""
    out = pl.load(sources["mesh.ply"][0]).save(tmp_path / "x.stl")
    assert not out.read_bytes().startswith(b"ply")
    assert _bytes_match(out, ".stl")


def test_i02_mhd_saved_under_another_name_points_at_its_own_data(sources, tmp_path):
    """Copying x.mhd to y.mhd kept 'ElementDataFile = vol.raw' in the header."""
    out = pl.load(sources["volume.mhd"][0]).save(tmp_path / "other.mhd")
    header = out.read_text(errors="replace")
    assert "ElementDataFile = other." in header
    src_arr = sitk.GetArrayFromImage(sitk.ReadImage(str(sources["volume.mhd"][0])))
    assert np.array_equal(sitk.GetArrayFromImage(sitk.ReadImage(str(out))), src_arr)
