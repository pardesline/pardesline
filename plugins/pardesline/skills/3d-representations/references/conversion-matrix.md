# Conversion formulas and what each one loses

## Label map -> surface (exact)

Binary mask `B(i,j,k) = [L(i,j,k) == k]`, marching cubes (flying edges) at
level 0.5. A vertex at index position `p_idx` maps to world coordinates
through the volume's affine:

```
p_world = origin + D · diag(spacing) · p_idx        (D = 3x3 direction cosines)
```

pardesline applies `D` (PyVista `direction_matrix`), so oblique acquisitions
land where the scanner put them. Area and volume of the result are in mm^2 and
mm^3 only if `spacing` is in mm. Smoothing afterwards (Taubin,
`pyvista_mesh_processing.pv_smooth_taubin`, `pass_band` ~0.1) removes the
staircase without shrinking; Laplacian smoothing shrinks.

## Grey volume -> surface (parametric)

Same operation at level `v`. The surface moves with `v`: bone in CT at 200-300
HU, skin at -500 HU, lung parenchyma at -500 to -700 HU. Partial-volume effects
make the surface position depend on the slice thickness; report `v` with the
mesh (pardesline records it in `provenance`).

## Mesh -> points (exact sampling)

Poisson-disk sampling picks points with a minimum distance `r` so that the
density is even; uniform sampling by area is cheaper but clumps. Normals are
taken from the face (`use_triangle_normal=True`) when the mesh is the ground
truth. Number of points `N` sets the resolution: for a tooth of 10 mm and
2 048 points, mean spacing ~0.4 mm.

## Points -> surface (lossy, parametric)

Poisson reconstruction solves `div(V) = div(n)` for an indicator function
whose gradient matches the oriented normal field `n`, on an octree of depth
`d` (cell width = bbox / 2^d). Low-support vertices (where the octree had few
samples) are trimmed by `density_quantile`. What is lost: sharp edges (the
field is smooth), thin sheets thinner than the cell width, anything the normals
did not see. Ball pivoting keeps the input points as vertices (no smoothing)
but leaves holes where the ball radius is too small.

## Surface -> SDF / voxels (parametric)

Signed distance `phi(x) = ±min_y ||x - y||`, sign from the normal (or winding
number for non-manifold input). Sampled on a grid of `voxel_size`; the zero
level set recovers the surface up to one voxel of aliasing. Memory `n^3`.
Occupancy = `phi < 0`. Voxelisation of a non-closed mesh has no inside: close it
first (`pyvista_mesh_processing.pv_fill_holes`).

## Points -> Gaussians (initialisation)

Per point: mean = position; scale `s = log(mean distance to the 3 nearest
neighbours)` so dense regions get tight Gaussians; rotation = identity
quaternion; opacity logit of 0.1; colour as SH degree-0 `f_dc = (rgb - 0.5) /
0.28209`. Covariance `Σ = R S Sᵀ Rᵀ` stays positive semi-definite during
optimisation because `R` is a unit quaternion and `S` is diagonal and
positive. Without images to optimise against, this is a visualisation of the
cloud, not a reconstruction.

## Gaussians -> points (exact means)

Keep the means; weight or drop by opacity `sigmoid(o) < 0.1`. The scale tells
the local footprint; the SH degree-0 term gives a base colour
`rgb = 0.28209 * f_dc + 0.5`.

## Resampling labels and images

Image: linear (or B-spline) interpolation. Labels: nearest-neighbour, or
one-hot -> linear -> argmax when smoothness matters. Never linear on label ids.
When going back to the original grid, use the inverse transform on the fixed
grid (resample *into* the target space), never forward-map voxels.
