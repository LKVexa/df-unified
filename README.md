# DF Unified

Version **1.0.1** · Copyright 2026 **RUSSELL PHILIP SMITHSON** · Apache-2.0

DF Unified checks five independently sealed DF containers and delegates their native commands only after all integrity and capability gates pass. It includes a static Technical Institute console (2.1.3). Python 3.10 or newer is required; the orchestrator has no third-party Python dependencies.

## Run

Place the five members under a common directory using their registry names: `DF_Small`, `DF_Medium`, `DF_Large`, `DF_Xtra_Large`, and `DF_Fabric`. Then run:

```text
python -B df_unified/cli.py --root /path/to/members members
python -B df_unified/cli.py --root /path/to/members status
python -B df_unified/cli.py --root /path/to/members verify --full
```

On Windows the `.cmd` launchers are available; set `DF_UNIFIED_ROOT` to the directory containing the members. On Unix use `sh STATUS` or `sh VERIFY --full`. Both status and verify hash every sealed file. `--deep` remains accepted for compatibility. Full verification additionally requires each member's native toolchains. Delegated build/run commands may create outputs inside those member directories.

The registry retains the original member pins and shared-code equality contract. **This release has not qualified a new five-member assembly.** Independently upgraded sibling repositories have different seals and may have different adapters; copying them beside this repository does not establish a compatible assembly. Missing, changed or incompletely bound members fail the gates and cannot be executed through the orchestrator. A future coordinated integration needs a reviewed registry and compatibility qualification; automatic repinning is deliberately absent.

## Console and Windows packaging

Open `ui/app/index.html` in a browser, or use `CONSOLE.cmd` for the unified status page. Bundled member measurements in `ui/evidence_digest/` and `assets/data.js` are historical reference data. The unified status starts empty. `status` writes a local snapshot into `reports/` and `ui/app/assets/unified_status.js`; it is a recorded result, not a live monitor. These generated files are local state and change the pristine source inventory.

`ui/Build-Single-EXE.ps1` builds an unsigned .NET Framework launcher using Windows PowerShell 5.1. It validates the embedded payload and every cached file before launch. Archive links, traversal, Windows aliases, duplicate names and excessive sizes are refused. Legacy IExpress packaging is disabled because it lacked equivalent validation; its compatibility entry points return an error. No compiled executable is shipped in this source release.

## Verification and boundaries

```text
python -B tools/validate_release.py
```

CI runs the source checks and synthetic five-member regression fixtures on Linux and Windows with Python 3.10 and 3.14. Windows also compiles and tests the C# extraction and cache helpers without launching the GUI. Fixtures validate rejection behavior; they are not evidence that a real federation passed U6/U7. An integrity-only result leaves U6/U7 SKIPPED. Physical QPU execution remains blocked; required fabric policy is `network=deny`, `backend=none`.

See [AUDIT.md](AUDIT.md), [CHANGELOG.md](CHANGELOG.md), [LICENSE](LICENSE), and [NOTICE](NOTICE). Release source ZIPs have SHA-256 checksums; `FILES.sha256` binds the pristine source files. Checksums detect changes, but are not a digital signature. Do not treat a modified registry or same-user filesystem races as a protected trust boundary.
