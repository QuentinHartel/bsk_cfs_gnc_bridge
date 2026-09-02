# cFS Setup Log

This documents the steps actually taken to get a working cFS build with a
custom `gnc_app` on this project, including the real problems hit along the
way. Written after the fact so future-me (or anyone cloning this repo) has
a real reference instead of a sanitized "it just worked" writeup.

## Environment

- WSL2 (Ubuntu) on Windows, hostname `DESKTOP-GVQLVV8`
- cFS cloned as a git submodule at `cfs/`
- Build config used: `native_std` (plain host Linux build, no EDS, no RTEMS)

## 1. Initial clone and submodule setup

```bash
git submodule add https://github.com/nasa/cFS.git cfs
cd cfs
git submodule update --init --recursive
```

cFS's top-level repo is a shell — cFE, OSAL, PSP, and the sample apps are
all submodules within it. A single-level `submodule add` is not enough;
`--recursive` is required or you'll hit CMake "source for N module(s) not
found" errors later.

## 2. First build attempt — RTEMS toolchain error /opt/rtems-5/bin/i386-rtems5-gcc is not a full path to an existing compiler tool


This bundle's default `sample_defs/targets.cmake` defines a second CPU
target (`cpu2`) that's configured to cross-compile for RTEMS, which
requires a toolchain most dev machines don't have installed. This is not
a broken environment — it's expected unless you specifically want to
build for that target.

**Fix:** use the `native_std` build config instead of bare `make prep`:

```bash
make native_std.prep
make native_std.install
```

This bundle's Makefile uses config-qualified targets
(`<config>.<goal>`), each writing to its own `build-<config>/` directory
— not the single `build/` directory used by older/simpler cFS Makefile
flavors.

## 3. Stale CMake cache after a folder rename

Renamed the project folder from `bsk-cfs-gnc-bridge` (hyphens) to
`bsk_cfs_gnc_bridge` (underscores) partway through setup. This broke the
existing `build-native_std/` cache: 

CMake Error: The current CMakeCache.txt directory .../bsk-cfs-gnc-bridge/... is
different than the directory .../bsk_cfs_gnc_bridge/... where CMakeCache.txt was created.


CMake caches the exact absolute path a build directory was configured at.
**Fix:** a stale/partial clean isn't enough — do a full `rm -rf` of the
build directory, not just the stamp file, then re-prep:

```bash
rm -rf build-native_std
make native_std.prep
```

## 4. Shared memory (`shmget`) crash on boot
CFE_PSP - Cannot shmget User Reserved Area Shared memory Segment: Invalid argument
CFE_PSP_Panic called with error code = 0xFFFFFFFF. Exiting.


Caused by a stale System V shared memory segment left behind from a
previous `./core-cpu1` run that didn't exit cleanly (Ctrl+C, crash).
Unrelated to any app code — purely an OS-level leftover.

**Fix:**
```bash
ipcs -m                  # find the stale segment
ipcrm -M <key>            # remove it
```

If no stale segment is found, check WSL2's shared memory limits:
```bash
cat /proc/sys/kernel/shmmax
cat /proc/sys/kernel/shmall
```

## 5. Adding a custom app (`gnc_app`) — the real gauntlet

Full chain of issues hit getting a custom app to actually build, load,
and run. See `gotchas.md` for the detailed breakdown — summary of steps
that were actually required, in order:

1. App source created at `cfs-apps/gnc_app/` (kept outside `cfs/` so it
   has its own git history), symlinked into `cfs/apps/gnc_app`.
2. Added `gnc_app` to `cpu1_APPLIST` in `sample_defs/targets.cmake`.
3. Fixed a missing-include compile error (`CFE_ES_RegisterApp` implicit
   declaration) — turned out to be a deprecated/removed API, not a missing
   header. Current cFE no longer requires apps to call this.
4. Discovered `CFE_ES_WriteToSysLog` doesn't print to console or a file
   by default — switched to `CFE_EVS_SendEvent` for visible status
   messages, which is also the officially recommended approach.
5. Discovered the startup script (`cfe_es_startup.scr`) is **fully
   auto-generated** at install time by `sample_defs/generate_startup.cmake`
   — direct edits to any `.scr` file are silently overwritten on every
   rebuild. This cost the most time in this whole process.
6. Found that `generate_startup.cmake` has a **hardcoded app allowlist**
   (`CFS_APP_STARTUP_ORDER`) separate from `targets.cmake`'s `_APPLIST` —
   an app must be in both to actually appear in the generated startup
   script. Added `gnc_app` to this list.
7. Renamed the app's entry point function to match the generator's fixed
   naming convention (`${APP_UPPER}_AppMain`) — `GNC_AppMain` became
   `GNC_APP_AppMain`.

## 8. Working state confirmed

```bash
cd ~/bsk_cfs_gnc_bridge/cfs
rm -rf build-native_std
make native_std.prep
make native_std.install
cd build-native_std/exe/cpu1
./core-cpu1
```

`gnc_app` now appears in the generated `cfe_es_startup.scr`, builds
successfully, and loads at boot alongside the stock sample apps.
