# W6 — 2026-10-26

Concrete reproduced W5 defect: absolute linker-script symbols lack STT_FUNC/Thumb
typing, so GNU ld generated BX PC / ARM LDR PC long-call veneers. ARMv5 can
interwork through LDR PC; GBA ARMv4T cannot. W5 reached original Thumb routines
in ARM state. The defect also affects W4's equivalent generated call veneers.

Replaced the three W5 veneers with local, explicitly typed Thumb LDR R3 / BX R3
tail stubs for _IsLinkTaskFinished, GetMultiplayerId and SetLinkStandbyCallback.
No ARM mapping symbols are allowed in the resulting shim ELF. Payload is 140
bytes, versus W5's 164. W6 is independently built from W3.

Updated CPU tests to TI925T ARMv4T and assert Thumb state at mocked original
Thumb-function boundaries. Without the latter assertion, mocks could mask a
wrong-state entry even on the correct CPU. New isolated regression executes
the actual linked veneers with a minimal real Thumb callee: all three W5 stubs
fail, all three W6 replacements return correctly. This is the first concrete
local reproduction of a regression in the failed readiness candidates.

The original trade/save callbacks and all native modules stay unchanged from W3.
Only two post-write readiness BL sites, an eight-byte header gateway and the own
Thumb shim differ. Display 1.0.0 / Nintendo, install version 11, same save/title ID.

Hardware: W3 saves traded Pokémon but post-save communication hangs; W4 screeches/
freezes during saving; W5 is closed by the Switch around saving. The supplied
three Emerald crash reports identify older module images, not W5. Their thread
dumps contain those same reported thread registers and do not establish a W5
exception location. No relevant Atmosphère directory was found on mounted PC
drive roots during this inspection. No SD override was established.

Tests: ARMv4T stub regression, 20 actual callback paths, 12 actual callback/RFU
lifecycle cycles, original cleanup/reentry, repeated party block exchange without
RFU reset, ABI/state assertions, W3 service routes, independent NSP verification.
Hardware reconnect remains unconfirmed; full official peer and full trade-menu
rendering are not executed by these tests. No Emerald-host fix is claimed.

## Build

Use prepare_trade_reference.py as documented in W5-CHANGELOG.md, then:

```powershell
python outputs/emerald-wireless-bridge/build_w5.py --candidate W6 --base-stage work/emerald-release-1.0.0 --previous-stage work/emerald-wireless-w3c --reference work/emerald-trade-reference/trade.o --toolchain C:/devkitPro/devkitARM/bin --out work/emerald-wireless-w6-new
python outputs/emerald-wireless-bridge/test_trade_w4.py --stage work/emerald-wireless-w6-new --reference work/emerald-wireless-w6-new/reconnect-build/reference.json --base-stage work/emerald-release-1.0.0 --out work/emerald-wireless-w6-new/callback-tests.json
python outputs/emerald-wireless-bridge/test_reconnect_w5.py --stage work/emerald-wireless-w6-new --rfu-image work/rs-emerald-port-build/rfu-apcs-test/rfu-core-test.elf --out work/emerald-wireless-w6-new/reconnect-tests.json
python outputs/emerald-wireless-bridge/test_armv4_calls.py --bad-stage work/emerald-wireless-w5-final --fixed-stage work/emerald-wireless-w6-new --out work/emerald-wireless-w6-new/armv4-regression.json
python outputs/emerald-standalone-builder/standalone.py package --stage work/emerald-wireless-w6-new --hacpack "outputs/Emerald Build Pack/tools/hacpack.exe" --keys "YOUR/prod.keys" --output outputs/Emerald-W6-new
```

build_w5.py now defaults to W6. Explicit --candidate W5 exists only to reproduce
the withdrawn bug. Names of shared test scripts are retained for reproducibility;
the corrected W6 build does not consume W4/W5 patched ROMs. The optional regression
uses the withdrawn W5 stage solely as a failing comparison fixture.
