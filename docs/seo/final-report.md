# Final report: making pardesline the reference for 3D vision and medical imaging in Python

Draft of the GitHub Discussion (category Announcements) that closes the mission of 2026-10-16. Everything below is measurable in the repository; the owner-side steps at the end are the ones only the repository owner can click.

## Before and after

| Metric | Before (2026-10-16, 0.2.0 as released) | After (five local commits on `main`) |
|---|---|---|
| README | 109 lines, 9 sections, 4 badges, relative image paths (blank on PyPI) | 358 lines, the 14 sections of the brief, 11 badges, absolute image URLs, executed 30-second demo with its image |
| Datasets table | moved to docs, prose | generated from the 43 manifests (`docs/_gen/datasets_table.py`), licence and loader per row |
| Algorithms & models table | none | classical (16 rows) / deep learning (6) / metrics (2), "validated on" only where an example ran |
| "Defaults that work on real data" | none | side-by-side with committed images and numbers (32.0° vs 0.14° on the bunny), parameter-by-parameter explanation |
| Documented defaults | 371 parameters described, 0 with a rationale | 371 / 371 with rationale, 73 / 73 methods with a validation regime, enforced by a test, printed by `pl.describe` |
| Docstrings (public, non-ops) | 99 / 130 | 130 / 130 |
| Docs site | 5 Markdown pages + a hand-written HTML landing | MkDocs Material, 127 pages: 44 dataset, 21 algorithm, 7 model, 14 guide, 19 how-to, API reference, comparison, FAQ, benchmarks, `llms.txt`; strict build passes |
| Examples | 0 | 13 executed examples with committed images and numbers, each with a README; `examples/real_cases/` mechanism |
| Benchmarks | 0 | 2 (registration, reconstruction), scripts + generated tables |
| Tests | 466 | 497 (templates, docs snippets, catalog rationale, archive safety, `.nii.gz`) |
| CI | 2 workflows, 4 jobs | 6 workflows: lint, mypy, core 3.10/3.13 with coverage, native matrix 3 OS × 3.10/3.13, README-demo job, build, docs (strict + link check + mike), nightly PyPI install, Scorecard, release-please |
| Type check | none | mypy clean on 26 source files |
| PyPI metadata | 12 keywords, 15 classifiers, 6 URLs | 26 keywords, 25 classifiers, 9 URLs unified on the docs site |
| GitHub metadata | description, 20 topics, website (set by the owner before the mission) | 330-character description and a reordered topic set proposed; applied by `docs/seo/apply_github.py` |
| Community files | CONTRIBUTING (54 lines) | CONTRIBUTING (full), CODE_OF_CONDUCT, SECURITY, SUPPORT, CODEOWNERS, 5 issue forms, PR template, Dependabot, pre-commit, all-contributors |
| Templates | 0 | `new_dataset`, `new_algorithm`, `new_model`, `new_pipeline`, tested |
| Issues drafted | 0 | 8 tracking + 16 good first issue + 11 help wanted (`docs/seo/issues-to-create.md`) |
| SEO assets | 0 | keyword map (190 queries), GitHub metadata, launch kit, 12-week calendar, this report |
| Package fixes found on the way | | `.nii.gz` accepted wherever `.nii` is; archives ≤ 64 MB downloaded whole (194 s → seconds on the hippocampus tar); archive member path-traversal guard; Open3D 0.20 accepted (Python 3.13 wheels, native suite green on 3.13) |

Commits, oldest first: `fe4cd1f` SEO foundation · `336fa2d` README + examples + fast path · `6e5e057` documentation site + documented defaults + benchmarks · `5fbbc04` contributor funnel · `237b4ff` CI, type-check, release automation · plus the closing commit with the launch kit, the calendar and this report. 268 files changed. Nothing was pushed: the owner reviews and pushes.

## What is honest about the claims

- "Defaults that work on real data" is backed by public stand-ins (bunny with synthetic noise and partial overlap, RIRE, MSD, KITTI) with committed numbers, and by the mechanism (`examples/real_cases/`) for industrial data. The README says so in the "Validated on real cases" section.
- The deep-learning rows say "reference scripts, no shipped weights, no inference API"; the model registry is the top roadmap item with a tracking issue, a manifest template and reserved URLs.
- The reconstruction benchmark is reported as a trade-off (less ballooning, higher Chamfer), not a win.
- BraTS, ModelNet, ShapeNet and ScanNet are listed as not supported, with the reason.

## Owner-side steps (cannot be done without the owner's credentials or settings)

1. **Push** the five commits and let CI run; the first `docs.yml` run deploys to the `gh-pages` branch with `mike`.
2. **Pages**: Settings → Pages → source `gh-pages` branch, `/ (root)`, once the first docs deployment exists (the current `main` / `docs` source serves the old hand-written landing page).
3. **Codecov**: sign in at codecov.io with the organisation, add `CODECOV_TOKEN` as a repository secret (the badge shows "unknown" until the first upload).
4. **Discussions**: Settings → General → Features → Discussions, then post the four threads of `docs/seo/discussions-seed.md`.
5. **Labels, metadata, issues**: write a classic token with `repo` scope to `C:\Users\mehes\.pardesline-secrets\github_token.txt` (PowerShell `Read-Host`) and run `python docs/seo/apply_github.py --all`; delete the token afterwards.
6. **Zenodo DOI**: at zenodo.org → GitHub, switch the repository on; the next GitHub release is archived with a DOI (`.zenodo.json` carries the metadata); then add the DOI badge to the README and `doi:` to `CITATION.cff`.
7. **Social preview**: Settings → General → Social preview, upload `docs/assets/social-preview.png`.
8. **Branch protection** on `main` (required checks: lint, typecheck, test-core, build): Scorecard scores it.
9. **Release 0.3.0**: merge the release-please pull request when it appears (the README install matrix already says Open3D 0.20 / Python 3.13 "from 0.3.0"); `publish.yml` uploads through Trusted Publishing.
10. **Hugging Face organisation** and **MCP registry** submissions from `docs/seo/launch-kit.md`.

## Not done, and why

- No Colab / Binder badges: the examples are scripts, not notebooks; converting them is a good first issue once Discussions bring the first contributors.
- No benchmark for volume registration or segmentation defaults: listed on the benchmarks tracking issue.
- The `gh` CLI is not installed on the maintainer's machine and no token was provided during the mission, so GitHub writes are scripted, not applied.
- `docs/index.html` (the hand-written landing page) was deleted on 2026-10-17 once Pages switched to the `gh-pages` branch. The first Pages build from that branch failed because mike's default alias is a symbolic link, which the Pages builder refuses; aliases are now copies (`alias_type: copy`).
