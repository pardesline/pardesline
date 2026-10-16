"""Live check of a manifest: list the source, derive samples, fetch one small role, read it.

    python templates/new_dataset/live_check.py <bundled name or path/to/manifest.json> [--take 1]

Prints the sample count, the roles seen, and the header of the first fetched
file. Use it before opening a pull request for a new dataset; paste its output
in the PR description.
"""

from __future__ import annotations

import argparse
import time

import pardesline as pl


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ref")
    ap.add_argument("--take", type=int, default=1, help="samples to fetch (smallest role each)")
    args = ap.parse_args()

    t0 = time.perf_counter()
    ds = pl.load(args.ref)
    ids = ds.ids
    print(f"{ds.name}: {len(ids)} samples listed in {time.perf_counter() - t0:.1f} s")
    print(ds.describe())
    for sample in ds.take(args.take):
        print(f"--- sample {sample.id} roles={sample.roles} fields={sample.fields}")
        role = sample.roles[-1]  # label maps and masks are usually the smallest files
        t1 = time.perf_counter()
        obj = sample.get(role)
        print(f"{role}: {obj.kind} {obj.path.name} fetched in {time.perf_counter() - t1:.1f} s")
        try:
            print(obj.info())
        except Exception as exc:  # the native extra may be missing: say so, do not fail the check
            print(f"info() needs an extra: {exc}")


if __name__ == "__main__":
    main()
