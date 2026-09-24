"""DF_Unified core: member registry, unified gates U0-U7, delegation, consolidated reports.

Stdlib only. Offline. Never writes into a member container.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import platform
import re
import tempfile
from pathlib import Path
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone

from . import integrity as I

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # DF_Unified/
UNIFIED = json.loads(Path(HERE, "UNIFIED.json").read_text(encoding="utf-8"), object_pairs_hook=I._unique_object)
CACHE_DIRS = {".git", "__pycache__", ".build", "_runs", "_scratch"}
PHYSICAL_OUTPUTS = ("PHYSICAL_PARALLEL_QPU_EXECUTION", "PHYSICAL_DISTRIBUTED_QPU_EXECUTION")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- registry
def members_root(root: str | None) -> str:
    return os.path.abspath(root or os.environ.get("DF_UNIFIED_ROOT") or os.path.join(HERE, ".."))


EXPECTED_MEMBERS = {'DF_Small': 'N_SMALL', 'DF_Medium': 'N_MEDIUM',
                    'DF_Large': 'N_LARGE', 'DF_Xtra_Large': 'N_XLARGE', 'DF_Fabric': 'DF0'}


def _json(root, rel):
    path = I._safe_file(root, rel)
    if os.path.getsize(path) > 20 * 1024 * 1024:
        raise ValueError('JSON evidence exceeds size limit')
    with open(path, encoding='utf-8') as stream:
        return json.load(stream, object_pairs_hook=I._unique_object)


def locate(root: str | None):
    base = members_root(root)
    records = UNIFIED['members']
    if (len(records) != 5 or len({m['container'] for m in records}) != 5
            or {m['container']: m['id'] for m in records} != EXPECTED_MEMBERS):
        raise ValueError('registry must identify exactly the five expected members')
    out = []
    for m in records:
        p = os.path.join(base, m['container'])
        I._safe_file(base, m['container'] + '/.integrity-probe')
        out.append(dict(m, path=p, present=os.path.isdir(p)))
    return base, out


def _complete(ms):
    if len(ms) != 5 or {m['container'] for m in ms} != set(EXPECTED_MEMBERS):
        raise ValueError('all five members are required')
    if any(not m['present'] for m in ms):
        raise ValueError('one or more members are absent')


def member(root, name):
    _, ms = locate(root)
    for m in ms:
        if name.lower() in (m["container"].lower(), m["id"].lower(), m["container"][3:].lower()):
            return m
    raise SystemExit(f"unknown member {name!r}; use one of: " + ", ".join(x["container"] for x in ms))


def overlays_for(container):
    return [o for o in UNIFIED["overlays"] if o["container"] == container]


# ---------------------------------------------------------------- gates
class Gate:
    def __init__(self, gid, name):
        self.id, self.name, self.status, self.detail, self.t0 = gid, name, "PASS", {}, time.time()

    def fail(self, **kw):
        self.status = "FAIL"; self.detail.update(kw)

    def skip(self, reason):
        self.status = "SKIPPED"; self.detail["reason"] = reason

    def done(self):
        return {"id": self.id, "name": self.name, "status": self.status,
                "seconds": round(time.time() - self.t0, 3), "detail": self.detail}


def g_u0(ms):
    g = Gate('U0', 'all five members present with regular, contained entry points')
    _complete(ms)
    for m in ms:
        for name in ('MANIFEST.json', 'SHA256SUMS.txt', 'adapter/dfabric/cli.py', 'VERIFY', 'RUN'):
            if not os.path.isfile(I._safe_file(m['path'], name)):
                raise ValueError(m['container'] + ': missing ' + name)
        g.detail[m['container']] = 'present'
    return g.done()


def g_u1(ms):
    g = Gate('U1', 'member seals match unified pins and every live fabric node pin')
    _complete(ms)
    fab = next(m for m in ms if m['container'] == 'DF_Fabric')
    records = _json(fab['path'], 'fabric/NODES.json')['nodes']
    live = {n['container']: n for n in records}
    if len(records) != 4 or set(live) != set(EXPECTED_MEMBERS) - {'DF_Fabric'}:
        raise ValueError('fabric registry must identify exactly four unique nodes')
    for m in ms:
        pins = m['pins']
        for key in ('sums_sha256', 'manifest_sha256'):
            if not isinstance(pins.get(key), str) or not re.fullmatch('[0-9a-f]{64}', pins[key]):
                raise ValueError('invalid registry digest')
        sums = sha256_file(I._safe_file(m['path'], 'SHA256SUMS.txt'))
        manifest = sha256_file(I._safe_file(m['path'], 'MANIFEST.json'))
        rec = {'sums_ok': sums == pins['sums_sha256'], 'manifest_ok': manifest == pins['manifest_sha256']}
        if m['container'] != 'DF_Fabric':
            rec['fabric_pin_ok'] = sums == live[m['container']]['sums_sha256']
        if not all(rec.values()):
            g.status = 'FAIL'
        g.detail[m['container']] = rec
    return g.done()


def tree_digest(root, rel):
    I._safe_file(root, rel + '/.integrity-probe')
    base = os.path.join(root, rel)
    h = hashlib.sha256()
    count = 0
    for name, path in I._tree(base, lambda x: any(p in CACHE_DIRS or p.endswith('.pyc') for p in x.split('/'))):
        h.update(name.encode() + b'\0' + sha256_file(path).encode() + b'\n')
        count += 1
    if not count:
        raise ValueError('shared artifact tree is empty')
    return h.hexdigest(), count


def g_u2(ms):
    g = Gate('U2', 'nonempty shared adapter and core trees match across all five members')
    _complete(ms)
    for rel in ('adapter/dfabric', 'core'):
        digests = {m['container']: tree_digest(m['path'], rel) for m in ms}
        unique = {d for d, _ in digests.values()}
        g.detail[rel] = {'identical': len(unique) == 1, 'per_member': digests}
        if len(unique) != 1:
            g.status = 'FAIL'
    return g.done()


def _excluded(rel, patterns):
    parts = rel.split("/")
    return any(fnmatch.fnmatch(p, pat) for p in parts for pat in patterns)


def inventory(m, deep=False):
    # Always hash sealed files, including fast status. Size alone cannot prove integrity.
    man = _json(m['path'], 'MANIFEST.json')
    files = I._records(man)
    allowed = set(I.INVENTORY_EXCLUSIONS) | {'FILES.sha256'}
    exclusions = man.get('inventory_exclusions', [])
    if not isinstance(exclusions, list) or any(x not in allowed for x in exclusions):
        raise ValueError('unrecognized inventory exclusions')
    disk = dict(I._tree(m['path'], I.is_excluded))
    omit = {'MANIFEST.json', 'SHA256SUMS.txt', 'FILES.sha256'}
    for name in omit:
        disk.pop(name, None)
    for rel in files:
        I._safe_file(m['path'], rel)
        if rel in omit:
            raise ValueError('recursive inventory entry')
    missing = sorted(set(files) - set(disk))
    extra = sorted(set(disk) - set(files))
    changed = [rel for rel, item in files.items() if rel in disk and
               (os.path.getsize(disk[rel]) != item['bytes'] or sha256_file(disk[rel]) != item['sha256'])]
    bound = set()
    with open(I._safe_file(m['path'], 'SHA256SUMS.txt'), encoding='utf-8') as stream:
        for line in stream:
            line = line.rstrip('\r\n')
            if not line:
                continue
            match = re.fullmatch(r'([0-9a-f]{64}) [ *](.+)', line)
            if not match or match.group(2) in bound:
                raise ValueError('malformed or duplicate checksum record')
            digest, name = match.groups()
            path = I._safe_file(m['path'], name)
            bound.add(name)
            if not os.path.isfile(path) or sha256_file(path) != digest:
                changed.append(name)
    if not set(files).issubset(bound) or 'MANIFEST.json' not in bound:
        raise ValueError('checksum inventory does not bind every sealed file and manifest')
    return missing, extra, sorted(set(changed))


def _overlay_matches(name, prefix):
    if not isinstance(prefix, str) or not prefix:
        raise ValueError('invalid overlay prefix')
    return name.startswith(prefix) if prefix.endswith('/') else name == prefix


def g_u3(ms, deep):
    g = Gate("U3", "sealed inventory intact in every member (missing/changed = FAIL; extras must be declared overlays)"
             + " [every sealed byte hashed]")
    _complete(ms)
    for m in ms:
        missing, extra, changed = inventory(m, deep)
        ov = overlays_for(m["container"])
        undeclared = [e for e in extra if not any(_overlay_matches(e, o["prefix"]) for o in ov)]
        rec = {"missing": missing[:20], "changed": changed[:20], "extra_declared": len(extra) - len(undeclared),
               "extra_undeclared": undeclared[:20], "missing_n": len(missing), "changed_n": len(changed),
               "undeclared_n": len(undeclared)}
        if missing or changed or undeclared:
            g.status = "FAIL"
        g.detail[m["container"]] = rec
    return g.done()


def g_u4(ms):
    g = Gate("U4", "every declared overlay is present and classified; nested duplicates compared with their parent seal")
    _complete(ms)
    by = {m["container"]: m for m in ms}
    for o in UNIFIED["overlays"]:
        m = by[o["container"]]
        prefix = o["prefix"].rstrip("/")
        I._safe_file(m["path"], prefix + "/.integrity-probe" if o["prefix"].endswith("/") else prefix)
        p = os.path.join(m["path"], prefix)
        rec = {"present": os.path.exists(p), "status": o["status"], "kind": o["kind"]}
        if not rec["present"] or not o.get("status") or not o.get("kind"):
            g.status = "FAIL"
        if rec["present"] and os.path.isdir(p):
            rec["files"] = sum(1 for _ in I._tree(p, lambda _: False))
        if o["kind"] == "nested_duplicate" and rec["present"]:
            ns = os.path.join(p, "SHA256SUMS.txt")
            rec["identical_seal_to_parent"] = os.path.exists(ns) and sha256_file(ns) == sha256_file(
                os.path.join(m["path"], "SHA256SUMS.txt"))
        g.detail[o["container"] + "/" + o["prefix"]] = rec
    return g.done()


def ledgers(ms):
    out = {}
    for m in ms:
        if m['present']:
            ledger = _json(m['path'], 'reports/DF_CAPABILITY_LEDGER.json')
            if (not isinstance(ledger, dict) or not isinstance(ledger.get('items'), list) or not ledger['items']
                    or any(not isinstance(item, dict) or not isinstance(item.get('status'), str)
                           for item in ledger['items'])):
                raise ValueError(m['container'] + ': missing capability evidence')
            out[m['container']] = ledger
    return out


def g_u5(ms):
    g = Gate('U5', 'every physical-output claim remains blocked; network=deny and backend=none')
    _complete(ms)
    bad = []
    for container, ledger in ledgers(ms).items():
        for token in PHYSICAL_OUTPUTS:
            named = [item for item in ledger['items'] if token in
                     (str(item.get('statement', '')) + str(item.get('title', ''))).upper()]
            if not named or any(item.get('status') not in
                    {'BLOCKED', 'BLOCKED_EXTERNAL_AUTHORITY', 'BLOCKED_CAPABILITY_ABSENT'} for item in named):
                bad.append(container + ':' + token)
    fab = next(m for m in ms if m['container'] == 'DF_Fabric')
    federation = _json(fab['path'], 'fabric/FEDERATION.json')
    if federation.get('network_policy') != 'deny' or federation.get('backend_policy') != 'none':
        bad.append('fabric execution policy')
    g.detail['violations'] = bad
    if bad:
        g.status = 'FAIL'
    return g.done()


# ---------------------------------------------------------------- delegation
def py():
    return sys.executable


def delegate(m, cmd, args=(), base=None, capture=False, timeout=1800, verified=False):
    if not verified:
        _, _, gates = battery(base, deep=True, full=False)
        if any(g['status'] != 'PASS' for g in gates if g['id'] in {'U0','U1','U2','U3','U4','U5'}):
            raise ValueError('member execution refused: unified integrity gates failed')
    if cmd not in {p + v for p in ('node-', 'fabric-') for v in ('build', 'run', 'verify', 'attest')}:
        raise ValueError('unsupported delegated command')
    cli = I._safe_file(m['path'], 'adapter/dfabric/cli.py')
    argv = [py(), '-B', cli, cmd]
    if m['role'] == 'control_plane' and base:
        argv += ['--nodes-root', base]
    argv += list(args)
    start = time.monotonic()
    result = subprocess.run(argv, cwd=m['path'], capture_output=capture, text=True,
                            encoding='utf-8', errors='replace', timeout=timeout)
    record = {'returncode': result.returncode, 'seconds': round(time.monotonic() - start, 2)}
    if capture:
        record['tail'] = (result.stdout + result.stderr)[-3000:]
    return record


def g_u6(ms, base):
    g = Gate("U6", "each node container's own ./VERIFY battery passes on this host (delegated, member-native)")
    _complete(ms)
    for m in ms:
        if m["role"] != "node" or not m["present"]:
            continue
        r = delegate(m, "node-verify", base=base, capture=True, verified=True)
        g.detail[m["container"]] = r
        if r["returncode"] != 0: g.status = "FAIL"
    return g.done()


def g_u7(ms, base):
    g = Gate("U7", "DF_Fabric battery (F0-F9) passes over the four bound nodes (delegated, --nodes-root = unified root)")
    fab = next(m for m in ms if m["container"] == "DF_Fabric")
    _complete(ms)
    r = delegate(fab, "fabric-verify", base=base, capture=True, verified=True)
    g.detail["DF_Fabric"] = r
    if r["returncode"] != 0: g.status = "FAIL"
    return g.done()


# ---------------------------------------------------------------- battery + reports
def _gate_call(gid, function, *args):
    try:
        return function(*args)
    except Exception as exc:  # Record malformed evidence and native failures; never promote them.
        return {'id': gid, 'name': function.__name__, 'status': 'FAIL', 'seconds': 0,
                'detail': {'error': type(exc).__name__, 'reason': str(exc)}}


def battery(root=None, deep=False, full=False):
    base, ms = locate(root)
    gates = [_gate_call('U0', g_u0, ms), _gate_call('U1', g_u1, ms),
             _gate_call('U2', g_u2, ms), _gate_call('U3', g_u3, ms, deep),
             _gate_call('U4', g_u4, ms), _gate_call('U5', g_u5, ms)]
    ready = all(g['status'] == 'PASS' for g in gates)
    if full and ready:
        gates += [_gate_call('U6', g_u6, ms, base), _gate_call('U7', g_u7, ms, base)]
    else:
        reason = 'integrity prerequisites failed' if not ready else 'run with --full and native toolchains'
        for gid, name in (('U6', 'member-native batteries'), ('U7', 'fabric battery')):
            gates.append({'id': gid, 'name': name, 'status': 'SKIPPED', 'seconds': 0,
                          'detail': {'reason': reason}})
    return base, ms, gates


def host():
    return {"platform": platform.platform(), "python": platform.python_version(), "network_policy": "deny"}


def consolidated(ms, gates):
    try:
        L = ledgers(ms)
    except (OSError, ValueError, TypeError, KeyError):
        L = {}  # Gate U5 records the failure; incomplete evidence cannot promote claims.
    dist = Counter(); items = []
    for c, led in L.items():
        for it in led.get("items", []):
            dist[it.get("status")] += 1
            items.append({"member": c, "id": it.get("id"), "title": it.get("title"), "status": it.get("status"),
                          "statement": it.get("statement")})
    member_gates = {}
    for m in ms:
        p = os.path.join(m["path"], "conformance", "DF_GATE_RESULTS.json")
        if m["present"] and os.path.exists(p):
            try:
                G = _json(m['path'], 'conformance/DF_GATE_RESULTS.json')
                if not isinstance(G, dict) or not isinstance(G.get('totals', {}), dict) or not isinstance(G.get('gates'), list) or any(not isinstance(g, dict) or not {'id', 'status', 'name'}.issubset(g) for g in G['gates']):
                    raise ValueError('invalid historical gate record')
            except (OSError, ValueError, TypeError, KeyError):
                continue
            member_gates[m["container"]] = {"totals": G.get("totals"), "verdict": G.get("verdict"),
                                            "executed_at_utc": G.get("executed_at_utc"),
                                            "gates": [{"id": x["id"], "status": x["status"], "name": x["name"]} for x in G["gates"]]}
    t = Counter(g["status"] for g in gates)
    complete = (len(gates) == 8 and {g['id'] for g in gates} == {f'U{i}' for i in range(8)}
                and all(g['status'] == 'PASS' for g in gates if g['id'] in {f'U{i}' for i in range(6)})
                and all(g['status'] in {'PASS', 'FAIL', 'SKIPPED'} for g in gates))
    verdict = 'PASS' if complete and not t['FAIL'] else 'FAIL' 
    return {"schema": "DF/UNIFIED_RESULTS/1", "system_id": UNIFIED["system_id"], "unified_version": UNIFIED["unified_version"],
            "df_release": UNIFIED["df_release"], "executed_at_utc": now(), "host": host(), "rule": UNIFIED["rule"],
            "verdict": verdict, "totals": dict(t), "unified_gates": gates, "member_recorded_gates": member_gates,
            "capability_distribution": dict(dist), "capability_items": items,
            "members": [{k: m[k] for k in ("container", "role", "id", "embedded", "dialect", "domain", "summary", "present")} for m in ms],
            "overlays": UNIFIED["overlays"], "claim_boundary": UNIFIED["claim_boundary"]}


def blocked_md(res):
    lines = ["# DF_Unified -- consolidated blocked / not-operational register", "",
             f"Generated {res['executed_at_utc']} by `STATUS`/`VERIFY`. Every entry is inherited verbatim from a member ledger; DF_Unified lifts none.", ""]
    for it in res["capability_items"]:
        if it["status"] not in ("OPERATIONAL", "VERIFIED", "QUALIFIED"):
            lines.append(f"* **{it['member']}** `{it['id']}` {it['title']} -- `{it['status']}`: {it['statement']}")
    lines += ["", "## Overlays outside the seals", ""]
    for o in res["overlays"]:
        lines.append(f"* `{o['container']}/{o['prefix']}` -- `{o['status']}`: {o['note']}")
    return "\n".join(lines) + "\n"


def results_md(res):
    L = [f"# DF_Unified gate results -- verdict **{res['verdict']}**", "",
         f"{res['executed_at_utc']} · {res['host']['platform']} · Python {res['host']['python']}", "",
         "| gate | statement | result | s |", "|---|---|---|---|"]
    for g in res["unified_gates"]:
        L.append(f"| `{g['id']}` | {g['name']} | **{g['status']}** | {g['seconds']} |")
    L += ["", "## Member-recorded batteries (as shipped)", "", "| member | passed | skipped | failed | verdict |", "|---|---|---|---|---|"]
    for c, v in res["member_recorded_gates"].items():
        t = v["totals"] or {}
        L.append(f"| {c} | {t.get('passed')} | {t.get('skipped')} | {t.get('failed')} | {v.get('verdict') or 'UNVERIFIED'} |")
    L += ["", "## Capability distribution across the system", ""]
    for k, v in sorted(res["capability_distribution"].items(), key=lambda x: -x[1]):
        L.append(f"* `{k}`: {v}")
    return "\n".join(L) + "\n"


def _atomic_text(rel, text):
    path = Path(I._safe_file(HERE, rel))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='\n',
                                         dir=path.parent, prefix='.df-report-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_reports(res):
    _atomic_text('reports/UNIFIED_GATE_RESULTS.json', json.dumps(res, indent=1) + '\n')
    _atomic_text('reports/UNIFIED_GATE_RESULTS.md', results_md(res))
    _atomic_text('reports/UNIFIED_BLOCKED_REGISTER.md', blocked_md(res))
    # The console displays a generated local snapshot, not bundled workstation state.
    _atomic_text('ui/app/assets/unified_status.js', 'window.DF_UNIFIED_STATUS = ' + json.dumps(res) + ';\n')
    return os.path.join(HERE, 'reports')
