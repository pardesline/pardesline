# LinkedIn — launch of pardesline 0.3.0 (contrarian / founder)

- **Goal:** reach + contributors · **Product:** pardesline (open source) · **Funnel:** top
- **Visual:** `launch_side_by_side.png` (one image, no carousel) · **CTA kw:** REPO
- **Format:** text + one image · **Best slot:** Tue–Thu, 15:00–17:00 Israel time (hits EU afternoon and US morning)

## Post (copy-paste; no link in the body)

```
Your ICP converged. Fitness 0.98. The part is 32 degrees off.

That is the Open3D tutorial call on a real partial scan.
And the metric says "success".

I measured it on the Stanford bunny: a second "scan" rotated 35°, 70 % overlap, 0.5 % noise, five noise draws.

• Tutorial ICP: 32.5° off
• Tutorial RANSAC with its fixed 0.05 m voxel: 134.5° off
• Defaults derived from the data: 0.11° off, RMSE at the noise floor

Why ICP fails here: it is a local optimiser. A 35° start is outside its basin, so it stops where it began. Fitness counts pairs inside a fixed 0.02 threshold, and the overlap satisfies that from the identity.

Why RANSAC fails: the voxel is hard-coded for a room, not for a 15 cm part.

The fix is not a smarter algorithm. It is tying every distance to the scan's own scale (voxel = 1.3 % of the bounding-box diagonal, every threshold a multiple of it, RANSAC on FPFH first, ICP second, coarse to fine) and writing down why.

So I did that for 73 algorithms: 371 parameters, each with its rationale and the data it was checked on, printed by one describe() call. Plus 43 public 3D and medical datasets (KITTI, Decathlon, TCIA, RIRE, TotalSegmentator…) loaded in one line with their licences. Open3D, PyVista and SimpleITK underneath. Apache-2.0, Python 3.10 to 3.13. Version 0.3.0 shipped today.

I need contributors, not stars: a dataset manifest, a default you disagree with, a scan that breaks it.

Comment REPO and I will send you the repository and the benchmark page.

Which default bit you last: the ICP threshold, or the Poisson depth?
```

## First comment (post immediately after)

```
Repository: https://github.com/pardesline/pardesline
Benchmark (script + numbers): https://pardesline.github.io/pardesline/benchmarks/
Why our defaults work, failure mode by failure mode: https://pardesline.github.io/pardesline/algorithms/why-our-defaults-work/
pip install "pardesline[all]"
```

## Replies to prepare (first hour)

- To every "REPO": the two links above in a DM or reply, plus one question back ("what do you register, parts or anatomy?").
- "Why not just lower the threshold?": a lower threshold does not move ICP out of its basin, it only makes fitness honest; the global stage is what fixes the pose.
- "Poisson?": the second benchmark: our trimmed surface has 0.8 % of its area farther than 2 mm from truth vs 3.4 % for the default, at a higher Chamfer (1.14 vs 0.80 mm). A trade-off, stated as such on the benchmarks page.
- "Weights / models?": reference scripts (PointNet, DINOv2/3 features, JEPA, VAE), no shipped weights yet; the model registry is the top roadmap item.

## Meta

Hashtags (end of body or first comment): #ComputerVision #PointCloud #MedicalImaging #Open3D #Python
Checklist: hook 62 chars ✓ · counter-intuitive ✓ · no body link ✓ · comment-keyword CTA ✓ · first comment seeded ✓ · question at the end ✓ · every number from `benchmarks/results.md` or `examples/icp_registration_bunny/result.json` ✓
