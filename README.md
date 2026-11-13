# PS5 DLC-emu

Standalone PS5 replacement modules that expose DLC entries from
`/app0/dlc_emu.ini` as owned content.

The project provides three replacement modules:

- `libSceAppContent.prx` / `libSceAppContent.sprx`
- `libSceNpEntitlementAccess.prx` / `libSceNpEntitlementAccess.sprx`
- `libSceGameUpdate.prx` / `libSceGameUpdate.sprx`

The modules are intended for titles that query AppContent,
NpEntitlementAccess, or GameUpdate before enabling DLC. Native and configured
DLC are not merged into one list: list and entitlement APIs return the
configured overlay.

## Runtime Configuration

The modules load `/app0/dlc_emu.ini` lazily on the first DLC-related call. The
file is parsed once per module load and is limited to 32 KiB and 1024 valid
entries.

If the file is missing, invalid, or contains no valid entries, fake entitlement
queries return the corresponding empty, not-found, or no-entitlement result.

Minimal installed and active DLC:

```ini
[PSAC]
content_id=UP9000-PPSA01234_00-SAMPLECONTENT001
mount_point=/app0/addcont0
```

More complete example:

```ini
[PSAL]
content_id=UP9000-PPSA01234_00-SAMPLELICENSE001
label=SAMPLELICENSE001

[PSAC]
content_id=UP9000-PPSA01234_00-SAMPLECONTENT001
download_status=INSTALLED
mount_point=/app0/addcont0
entitlement_key=01040000000000000000000000000000
active_flag=true

[PSCONS]
label=SAMPLECONSUME1
use_count=0
use_limit=1
consumable=true
addcont_visible=false
unified_visible=true
active_date=0
inactive_date=18446744073709551615
```

Each section defines one DLC entry. Supported package-type sections:

| Section | Value | Typical use |
| --- | ---: | --- |
| `[NONE]` | 0 | No package-type filtering |
| `[PSGD]` | 1 | Game data entitlement |
| `[PSAC]` | 2 | Additional content with file data |
| `[PSAL]` | 3 | Add-on or license-style entitlement |
| `[PSCONS]` | 4 | Consumable or product entitlement |
| `[PSVC]` | 5 | Virtual currency |
| `[PSSUBS]` | 6 | Subscription |

Supported entry parameters:

| Parameter | Default | Behavior |
| --- | --- | --- |
| `content_id` | optional with an explicit label | Exactly 36 characters. Its final 16-character suffix becomes the default unified entitlement label. Addcont entries normally need it; store/service records may be label-only. |
| `label` / `entitlement_label` | content ID suffix | Optional 1-16 character alphanumeric unified entitlement label. Required for unified/addcont visibility when `content_id` is omitted. |
| `download_status` | `INSTALLED` | `NO_EXTRA_DATA`, `NO_IN_QUEUE`, `DOWNLOADING`, `DOWNLOAD_SUSPENDED`, or `INSTALLED`. |
| `mount_point` | `/app0/addcontN` for mountable entries | Existing path of at most 15 characters returned by fake mount APIs. DLC-emu does not create the directory. |
| `entitlement_key` | entry index + 1024 | 16-byte key encoded as 32 hexadecimal characters. The generated default stores the integer in the first eight bytes. |
| `service_label` | unset | Optional 1-6 character alphanumeric label used by service-entitlement APIs. |
| `np_service_label` | `-1` | Numeric `SceNpServiceLabel` in `0..UINT32_MAX`; exact `-1` accepts calls for any service. |
| `addcont_visible` | true for `PSAC`/`PSAL` | Exposes the entry through AppContent and NpEntitlementAccess addcont APIs. |
| `unified_visible` | true when a unified label exists | Exposes the entry through unified entitlement APIs. |
| `service_visible` | true when `service_label` exists | Exposes the entry through service entitlement APIs. |
| `mountable` | true for `PSAC` | Allows mount calls; also requires addcont visibility, active state, `INSTALLED`, and a mount point. |
| `active_flag` | `true` | Returned active state; inactive entries are omitted from addcont APIs. |
| `active_date` | `0` | Returned `SceRtcTick.tick` activation date. |
| `inactive_date` | `UINT64_MAX` | Returned expiration date. |
| `use_count` | `0` | Initial consumed count. Successful consumption increments it. |
| `use_limit` | `1` | Current remaining consumable balance. Successful consumption decrements it and poll returns the new value. |
| `consumable` / `is_consumable` | true for `PSCONS`/`PSVC` | Enables consume requests. |

Entries with duplicate unified or service labels are skipped. Invalid content
IDs, labels, keys, usage values, or mount points are also skipped. At least one
visibility surface must be enabled, and `mountable=true` requires
`addcont_visible=true`.

## Emulated Behavior

### AppContent

Entries with `addcont_visible=true` are exposed through the addcont list, info, IRO info,
entitlement-key, mount, unmount, delete, license, playable-status, and download
progress APIs.

- Addcont lists return active addcont-visible entries and preserve their configured
  `download_status`.
- Mount succeeds only for active, addcont-visible, mountable entries with status `INSTALLED`.
  It returns the configured pre-existing path and tracks mounted state locally.
- Addcont enqueue, delete, and shrink calls are successful no-ops only for
  known active addcont-visible labels or entitlement IDs.
- Bundle-license and playable-status checks succeed only for known active
  addcont-visible labels.
- SKU is reported as full; Game Trials and PFT flags are reported as OFF.
- Addcont download progress always reports a completed `1/1` download.

Bundle-license, playable-status, addcont enqueue, delete, shrink, download
progress, info, key, and mount calls return their normal not-found or
no-entitlement result for unknown or non-addcont labels.

Storage-management operations remain native AppContent RPC calls. This includes
TemporaryData, DownloadData, download shrink/expand, region, patch-install, and
store-country APIs. In particular,
`sceAppContentDownload2Shrink` and `sceAppContentDownload2Expand` forward their
opaque download handle without dereferencing it.

### NpEntitlementAccess

NpEntitlementAccess is emulated locally from the configuration file.

- Addcont list/info APIs, including the `Individual` variants, expose active
  addcont-visible entries using `SceNpEntitlementAccessAddcontEntitlementInfo`.
- Unified and service entitlement request/poll APIs return configured package
  type, active state, dates, usage counts, label filtering, and pagination.
- Entitlement-key queries return the configured or generated key.
- Consumable requests increment `use_count`, decrement the remaining
  `use_limit`, and preserve idempotency for repeated transaction IDs.
- SKU is reported as full; Game Trials and PFT flags are reported as OFF.
- Async requests are typed and independently tracked. Abort/delete and wrong
  poll-function use return request-lifecycle errors. State remains in memory
  for the current module lifetime.

### GameUpdate

GameUpdate is emulated locally with initialization and request lifecycle
validation.

- Up to 32 requests may exist simultaneously.
- Invalid structure sizes, unknown requests, aborted requests, and invalid
  initialization order return the corresponding errors.
- `sceGameUpdateCheck` and `sceGameUpdateCheckTitle` report no title or addcont
  update.
- `sceGameUpdateGetAddcontLatestVersion` returns success with `found=false` for
  every valid label.

## Building

### Windows

`DlcEmu.sln`, configuration `ReleaseHooks|Prospero`, with the Prospero SDK.
This is the reference build and is unaffected by everything below.

### Linux

`Makefile` and `build.sh` build the same three modules with
[ps5-payload-sdk](https://github.com/ps5-payload-dev/sdk) and upstream LLD, no
Prospero SDK and no Windows:

```sh
./build.sh                      # nolog and log, into out/payload-sdk/
PS5_PAYLOAD_SDK=/opt/ps5-payload-sdk ./build.sh
make verify MODULES=libSceGameUpdate
```

Every build runs `tools/verify_payload_prx.py`, which reads the finished module
back and checks it against the `.pemd` it came from. A wrong NID or library id
links cleanly and only misbehaves on the console, so the check is not optional.

Two jobs the Prospero linker does from the `.pemd` have no equivalent upstream,
and `tools/` does them instead:

- `dlc_prx_meta.py` parses the `.pemd` and derives the NIDs, the symbol
  suffixes and the module and library ids. It is the only place that
  arithmetic lives, because the generator, the linker script and the stamper
  must agree on it exactly.
- `generate_payload_exports.py` renames every export to its NID before the
  link and satisfies every import from a generated stub, so the imports carry
  NID names too.
- `prepare_prx_link_script.py` injects the SCE dynamic entries, which LLD
  cannot emit, and `stamp_payload_prx.py` points them at `.dynstr` and sets
  the SCE ELF identity afterwards.
- `prx_hash_fix.py` moves the exports into the buckets the loader will look
  in: LLD hashes the short symbol name, the loader hashes the expanded one.

The exports match the Prospero-built modules NID for NID, as do the module
name, the export libraries and their ids, and the imported modules. The
imports differ in two ways, both harmless:

- The Prospero libc reaches `tolower`, `isalnum`, `isxdigit` and `strtoul`
  through macros over `_Getptolower`, `_Getpctype` and `_Stoul`; this build
  calls the public functions. Different entry point, same work.
- There is no `--gc-sections` here, so a module keeps the shared emulation
  code its exports do not reach, and imports what that code needs.
  `libSceGameUpdate` is the visible case.

`DT_SCE_MODULE_FILENAME` is the plain module name rather than the absolute
path of whoever built it.

## ShadowMountPlus INI I/O diagnostics (PPSA31246)

This fork first tries `/app0/dlc_emu.ini`. If the file cannot be opened
or read, it retries the **independent, persistent** path
`/data/shadowmount/dlc_emu_PPSA31246.ini`. Place a copy of the existing
INI there via FTP **before** launching the game. No extra folder is required;
`/data/shadowmount` already exists on ShadowMountPlus setups.

**Do not use `/data/shadowmount/PPSA31246/dlc_emu.ini` for the fallback:**
the PPSA31246 subdirectory can be mounted from the game image and be read-only.
The separate INI filename in the parent directory avoids that mount.

The fallback is specific to PPSA31246 and can be changed or disabled by
overriding `SCE_DLC_EMU_INI_FALLBACK_PATH` at build time (set to `""` to disable).
The modules do not create directories or configuration files.

The `log/` modules report `dlc.ini.open`, `dlc.ini.read`, and
`dlc.ini.fallback` messages, with return code and errno for failures.
The `log/` modules also perform a read-only diagnostic on each successful
fake addcont mount: they try to open `<mount_point>/re_dlc_000.pak` from the
**game process** and read its first eight bytes. Check `dlc.mount.probe`
lines for the raw open return code and errno, or `open=ok read=8`.
This is **only a probe for the known PAK filename**; it does not prove that
other DLC contents are absent when that filename is missing, and it never
changes the mount's return value. The `nolog/` variant does not probe.

The INI reader uses 4096-byte reads and rejects configs above 32 KiB.
Successful loading reports the actual source path through
`dlc.load status=ok path=... entries=...`.

A failed load remains cached until the game process exits. Fully close and
restart the game after changing the INI. `nolog/` modules use the same
INI logic but have no diagnostic output.

## Logging

The `log/` build writes the persistent file
`/data/shadowmount/dlc_emu_PPSA31246.log` only. No fallback is attempted
to the game's **read-only** `/app0` sandbox or nonexistent `/download0-2`
directories. The first line of the file identifies the selected location
(`dlc.log open version=... path=...`). If the log file cannot be opened,
its failing path and return code are sent to klogsrv when the
`sceKernelDebugOutText` symbol is available.
`SCE_DLC_EMU_LOG_KERNEL_OUT` also streams regular log messages to klogsrv.
Logging remains disabled in the `nolog/` variant.

## Known Limitations

- The modules do not discover or merge native installed DLC into configured
  lists.
- Mount paths must already exist; no files or directories are created.
- Runtime state is in memory and resets when the replacement module unloads.
- Internal APIs without public declarations were reconstructed from observed
  NIDs, neighboring APIs, and RPC behavior. They require validation on the
  target firmware/title.

## Thanks

Thanks to @idlesauce for
https://github.com/idlesauce/ps4-eboot-dlc-patcher
