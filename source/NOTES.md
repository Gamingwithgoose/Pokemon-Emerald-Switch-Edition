# Build and patch notes

## Reproduction

`builder/patches.json` stores only changed byte ranges and input/output hashes.
The normal build applies these ranges to the user's exact original dump and
vanilla ROM; it does not assemble source or depend on a previously built NSP.
The result must have these IDs before packaging:

- main: `4ba69d8ed940a09e14bd55b272a73ce7114b499750b5f45479aa2cd83925c358`
- subsdk0: `5772a23d47d16a96913158ae9fbe109526793f65e0ee068eff56c58a233a707d`
- patched ROM SHA-256: `a6179cc1b1908019f0da032e4ac19443eb1ef9d391f97cbb7d40ad6a6e98ef07`

The scripts decompress and validate each NSO segment, apply changes, extend the
text segment to its verified boundary, update BSS size, recalculate segment
hashes, and generate the same standalone build IDs. NPDM application IDs and
the explicit save-owner grant are changed semantically. The NACP patch restores
the tested communication authorizations, names, version, and save identity.

`rtc.s`, `save_gate.s`, `router.s`, `shims.s`, and `logger.s` document the added
assembly. They are included for inspection and development. Editing these
files alone does not change the frozen patch data used by `build.bat`.

## RTC and saves

- Main cartridge halfword dispatch: `0x33994` and `0x33A84`.
- Main RTC wrappers: `0x160DA0` and `0x160DEC`.
- RTC payload: subsdk0 `0x1136960`; state `0x15EF000`.
- Save gate: subsdk0 `0x1136C30`; state `0x15EF040`.
- Emerald section sizes: `F2C,F80,F80,F80,F08,F80,F80,F80,F80,F80,F80,F80,F80,7D0`.

The RTC implements the cartridge serial protocol and reads the Switch system
clock. It supports status and BCD time reads; calendar writes are ignored.
It does not emulate an independently adjustable battery clock. In-game clock
offsets remain in the game's save. The save gate checks the complete rotating
section set, signature, checksums, and counters before allowing a committed
native snapshot. It uses the actual emulator backup-manager layout.

## W3 wireless hooks

Eight guest Thumb BL sites route through the gateway at `080000CC`, with a
284-byte router/shim payload at `08F00000`:

| Guest site | Native service | Purpose |
| --- | --- | --- |
| 082E44F0 | 47 | Publish game data |
| 082E45FC | 42 | Host |
| 082E480C | 45 | Search |
| 082E4860 | 45 | Refresh candidates |
| 082E49DE | 43 | Join |
| 0800EDD6 | 44 | Runtime shutdown |
| 082E46A0 | 49 | Host busy query |
| 082E4844 | 4A | Search busy query |

Original RFU function bodies and the boot stop routine stay in place apart
from the selected call instructions. The ROM header and RTC GPIO area are
preserved. The host router uses the existing native service table.

The bounded logger at subsdk0 `0x1136E80`, state `0x15EF080`, writes at most
32 records to `save:/Emerald_W3.bin`. Each record is six little-endian u32:
sequence, service, pre-command native state, mode, peer count, guest R0.
Polls are sampled every 64 calls. The first captured record on a new launch
truncates that diagnostic file. It never opens `Emerald_e.sav`.

## Packager source and licenses

hacPack upstream: https://github.com/DarkMatterCore/hacPack

Pinned commit: `e506cb58b7843d86df7518156debd28f3b575638`.
The included `tools/hacPack-source.zip` contains its corresponding source,
including bundled mbedTLS, configuration, and `build-windows.sh`.
The Windows build used GCC 16.2.0's x86_64-w64-mingw32ucrt toolchain and GNU make,
with static library linkage. Those tools are only needed to rebuild hacPack.
GPLv2 and component notices are included beside the executable and in the
source archive. Preserve them when sharing the pack.

Credits: hacPack and its upstream contributors; pret's pokeemerald and
pokefirered decompilations for protocol/save analysis; gmr7z's original Hoenn
save patch for the starting emulator-save adaptation. RTC, corrected save
gate, standalone changes, W3 integration, and this builder were developed in
this project. No blanket relicensing of third-party work is claimed.

Public reference commits used during analysis:

- pokeemerald: `731ad5bfd6e6f265508d0efcca0ba42f9dcf5881`
- pokefirered: `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`

## Scope

Only the exact English Emerald ROM and LeafGreen dump listed in README are
supported. Ruby, Sapphire, Seaglass, other regions, and emulator updates need
their own analysis. No Champion/National Dex bypass or save editor is included.
Berry events are not independently confirmed here. The pack keeps the tested
diagnostic logger and internal content version 8, with display version 1.0.0.
