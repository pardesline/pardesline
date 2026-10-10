"""`pardesline` command-line interface — thin wrapper over the client.

    pardesline login
    pardesline whoami
    pardesline upload scan.ply
    pardesline send scan.ply bob@lab.org
    pardesline inbox
    pardesline ls
    pardesline download "alice@lab.org/scan.ply" out.ply
    pardesline share <file_id> bob@lab.org
    pardesline logout
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .client import Client
from .errors import PardesLineError


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n/1:.0f}{unit}" if False else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pardesline", description="Transfer files between PardesLine accounts.")
    p.add_argument("--version", action="version", version=f"pardesline {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login", help="Sign in (email + code) and store a key")
    sub.add_parser("logout", help="Revoke and forget the stored key")
    sub.add_parser("whoami", help="Show the logged-in account")
    up = sub.add_parser("upload", help="Upload a file or folder"); up.add_argument("path")
    se = sub.add_parser("send", help="Upload and share with an email"); se.add_argument("path"); se.add_argument("to")
    sub.add_parser("inbox", help="Files shared with you")
    lsp = sub.add_parser("ls", help="Your files"); lsp.add_argument("--scope", default="mine", choices=["mine", "shared", "all"])
    dl = sub.add_parser("download", help="Download by id or owner@email/name")
    dl.add_argument("ref"); dl.add_argument("out", nargs="?"); dl.add_argument("--extract", action="store_true")
    sh = sub.add_parser("share", help="Share one of your files"); sh.add_argument("file_id"); sh.add_argument("to")

    args = p.parse_args(argv)
    client = Client()
    try:
        if args.cmd == "login":
            client.login(); return 0
        if args.cmd == "logout":
            client.logout(); print("Logged out."); return 0
        if args.cmd == "whoami":
            print(client.whoami() or "(not logged in)"); return 0
        if args.cmd == "upload":
            print(client.upload(args.path)); return 0
        if args.cmd == "send":
            obj = client.send(args.path, to=args.to); print(f"Sent {obj.name} to {args.to} (id {obj.id})"); return 0
        if args.cmd == "inbox":
            for o in client.inbox():
                print(f"{o.id}  {o.name:<32} {_fmt_size(o.size_bytes):>9}  from {o.shared_by}")
            return 0
        if args.cmd == "ls":
            for o in client.list(args.scope):
                print(f"{o.id}  {o.name:<32} {_fmt_size(o.size_bytes):>9}")
            return 0
        if args.cmd == "download":
            dest = client.download(args.ref, args.out, extract=args.extract); print(f"Saved {dest}"); return 0
        if args.cmd == "share":
            s = client.share(args.file_id, to=args.to); print(f"Shared with {args.to} ({s.status})"); return 0
    except PardesLineError as e:
        print(f"error: {e.message}" + (f"  [{e.code}]" if e.code else ""), file=sys.stderr)
        if getattr(e, "upgrade_url", None):
            print(f"  upgrade: {e.upgrade_url}", file=sys.stderr)
        return 1
    except (FileNotFoundError, KeyboardInterrupt) as e:
        print(f"error: {e}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
