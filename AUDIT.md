# Audit — 1.0.1

## Fixed

- Partial installations, missing registries, empty shared-code trees and incomplete gate sets could produce misleading success. All five members and required evidence now participate in every integrity decision.
- Fast status previously compared sizes without hashing sealed bytes. Every sealed file is now hashed; duplicate JSON/checksum records, unsafe paths, malformed sizes and unsupported exclusion patterns fail closed.
- File overlays previously authorized similarly prefixed names. Exact file names and explicit directory prefixes now have separate matching rules.
- Missing capability records and malformed historical data could be silently omitted or crash reporting. Required physical-output blockers and deny/none fabric policy are enforced; malformed evidence produces failure.
- Native delegation now requires U0–U5, uses the current Python interpreter and has a bounded timeout. Failed prerequisites leave U6/U7 skipped without starting members.
- Reports use contained paths, reject filesystem links and replace each file atomically. Shipped workstation status and 454 generated report/repair-backup files were removed from the delivery copy; their hash inventory is preserved under provenance/.
- Windows bootstrap caches are checked byte-for-byte by digest against the payload, with an exact file count. Archive validation rejects traversal, links, duplicates, reserved Windows names, alternate streams and oversized files. Deletion is constrained to validated application subdirectories. Legacy IExpress extraction is disabled.
- Diagnostics now fail on a mismatched UI data version. UI version is 2.1.3; the wrapper is 1.0.1. Original pins, embedded runtime identities and historical measurements were not promoted.

## Validation

The Python fixture suite covers tampering of unchanged-size files, missing members/ledgers/claims, malformed inventories, unsafe overlays, execution refusal and safe reports. The Windows C# harness exercises 27 assertions covering valid/tampered caches, traversal, aliases, duplicates, links, size limits and bounded deletion. It invokes helper methods, never the GUI entry point.

Local Python fixture checks passed (one Windows symlink privilege skip). C# compilation succeeded locally, but endpoint protection rejected execution of the generated test executable (WinError 225). No protection was disabled or bypassed. Windows CI must run the bootstrap harness before release publication; Linux CI covers the filesystem link test. CI also verifies the pristine source inventory and parses Python, JSON, JavaScript and PowerShell files.

## Remaining limits

The original five-member registry is retained. The newly published sibling versions have not been integrated or qualified together; this release does not claim real U6/U7 execution. Historical UI evidence and provenance do not certify current hardware or production operation. ZIP hashes and mutable local registry pins provide integrity checking, not remote authenticity. Launchers operate with the current user's privileges; protection against a malicious process with the same filesystem access is outside this release's boundary. Reports are atomic per file, not a transaction across the entire report set. Native subprocess timeout kills the direct child, not an arbitrary descendant process tree.
