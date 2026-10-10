"""``pardesline`` command line.

    pardesline list [--ext .ply] [--category registration]
    pardesline describe point_cloud_reconstruction[.poisson]
    pardesline run point_cloud_processing.voxel_downsample scan.ply -o small.ply --voxel_size 0.02
    pardesline run simpleitk_registration.rigid ct.mha --moving mr.mha -o registered.vti
    pardesline version

Cloud commands (login, upload, send, inbox, ls, download, share, whoami,
logout) are forwarded to the cloud client.
"""

from __future__ import annotations

import argparse
import sys

from ._version import __version__
from .catalog import load_catalog
from .errors import PardesLineError

CLOUD_COMMANDS = ("login", "logout", "whoami", "upload", "send", "inbox", "ls", "download", "share")


def _parse_params(tokens: list[str]) -> dict[str, str]:
    """``--name value`` pairs (also ``--name=value``) into a dict."""
    params: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if not tok.startswith("--"):
            raise SystemExit(f"error: unexpected argument {tok!r}; parameters are --name value")
        key = tok[2:]
        if "=" in key:
            key, value = key.split("=", 1)
        else:
            if i + 1 >= len(tokens) or tokens[i + 1].startswith("--"):
                raise SystemExit(f"error: --{key} needs a value (booleans are --{key} true/false)")
            value = tokens[i + 1]
            i += 1
        params[key] = value
        i += 1
    return params


def _cmd_list(args: argparse.Namespace) -> int:
    cat = load_catalog()
    for mod in cat:
        if args.category and mod.category != args.category:
            continue
        if args.ext and not mod.accepts(args.ext if args.ext.startswith(".") else "." + args.ext):
            continue
        print(f"{mod.id}  [{mod.category}]  {', '.join(mod.input_formats)}")
        for m in mod.methods.values():
            flag = "  (two inputs)" if m.dual_input else ""
            print(f"    {m.id:<34} {m.name}{flag}")
    return 0


def _cmd_describe(args: argparse.Namespace) -> int:
    print(load_catalog().describe(args.what))
    return 0


def _cmd_run(args: argparse.Namespace, extra: list[str]) -> int:
    from .runner import run

    params = _parse_params(extra)
    res = run(
        args.method,
        None,
        args.input,
        args.output,
        moving=args.moving,
        params=params,
        timeout=args.timeout,
        on_log=(lambda line: print(line, file=sys.stderr)) if not args.quiet else (lambda _line: None),
    )
    print(res.output)
    if res.sidecar:
        print(res.sidecar)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in CLOUD_COMMANDS:
        from .cloud.cli import main as cloud_main

        return cloud_main(argv)

    p = argparse.ArgumentParser(
        prog="pardesline",
        description="Run 3D vision and medical imaging algorithms locally.",
        epilog="Cloud commands: " + ", ".join(CLOUD_COMMANDS) + ".",
    )
    p.add_argument("--version", action="version", version=f"pardesline {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    lp = sub.add_parser("list", help="List modules and methods")
    lp.add_argument("--ext", help="Only modules accepting this extension (e.g. .ply)")
    lp.add_argument("--category", help="Only this category")

    dp = sub.add_parser("describe", help="Show a module or a method with its parameters")
    dp.add_argument("what", help="module or module.method")

    rp = sub.add_parser(
        "run",
        help="Run one method on a file; parameters as --name value after the file",
        usage="pardesline run MODULE.METHOD INPUT [-o OUTPUT] [--moving FILE] [--name value ...]",
    )
    rp.add_argument("method", help="module.method")
    rp.add_argument("input", help="Input file (the fixed reference for registration)")
    rp.add_argument("-o", "--output", help="Output path (default: the pardesline output folder)")
    rp.add_argument("--moving", help="Second input for registration methods")
    rp.add_argument("--timeout", type=float, default=600, help="Seconds before the run is killed")
    rp.add_argument("-q", "--quiet", action="store_true", help="Do not echo the algorithm log")

    sub.add_parser("version", help="Print the version")

    args, extra = p.parse_known_args(argv)
    try:
        if args.cmd == "list":
            return _cmd_list(args)
        if args.cmd == "describe":
            return _cmd_describe(args)
        if args.cmd == "run":
            return _cmd_run(args, extra)
        if args.cmd == "version":
            print(__version__)
            return 0
    except PardesLineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    if extra:
        raise SystemExit(f"error: unrecognised arguments: {' '.join(extra)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
