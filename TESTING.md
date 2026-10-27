# W6 builder verification — 2026-10-26

A complete Windows build passed using copies of the user's original inputs in
a separate private test folder. No personal inputs were added to this pack.

- Reconstructed W6 ROM: exact byte match with the hardware-tested installer.
- All ExeFS files and control.nacp: exact byte matches with W6.
- Custom WebP icon conversion, NCA/NSP packaging and independent verification: pass.
- Installation version 11, display 1.0.0 / Nintendo, title and save IDs: checked.
- Original inputs: unchanged after building.

W6 was confirmed working by the user on Switch after the W5 failure. The newly
rebuilt installer was verified on the PC; that particular rebuilt file has not
been retested on the console.

The existing batch/PowerShell launchers and dependency versions are unchanged.
Their fresh-environment setup was tested with the earlier W3 pack. This update
tested the full Python build path with the updated frozen patch data.

The public archive and repository delivery exclude keys, ROMs, saves, original
executables, control metadata, generated NSPs and private test folders.
