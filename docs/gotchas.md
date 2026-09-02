# cFS Gotchas

Non-obvious issues hit while setting this project up, kept short and
reference-style. If something breaks in a similar way later, check here
first before re-debugging from scratch.

## Build system

- **`make prep` alone may target RTEMS/cross-compile configs you don't
  have toolchains for.** Use config-qualified targets instead:
  `make native_std.prep`, `make native_std.install`.

- **CMake caches the absolute build path.** Renaming or moving the
  project folder breaks any existing `build-*/` directory. Fix: full
  `rm -rf build-<config>`, don't try to patch the cache.

- **`rm -f build-*/stamp.prep` is not a clean.** It only clears the stamp
  file cFS's Makefile uses to track whether prep ran — the actual CMake
  cache underneath is untouched. Use `rm -rf` on the whole build
  directory when something's actually stale.

## Startup script / app registration

- **`cfe_es_startup.scr` is generated, not static.** It's rebuilt from
  scratch on every `make ... .install` by
  `sample_defs/generate_startup.cmake`. Any direct edit to a `.scr` file
  will be silently overwritten on the next build. There may also be
  multiple decoy copies elsewhere in the tree (e.g. under
  `cfe/cmake/sample_defs/`, or inside unrelated apps' example configs
  like `apps/sbn/examples/`) — none of those are the one actually
  consumed by this build.

- **Two separate lists control whether a custom app shows up at boot:**
  1. `<cpuname>_APPLIST` in `sample_defs/targets.cmake` — controls
     whether the app is *built and installed* at all.
  2. `CFS_APP_STARTUP_ORDER` inside `generate_startup.cmake` — a
     **hardcoded allowlist** the generator checks against `_APPLIST`
     before writing a `CFE_APP` line. An app can be correctly listed in
     `_APPLIST`, compile fine, and produce a working `.so`, and *still
     never appear in the generated startup script* if it's missing from
     this second list. This is easy to miss because there's no error —
     the app is just silently absent from the boot sequence.

- **The generator's entry-point naming is fixed, not inferred from your
  code.** It writes `${APP_UPPER}_AppMain` regardless of what your
  actual function is named. If your function is named differently
  (e.g. `GNC_AppMain` instead of `GNC_APP_AppMain`), the startup line
  will reference a symbol that doesn't exist in your `.so`, and it'll
  fail to load. Match your entry point name to the generator's
  convention, or the app will build but fail at load time.

- **`CFE_APP` line format has no fixed convention across cFS bundles.**
  Some bundles/apps use `/cf/<name>.so` with explicit path and
  extension; others (including this one, via the generator) use a bare
  app name with no path or extension. Check an existing working line in
  the *actual generated file* before assuming a format — don't copy a
  format from documentation or another bundle without verifying.

## cFE API surface

- **`CFE_ES_RegisterApp()` no longer needs to be called.** Older
  tutorials/docs list it as mandatory first-call for every app. Current
  cFE handles app registration automatically at load time; calling it
  will fail with "implicit declaration" because the function has been
  removed, not because of a missing include. If you hit this, don't
  hunt for a header — just delete the call.

- **cFE's public API headers are consolidated in one place per recent
  versions:** `cfe/modules/core_api/fsw/inc/` contains `cfe_es.h`,
  `cfe_sb.h`, `cfe_evs.h`, `cfe_tbl.h`, `cfe_time.h`, etc. all together
  — not scattered per-module under each module's own `fsw/inc/` as
  older tutorials might suggest. When hitting an "implicit declaration"
  error for a cFE function, check here first.

- **`CFE_ES_WriteToSysLog()` does not print to console or write to a
  file by default.** It appends to an in-memory buffer meant for
  fallback diagnostics (e.g. when `CFE_EVS_Register` itself fails), not
  general logging. Use `CFE_EVS_SendEvent()` for anything you actually
  want to see during development — it's also the officially recommended
  approach for normal status/error reporting.

## Runtime

- **`shmget` "Invalid argument" on boot is almost always a stale shared
  memory segment**, not a real config problem — happens after a
  `./core-cpu1` run is killed uncleanly (Ctrl+C, crash). Check with
  `ipcs -m`, clear with `ipcrm -M <key>`. If no stale segment exists,
  check WSL2's `kernel.shmmax` / `kernel.shmall` sysctls, which can
  default unusually low.

## General debugging approach that worked

When something silently doesn't show up (a startup line, a config
value, a compiled artifact) despite "everything looking right":
1. Don't trust an edited source file — check the **actual generated /
   staged output** the build produced.
2. Grep broadly first (`grep -rl "<distinctive string>" .`) to find the
   *real* source of generated content before assuming which file you've
   been editing is authoritative.
3. Read full build/install logs, not just narrow greps — silent
   skips (like the `CFS_APP_STARTUP_ORDER` allowlist) don't error, they
   just produce no output for the thing you're looking for.
