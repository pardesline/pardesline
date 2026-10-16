"""Apply the GitHub metadata, labels and issues through the REST API.

    python docs/seo/apply_github.py --check                 # token works, repo reachable
    python docs/seo/apply_github.py --metadata              # description, homepage, topics, discussions on
    python docs/seo/apply_github.py --labels                # create or update the labels
    python docs/seo/apply_github.py --issues                # create the tracking, good-first and help-wanted issues
    python docs/seo/apply_github.py --all

The token is read from %USERPROFILE%/.pardesline-secrets/github_token.txt (a
classic token with the `repo` scope; fine-grained tokens must be created with
the organisation as resource owner). Nothing is sent to any other host. Issues
are matched by title so the script can be re-run without duplicates.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "pardesline/pardesline"
API = f"https://api.github.com/repos/{REPO}"
TOKEN_FILE = Path.home() / ".pardesline-secrets" / "github_token.txt"
HERE = Path(__file__).parent

DESCRIPTION = (
    "Python library for 3D computer vision and medical imaging. Load 43 public 3D and medical datasets "
    "(MSD, TCIA, TotalSegmentator, KITTI, Hugging Face) in one line with manifests and licences; run 73 "
    "algorithms (ICP/RANSAC registration, segmentation, reconstruction) on point clouds, meshes, CT/MRI "
    "volumes; MCP server for AI agents."
)
HOMEPAGE = "https://pardesline.github.io/pardesline/"
TOPICS = [
    "python",
    "computer-vision",
    "medical-imaging",
    "3d",
    "point-cloud",
    "datasets",
    "deep-learning",
    "huggingface",
    "segmentation",
    "registration",
    "3d-reconstruction",
    "mesh-processing",
    "dicom",
    "nifti",
    "ct",
    "mri",
    "open3d",
    "simpleitk",
    "mcp",
    "lidar",
]
LABELS = {
    "good first issue": ("7057ff", "scoped, templated, a maintainer will review within a week"),
    "help wanted": ("008672", "needs domain knowledge or hardware the maintainers lack"),
    "dataset": ("0e8a16", "a dataset manifest to add or fix"),
    "algorithm": ("1d76db", "a catalog method to add or fix"),
    "model": ("5319e7", "a model manifest or the model registry"),
    "roadmap": ("d93f0b", "a tracking issue people vote on"),
    "real-case": ("fbca04", "a reproducible run on production-like data"),
    "docs": ("0075ca", "documentation"),
    "bug": ("d73a4a", "something does not work as documented"),
    "enhancement": ("a2eeef", "new capability"),
    "mcp": ("bfd4f2", "the MCP server"),
}


def token() -> str:
    if not TOKEN_FILE.is_file():
        sys.exit(
            f"no token at {TOKEN_FILE}: write it with PowerShell Read-Host, see docs/seo/github-metadata.md"
        )
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def call(method: str, url: str, body: dict | None = None, tok: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode()
            return resp.status, (json.loads(text) if text else {})
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def check(tok: str) -> None:
    status, repo = call("GET", API, tok=tok)
    if status != 200:
        sys.exit(f"cannot read {REPO}: HTTP {status} {repo.get('message')}")
    perms = repo.get("permissions", {})
    print(
        f"{repo['full_name']}: admin={perms.get('admin')} push={perms.get('push')} discussions={repo.get('has_discussions')}"
    )
    if not perms.get("push"):
        sys.exit("the token cannot write to the repository")


def metadata(tok: str) -> None:
    status, body = call(
        "PATCH", API, {"description": DESCRIPTION, "homepage": HOMEPAGE, "has_discussions": True}, tok
    )
    print("metadata:", status, body.get("message", "ok"))
    status, body = call("PUT", f"{API}/topics", {"names": TOPICS}, tok)
    print("topics:", status, body.get("names", body.get("message")))


def labels(tok: str) -> None:
    status, existing = call("GET", f"{API}/labels?per_page=100", tok=tok)
    names = {lab["name"] for lab in existing} if status == 200 else set()
    for name, (colour, desc) in LABELS.items():
        if name in names:
            status, body = call(
                "PATCH",
                f"{API}/labels/{urllib.request.quote(name)}",
                {"color": colour, "description": desc},
                tok,
            )
        else:
            status, body = call(
                "POST", f"{API}/labels", {"name": name, "color": colour, "description": desc}, tok
            )
        print(f"label {name!r}: {status} {body.get('message', '')}")


def parse_issues() -> list[dict]:
    """Read docs/seo/issues-to-create.md: tracking issues (### headings) and numbered lists."""
    text = (HERE / "issues-to-create.md").read_text(encoding="utf-8")
    issues: list[dict] = []
    # tracking issues
    tracking = text.split("## Tracking issues (`roadmap`)", 1)[1].split("## Good first issues", 1)[0]
    for block in re.split(r"\n### ", tracking)[1:]:
        title, rest = block.split("\n", 1)
        labs = re.findall(r"`([a-z -]+)`", rest.split("\n", 1)[0])
        body = rest.split("\n", 1)[1].strip()
        issues.append({"title": title.strip(), "labels": labs, "body": body})
    for section, extra in (("## Good first issues", "good first issue"), ("## Help wanted", "help wanted")):
        part = text.split(section, 1)[1]
        part = part.split("\n## ", 1)[0]
        for m in re.finditer(
            r"^\d+\. \*\*(.+?)\*\* \(`([a-z-]+)`\)\. (.+?)(?=\n\d+\. \*\*|\Z)", part, re.S | re.M
        ):
            issues.append(
                {"title": m.group(1).strip(), "labels": [extra, m.group(2)], "body": m.group(3).strip()}
            )
    return issues


def create_issues(tok: str) -> None:
    status, existing = call("GET", f"{API}/issues?state=all&per_page=100", tok=tok)
    titles = {i["title"] for i in existing} if status == 200 else set()
    footer = (
        "\n\n---\nFrom `docs/seo/issues-to-create.md`. Templates: `templates/`. Guide: `CONTRIBUTING.md`."
    )
    for issue in parse_issues():
        if issue["title"] in titles:
            print(f"exists: {issue['title']}")
            continue
        status, body = call(
            "POST",
            f"{API}/issues",
            {"title": issue["title"], "body": issue["body"] + footer, "labels": issue["labels"]},
            tok,
        )
        print(f"{status} #{body.get('number', '?')} {issue['title']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--metadata", action="store_true")
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--issues", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true", help="print the parsed issues without sending anything")
    args = ap.parse_args()
    if args.list:
        for i in parse_issues():
            print(f"[{', '.join(i['labels'])}] {i['title']}")
        print(len(parse_issues()), "issues")
        return
    tok = token()
    check(tok)
    if args.metadata or args.all:
        metadata(tok)
    if args.labels or args.all:
        labels(tok)
    if args.issues or args.all:
        create_issues(tok)


if __name__ == "__main__":
    main()
