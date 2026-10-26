# Build-pack verification — 2026-10-26

Tested on Windows with Python 3.14.6 x64. Personal inputs were copied into a
separate private test directory; none were added to this pack.

- Full build with an empty icon folder: PASS, generated emerald-symbol icon.
- Full PowerShell launcher from a fresh `.venv`: PASS, dependency installation,
  custom WebP icon conversion, build, and final verification.
- Reconstructed main and subsdk0 Build IDs: match the tested W3 baseline.
- Patched Emerald ROM SHA-256: matches the tested W3 baseline.
- Finished NSP: three content archives with valid IDs, sizes, metadata,
  filesystem header hashes, ExeFS hashes, and CNMT references.
- Embedded executable files, ROM, icon, and NACP: match their staged inputs.
- Title/save identity and communication authorizations: match the intended build.
- Original keys, ExeFS, control, and ROM: unchanged after each build.
- Bundled native hacPack: imports Windows system/UCRT libraries; no MSYS runtime.

- Batch launcher: PASS, full build and verification, exit code 0.
- Empty-input check: PASS, reports missing file paths without creating an NSP.

The batch file delegates to the same PowerShell launcher. Console behavior
was established by the preceding W3 build; the
newly rebuilt NSP was validated on the PC, not retested on a Switch in this run.
