# W6 builder update — 2026-10-26

- Reconstructs the hardware-tested W6 ROM exactly.
- Includes the post-trade communication handshake and ARMv4T-safe call stubs.
- Keeps original LeafGreen inputs, unique Emerald save/title ID and 1.0.0 / Nintendo.
- Uses installation version 11 consistently in the manifest and NSP metadata.
- No extra compiler or software is required by build.bat.

# Changelog

## Build pack 1 — 2026-10-26

- Packaged the working Emerald W6 RTC/save/wireless implementation for local rebuilding.
- Added empty input directories, a batch launcher, a PowerShell launcher, and a plain-language guide.
- Added strict input checks, optional custom icons, a generated default icon, and automatic NSP verification.
- Included a native Windows hacPack build, corresponding source, and upstream licenses.
- Kept the standalone Title ID, Emerald_e filenames, display 1.0.0, and internal content version 8.
- Excluded personal keys, game dumps, ROMs, saves, custom artwork, and generated NSPs.

## Hardware baseline

- User confirmed RTC progression across application close/relaunch and sleep.
- User confirmed the corrected save build, Emerald-to-Emerald communication,
  and Emerald-to-FireRed trading after setting required progression flags.
- The earlier cross-game readiness messages came from game progression checks.
  No readiness bypass is part of this pack.
