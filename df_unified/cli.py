"""DF_Unified CLI -- one door over DF_Small, DF_Medium, DF_Large, DF_Xtra_Large and DF_Fabric.

  status                      unified integrity gates U0-U5 (+ consolidated reports)
  verify [--deep] [--full]    U0-U5; --deep hashes every sealed byte; --full also runs U6 (node batteries) and U7 (fabric battery)
  build                       build all four nodes in place (delegates to DF_Fabric fabric-build)
  run [bundle.pal] [...]      run a bundle on the federation (DF_Fabric fabric-run); extra args pass through
  node <member> <verb> [...]  talk to one member directly: verb = build | verify | run | attest
  members                     print the registry and where each member was found
  console [--fullscreen]      open the unified console (Technical Institute + Unified System page)

Global: --root DIR (folder holding the five DF_* containers; default: beside DF_Unified; env DF_UNIFIED_ROOT)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from df_unified import core  # noqa: E402


def _print_gates(res):
    for g in res["unified_gates"]:
        print(f"  {g['id']:<3} {g['status']:<8} {g['name']}")
        if g["status"] == "FAIL":
            print("        " + json.dumps(g["detail"])[:1200])
    t = res["totals"]
    print(f"\n  verdict {res['verdict']}  ·  {t.get('PASS', 0)} pass, {t.get('FAIL', 0)} fail, {t.get('SKIPPED', 0)} skipped")


def cmd_verify(a, deep=None, full=None):
    base, ms, gates = core.battery(a.root, deep=a.deep if deep is None else deep, full=a.full if full is None else full)
    res = core.consolidated(ms, gates)
    rd = core.write_reports(res)
    print(f"DF_Unified {core.UNIFIED['unified_version']} · members under {base}")
    _print_gates(res)
    print(f"  reports -> {rd}")
    return 0 if res["verdict"] == "PASS" else 1


def cmd_status(a):
    return cmd_verify(a, deep=False, full=False)


def cmd_members(a):
    base, ms = core.locate(a.root)
    print(f"root: {base}")
    for m in ms:
        print(f"  {m['container']:<14} {m['id']:<9} {m['role']:<13} {'present' if m['present'] else 'ABSENT':<8} {m['embedded']}")
    return 0


def _fabric(a):
    base, ms = core.locate(a.root)
    return base, next(m for m in ms if m["container"] == "DF_Fabric")


def cmd_build(a):
    base, fab = _fabric(a)
    return core.delegate(fab, "fabric-build", a.rest, base=base)["returncode"]


def cmd_run(a):
    base, fab = _fabric(a)
    return core.delegate(fab, "fabric-run", a.rest, base=base)["returncode"]


def cmd_node(a):
    base, _ = core.locate(a.root)
    m = core.member(a.root, a.member)
    prefix = "fabric-" if m["role"] == "control_plane" else "node-"
    return core.delegate(m, prefix + a.verb, a.rest, base=base)["returncode"]


def cmd_console(a):
    app = os.path.join(core.HERE, "ui", "app")
    if not os.path.exists(os.path.join(app, "assets", "unified_status.js")):
        core.write_reports(core.consolidated(*core.battery(a.root)[1:]))
    if os.name == "nt":
        ps = os.path.join(app, "Launch-DF-VM-Technical-Institute.ps1")
        argv = ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps, "-Start", "unified.html"]
        if a.fullscreen: argv.append("-Fullscreen")
        return subprocess.call(argv)
    import webbrowser
    webbrowser.open(core.Path(app, "unified.html").as_uri())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="df_unified", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="folder holding the five DF_* containers")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("status").set_defaults(fn=cmd_status)
    p = sp.add_parser("verify"); p.add_argument("--deep", action="store_true"); p.add_argument("--full", action="store_true"); p.set_defaults(fn=cmd_verify)
    sp.add_parser("members").set_defaults(fn=cmd_members)
    p = sp.add_parser("build"); p.add_argument("rest", nargs=argparse.REMAINDER); p.set_defaults(fn=cmd_build)
    p = sp.add_parser("run"); p.add_argument("rest", nargs=argparse.REMAINDER); p.set_defaults(fn=cmd_run)
    p = sp.add_parser("node"); p.add_argument("member"); p.add_argument("verb", choices=["build", "verify", "run", "attest"])
    p.add_argument("rest", nargs=argparse.REMAINDER); p.set_defaults(fn=cmd_node)
    p = sp.add_parser("console"); p.add_argument("--fullscreen", action="store_true"); p.set_defaults(fn=cmd_console)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f'DF_Unified refused: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
