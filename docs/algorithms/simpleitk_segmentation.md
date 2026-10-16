---
title: "SimpleITK Segmentation (simpleitk_segmentation): 4 methods in Python"
description: "Medical image segmentation using SimpleITK"
---

# SimpleITK Segmentation

`simpleitk_segmentation`: Medical image segmentation using SimpleITK. Automatic thresholding, region growing, watershed, and connected components for organ/tissue segmentation.

| | |
|---|---|
| Methods | [`otsu_threshold`](#otsu_threshold), [`manual_threshold`](#manual_threshold), [`connected_components`](#connected_components), [`watershed`](#watershed) |
| Input files | `.vti`, `.mha`, `.nrrd`, `.nii` (and `.nii.gz`) |
| Bundled datasets to try | [`rire_brain`](../datasets/rire_brain.md), [`liver_tumor_patient01`](../datasets/liver_tumor_patient01.md), [`visible_human_head_mri`](../datasets/visible_human_head_mri.md), [`spider_lumbar_mri`](../datasets/spider_lumbar_mri.md), [`msd_task04_hippocampus`](../datasets/msd_task04_hippocampus.md), [`msd_task09_spleen`](../datasets/msd_task09_spleen.md) |
| Example | [Threshold segmentation on MSD spleen](../examples.md#spleen_ct_threshold_segmentation) |
| CLI | `pardesline run simpleitk_segmentation.<method> input.ext [--param value]` |

## How it works

Segmentation partitions a medical image $I: \Omega \to \mathbb{R}$ into disjoint regions $\{R_1, R_2, \ldots, R_k\}$ such that $\bigcup_{i} R_i = \Omega$ and $R_i \cap R_j = \emptyset$ for $i \neq j$.

Each region corresponds to an anatomical structure (organ, bone, lesion). The segmentation can be expressed as a labeling function:

$$
L(\mathbf{x}) = \arg\max_{c \in \{1, \ldots, k\}} P(c \mid I(\mathbf{x}))
$$


SimpleITK provides methods ranging from global thresholding (Otsu) to topological segmentation (watershed), each suited to different imaging scenarios.

## Methods

### otsu_threshold

**1. Between-Class Variance Maximization**
Otsu's method finds the optimal threshold $t^*$ that maximizes the between-class variance $\sigma_B^2(t)$ for a bimodal intensity histogram:
$$t^* = \arg\max_t \sigma_B^2(t) = \arg\max_t \, \omega_0(t) \omega_1(t) [\mu_0(t) - \mu_1(t)]^2$$
where $\omega_0, \omega_1$ are the class probabilities and $\mu_0, \mu_1$ are the class means for intensities below and above threshold $t$.

**2. Segmentation**
The binary output is:
$$L(\mathbf{x}) = \begin{cases} 1 & \text{if } I(\mathbf{x}) > t^* \\ 0 & \text{otherwise} \end{cases}$$

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("simpleitk_segmentation.otsu_threshold")  # catalog defaults
# same thing, domain vocabulary: `volume.segment()`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_segmentation.otsu_threshold --input ... --output ...`.

**Defaults validated on:** MSD spleen CT through Volume.segment() (examples/spleen_ct_threshold_segmentation uses the manual window); generated volumes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `number_of_histogram_bins` *(advanced)* | int | `128` | 16 to 512 | Histogram bins for the Otsu criterion. | 128 bins resolve the bimodal histogram of CT (air/tissue) or MR (background/foreground) without the noise of 512. |
| `inside_value` *(advanced)* | int | `1` | 0 to 255 | Foreground label. | 1: the foreground label, so the result is a LabelMap with label 1. |
| `outside_value` *(advanced)* | int | `0` | 0 to 255 | Background label. | 0 is the background label, so the result is a label map with a single foreground label. |

### manual_threshold

**1. Range Thresholding**
A simple but effective segmentation using user-specified intensity bounds $[l, u]$:
$$L(\mathbf{x}) = \begin{cases} 1 & \text{if } l \leq I(\mathbf{x}) \leq u \\ 0 & \text{otherwise} \end{cases}$$

**2. Hounsfield Units**
For CT images, intensities are calibrated in Hounsfield Units (HU):
- Air: $-1000$ HU
- Water: $0$ HU
- Soft tissue: $+40$ to $+80$ HU
- Bone: $+300$ to $+3000$ HU

This allows reproducible thresholds across scanners.

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("simpleitk_segmentation.manual_threshold")  # catalog defaults
# same thing, domain vocabulary: `volume.segment(lower=..., upper=...)`
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_segmentation.manual_threshold --input ... --output ...`.

**Defaults validated on:** MSD spleen CT, 30-200 HU soft-tissue window (examples/spleen_ct_threshold_segmentation); generated volumes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `lower` | float | `100.0` | -1000.0 to 3000.0 | Lower intensity threshold. | 100 HU is the placeholder bone/contrast threshold on CT; Volume.segment(lower, upper) takes the window you mean (30-200 HU soft tissue, 300+ bone). |
| `upper` | float | `1000.0` | -1000.0 to 3000.0 | Upper intensity threshold. | 1000 HU caps the window below metal and dense bone. |
| `inside_value` *(advanced)* | int | `1` | 0 to 255 | Foreground label. | 1: foreground label. |
| `outside_value` *(advanced)* | int | `0` | 0 to 255 | Background label. | 0 is the background label, so the result is a label map with a single foreground label. |

### connected_components

**1. Labeling Algorithm**
After binary thresholding, connected component analysis assigns a unique label $l_i$ to each maximal connected region. Two voxels are connected if they share a face (6-connectivity) or edge (26-connectivity).

**2. Size Filtering**
Small components (noise) are removed by discarding regions with fewer than `min_size` voxels:
$$R_i' = \begin{cases} R_i & \text{if } |R_i| \geq n_{\min} \\ \emptyset & \text{otherwise} \end{cases}$$
where $|R_i|$ denotes the voxel count of region $R_i$.

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("simpleitk_segmentation.connected_components")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_segmentation.connected_components --input ... --output ...`.

**Defaults validated on:** MSD spleen CT after thresholding (examples/spleen_ct_threshold_segmentation, min_size 1000); generated volumes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `threshold` | float | `100.0` | -1000.0 to 3000.0 | Intensity threshold before labeling. | 100 intensity units binarises before labelling; on a LabelMap input use 0.5. |
| `min_size` | int | `15` | 1 to 1000 | Minimum object size in voxels. | 15 voxels removes speckle components; raise to the hundreds or thousands to keep only organs. |
| `upper_threshold` *(advanced)* | float | `255.0` | -1000.0 to 3000.0 | Upper bound for binarization. | 255 is the upper bound for 8-bit inputs; raise it for HU. |
| `fully_connected` *(advanced)* | bool | `false` |  | 26-connectivity (True) vs 6-connectivity (False). | Off (6-connectivity): diagonal-only contacts do not join two structures, which keeps touching organs apart. |
| `inside_value` *(advanced)* | int | `1` | 0 to 255 | Foreground label. | 1: foreground label. |
| `outside_value` *(advanced)* | int | `0` | 0 to 255 | Background label. | 0 is the background label, so the result is a label map with a single foreground label. |

### watershed

**1. Distance Transform**
From a binary mask $B$, the Euclidean distance transform computes:
$$D(\mathbf{x}) = \min_{\mathbf{y} \in \partial B} \|\mathbf{x} - \mathbf{y}\|_2$$
Local maxima of $D$ serve as seed points for the watershed.

**2. Watershed Algorithm**
The watershed treats $-D(\mathbf{x})$ as a topographic surface. Starting from seed points (local minima of $-D$), regions are grown by immersion — flooding the surface from each seed and building dams where floods from different seeds meet.

**3. Pipeline**
The full pipeline is:
1. Binary threshold: $B = \{\mathbf{x} : I(\mathbf{x}) > t\}$
2. Morphological opening: remove small noise
3. Distance transform: $D(\mathbf{x})$
4. Seed generation: local maxima of $D$ with radius $r$
5. Watershed: flood from seeds to produce labels

```python
import pardesline as pl

obj = pl.load("input.vti")
result = obj.run("simpleitk_segmentation.watershed")  # catalog defaults
result.provenance[-1]  # the step, every parameter used, duration, version
```

Output: `.vti`. Script: `python -m pardesline.ops.simpleitk_segmentation.watershed --input ... --output ...`.

**Defaults validated on:** generated volumes in tests/test_ops_smoke.py

| Parameter | Type | Default | Range | What it does | Why this default, when to change it |
|---|---|---|---|---|---|
| `threshold` | float | `100.0` | -1000.0 to 3000.0 | Initial binary threshold. | 100 intensity units for the initial binarisation. |
| `seed_radius` | float | `10.0` | 1.0 to 50.0 | Seed generation radius in mm. | 10 mm: markers are placed where the distance map exceeds this radius, so only objects at least 2 cm across become basins. |
| `min_object_size` | int | `15` | 1 to 1000 | Minimum object size after watershed. | 15 voxels drops speckle basins. |
| `upper_threshold` *(advanced)* | float | `255.0` | -1000.0 to 3000.0 | Upper bound for initial binarization. | 255 for 8-bit inputs. |
| `opening_radius` *(advanced)* | list | `10,10,10` |  | BinaryOpening radius per axis (comma-separated). | 10,10,10 voxels of binary opening detach thin bridges between objects before the distance map. |
| `closing_radius` *(advanced)* | list | `10,10,10` |  | BinaryClosing radius per axis (comma-separated). | 10,10,10 voxels of closing fill small holes inside objects. |
| `distance_inside_is_positive` *(advanced)* | bool | `false` |  | SignedMaurerDistanceMap insideIsPositive. | Off: SimpleITK's convention, inside is negative. |
| `distance_squared` *(advanced)* | bool | `false` |  | SignedMaurerDistanceMap squaredDistance. | Off: true Euclidean distance in mm. |
| `mark_watershed_line` *(advanced)* | bool | `true` |  | Draw watershed dam lines between basins. | On: dam lines between basins are drawn, which shows where touching objects were split. |
| `inside_value` *(advanced)* | int | `1` | 0 to 255 | Foreground label. | 1: foreground label. |
| `outside_value` *(advanced)* | int | `0` | 0 to 255 | Background label. | 0 is the background label, so the result is a label map with a single foreground label. |

## Related

- [Why our defaults work](why-our-defaults-work.md) · [The catalog and `pl.run`](../getting-started/concepts.md#catalog) · [API reference](../api/index.md)
- `pl.describe("simpleitk_segmentation")` prints this module from the installed package; `pl.describe("simpleitk_segmentation.<method>")` one method with ranges and rationale.

<sub>Generated from `src/pardesline/catalog/data/simpleitk_segmentation.json` and `_defaults.json` on 2026-10-16.</sub>
