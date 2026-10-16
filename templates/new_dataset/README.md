# Template: a new dataset manifest

Copy this folder's `manifest.json` to `src/pardesline/data/manifests/<name>.json`, fill it, and follow the checklist. The manifest describes where the files are, how they group into samples and what the files cannot say by themselves; it never embeds data and never guesses.

## Steps

1. **Probe the source.** Before writing anything, list it:
   - Hugging Face: `HfApi().list_repo_tree(repo, path_in_repo="<subfolder>", recursive=True)`, one sub-folder at a time with a pause between calls (anonymous listing of large repos ends in HTTP 429). Licence from `HfApi().dataset_info(repo).card_data`.
   - zip or tar on a server: check that `GET` with `Range: bytes=0-0` answers 206, then `python -c "from pardesline.data.sources.archive import RemoteZip, _Ranged; ..."` or simply write the manifest and run `pl.load(path).ids`: the archive source indexes it.
   - TCIA: `https://services.cancerimagingarchive.net/nbia-api/services/v1/getSeries?Collection=<name>` lists the series; the licence is on the collection page.
   - S3 bucket: `https://s3.amazonaws.com/<bucket>/?list-type=2&prefix=<prefix>`.
2. **Fill `manifest.json`.** Every field is explained inline. Delete the fields that do not apply. Role names are lower-case identifiers; patterns use `{id}` (or several placeholders that join into the id) and `*`.
3. **Validate offline.**
   ```bash
   python -c "import pardesline as pl; print(pl.describe('src/pardesline/data/manifests/<name>.json'))"
   pytest -q tests/test_manifest.py
   ```
4. **Check live.** `python templates/new_dataset/live_check.py <name>`: lists the source, derives the samples, fetches the smallest role of the first sample, prints what it read. Compare the sample count with the source's own count.
5. **Wire it in.** A row in `docs/datasets.md` and in the `datasets-and-manifests` skill table; `tests/test_skills.py` prefixes if the name starts with a new prefix; a CHANGELOG line. The docs page and the README table are generated.

## Rules

- Licence: copy the exact wording and where you found it, with the date, into `license.note`. `spdx` only when it is a standard licence. `requires_agreement: true` for gated sources. Never mirror data.
- Raw arrays (`.npy`, `.npz`, `.bin`, `.raw`) must have a `layout`.
- Label maps should name their labels; if the source does not, say so in the role description.
- Keep `size_mb` honest (the whole source) and the description factual: how it is read (Range, API), how many samples, what one sample costs.
