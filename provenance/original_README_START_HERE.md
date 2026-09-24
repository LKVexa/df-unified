# DF_Unified -- START HERE

**DFU0 · v1.0.0 · DF-PA21.2-1.0.0.** The five DF containers run as one system through one entry point.

```
New folder\
  DF_Small\  DF_Medium\  DF_Large\  DF_Xtra_Large\   execution plane  (N_SMALL, N_MEDIUM, N_LARGE, N_XLARGE)
  DF_Fabric\                                         control plane    (DF0 federation: replica / pipeline / BSP)
  DF_Unified\                                        this folder: registry, integrity, orchestration, console
```

## Why this design

The Technical Institute (`ui/`) and the members' own records agree on three points:

1. **The members are sealed.** Each has its own `SHA256SUMS.txt`/`MANIFEST.json`. `DF_Fabric/fabric/NODES.json` pins those seals, and gate F0 fails if they change.
2. **Images are not portable between nodes.** This was measured (gate F7). The fabric moves sealed rows and lowers them on each node. Pooling the VM payloads into one tree would add nothing and would break every seal.
3. **`adapter/dfabric` and `core/` are the same bytes in all five members.**

So DF_Unified combines the members **by binding them, not by copying them**. Nothing inside a member is rewritten. DF_Unified:

* finds all five members beside itself;
* proves they are the pinned bytes;
* proves the shared code really is shared;
* declares everything that was added to a member after sealing, so accounted-for drift can be told apart from tampering;
* runs every battery from one place;
* gathers every ledger, gate record and blocker into one report and one console.

## Use it (Windows: double-click the `.cmd`; elsewhere run `./NAME`)

| Launcher | What it does |
|---|---|
| `STATUS.cmd` | Runs the fast unified gates U0–U5 in seconds with no toolchain, then writes `reports/` and the console status |
| `VERIFY.cmd --deep` | Same, but hashes every sealed byte of every member |
| `VERIFY.cmd --full` | Also runs U6 (each node's own `VERIFY`) and U7 (the DF_Fabric F0–F9 battery with `--nodes-root` set to this folder's parent) |
| `BUILD.cmd` | Builds all four nodes in place (delegates to `DF_Fabric fabric-build`) |
| `RUN.cmd [bundle.pal] [--profile …]` | Runs a bundle on the federation (delegates to `DF_Fabric fabric-run`; default `fabric/FABRIC.pal`) |
| `MEMBERS.cmd` | Lists the registry and where each member was found |
| `CONSOLE.cmd` | Opens the console on the new **Unified System 08** page. The Institute pages 00–07 are unchanged |

To reach one member directly: `python df_unified\cli.py node <small|medium|large|xtra_large|fabric> <build|verify|run|attest> [args]`.
If the members live somewhere else, use `--root <folder>` or set `DF_UNIFIED_ROOT`.

## Unified gates

| Gate | Statement |
|---|---|
| `U0` | All five members are present, with MANIFEST, SUMS, the adapter CLI, VERIFY and RUN |
| `U1` | Each member's `SHA256SUMS.txt` and `MANIFEST.json` match the unified pins, and the four nodes also match DF_Fabric's live `NODES.json` pins (checked at assembly: **all match**) |
| `U2` | `adapter/dfabric/` and `core/` produce one tree digest across all five members |
| `U3` | Each sealed inventory is intact. Missing or changed files FAIL. Extra files pass only when declared as overlays |
| `U4` | Every declared overlay is present and classified. The nested `DF_Medium\DF_Medium` copy is compared with its parent's seal |
| `U5` | Claim boundary: every ledger keeps `PHYSICAL_*_QPU_EXECUTION` BLOCKED, and the fabric keeps `NETWORK=deny` |
| `U6` | Each node's own VERIFY battery (member-native; needs C11 + make + OpenSSL, and Java for XL column compiles) |
| `U7` | The DF_Fabric battery F0–F9 over the bound nodes |

## Overlays found outside the seals (declared in `UNIFIED.json`)

* `DF_Fabric\PHOTON\` plus the `PHOTON.cmd`/`.sh` launchers: the VEC1 Photon, `VENDORED_UNBOUND`, integrated 2026-09-22.
* `DF_Fabric\pk\`: Post-Kubernetes batches 1–6 (6 owned components and 89 dependencies).
* `DF_Medium\DF_Medium\`: a duplicate copy of the container nested inside itself. No launcher uses it. Consider removing it yourself once U4 shows `identical_seal_to_parent: true`.

Because of these additions, DF_Fabric's own `G0.2` ("no extras") will report the PHOTON/pk files when it runs. U3 is where they are accounted for. They are not hidden.

## What is not claimed

Every member's blockers carry over word for word (`reports/UNIFIED_BLOCKED_REGISTER.md` after the first `STATUS`). The system runs on one host with local processes, and `distributed_state` is capped at `DISTRIBUTED_CLASSICAL_EMULATION`. No node has a qubit. Combining the containers promotes nothing.

> No item is operational because its source file exists. Operational status requires native executable evidence satisfying that item's promotion gate.

## Layout

```
README_START_HERE.md  UNIFIED.json  LICENSE  THIRD-PARTY-NOTICES.md
STATUS  VERIFY  BUILD  RUN  MEMBERS  CONSOLE  (+ .cmd)
df_unified/   __init__.py  core.py (registry, U0–U7, delegation, reports)  cli.py
ui/           DF VM Technical Institute v2.1.2 + app/unified.html, app/assets/unified.js
reports/      UNIFIED_GATE_RESULTS.json/.md, UNIFIED_BLOCKED_REGISTER.md   (written by STATUS/VERIFY)
```
