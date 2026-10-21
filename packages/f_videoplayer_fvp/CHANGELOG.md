## 0.5.9

- Resolve the Apple MDK SDK at build time instead of pinning one archive. The pinned 2026-08-14 binary closed its 44-day key-free window on 2026-09-27, which is when iOS started drawing the outdated-SDK QR frame over playback. The Apple binary target is now a local path filled by `darwin/fvp/tool/mdk_apple_freshness.py`, so a build refuses an SDK that is already too old instead of shipping it.

## 0.5.8

- Coordinate the package with the player keyboard shortcut fixes.

## 0.5.6

- Restored dynamic Apple Swift-package linkage so App Store archives embed the
  FVP callback bridge used by `DynamicLibrary.process()` instead of stripping
  every `MdkCallbacks*` symbol from the final application.
- Link the dynamic product to the platform Flutter engine while retaining the
  generated `FlutterFramework` product for compile-time headers.

## 0.5.5

- Stop injecting the historical Flutter key rejected by MDK 0.38; the pinned
  fresh SDK runs key-free, while explicitly supplied current keys remain
  supported and are asserted before every native player is constructed.

## 0.5.4

- Made explicit FVP initialization install the bundled Flutter MDK key before
  returning, preventing a child engine from constructing an unkeyed player.
- Kept Dart tooling's automatic pre-main registration deferred so native log
  callbacks cannot enter Dart before the engine is ready.

## 0.5.3

- Pinned the official 2026-08-14 MDK nightly by SHA-256 on every native
  platform and verified its Apple framework in a real FVP playback build.

## 0.5.2

- Validated and documented the integrity-pinned MDK 0.38.0 FVP runtime used
  by repository consumers.

## 0.5.1

- Coordinated the adapter with the core player's cross-platform built-in
  surface-control interaction fix.

## 0.5.0

- Coordinated the adapter dependency and source-only FVP override with the
  standalone player's additive host-integration release.

## 0.4.2

- Made the FVP Apple Swift package a static product and removed redundant
  explicit Flutter framework linker settings; Flutter's generated
  `FlutterFramework` product now supplies engine symbols exactly once on both
  iOS and macOS.
- Validated the `0.37.3+fvideo.3` FVP fork and added a packaging regression
  check for the linker contract.

## 0.4.1

- Published the standalone adapter against the matching `f_videoplayer`
  release tag and the integrity-pinned FVP fork.

## 0.1.0

- Added explicit, one-time FVP backend registration for every Flutter engine.
- Added typed platform, latency, decoder, size, and advanced libmdk options.
- Added a reusable macOS packaging helper and host integration contract that
  remove MDK's Homebrew and local FFmpeg search paths before final app signing.
- Kept FVP optional so the core player does not force native FVP binaries into
  applications that use only official `video_player` implementations.
- Documented per-engine/process-wide initialization rules and the repository's
  validated `0.37.3+fvideo.1` Apple Swift Package Manager override.
