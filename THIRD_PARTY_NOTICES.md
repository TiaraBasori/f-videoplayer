# Third-party notices

The repository license covers original F Video Player source. It does not
relicense third-party projects, downloaded SDKs, CDMs, or media.

## FVP

`third_party/fvp` is a modified fork of Wang Bin's FVP project, based on the
0.37.3 line. FVP is BSD-3-Clause. Its upstream license is preserved verbatim at
`third_party/fvp/LICENSE`; upstream names may not be used for endorsement.

Upstream: https://github.com/wang-bin/fvp

Local changes include Apple Swift Package Manager packaging, active-player iOS
Picture in Picture, player-volume preservation, Android startup hardening, and
native dependency version alignment.

## libmdk and downloaded native runtimes

FVP downloads libmdk archives at build time. libmdk has separate upstream
terms and is not covered by this repository's BSD license. Consult:

https://github.com/wang-bin/mdk-sdk#license

The build scripts pin the official 2026-08-14 MDK nightly (0.38.0, git
5411f17) mirrored at the repository's `mdk-nightly-2026-08-14` release, and
verify every asset with SHA-256 before extraction. Apple SDKs are resolved at
build time instead, because libmdk's key-free path expires 44 days after the
library's own build stamp; `darwin/fvp/tool/mdk_apple_freshness.py` verifies
the archive against the digest its publisher reports and refuses an SDK outside
that window. Integrity verification does not replace license review.

Native archives may contain FFmpeg, libass, TLS/crypto libraries, or other
components. Before distributing a binary, the application owner must preserve
the exact archive's notices, SBOM, source/build provenance, and applicable
license obligations. In particular:

- FFmpeg builds may be LGPL-2.1-or-later and require corresponding-source and
  relinking compliance: https://ffmpeg.org/legal.html
- libass is ISC-licensed: https://github.com/libass/libass
- some inspected Android MDK/FFmpeg builds reference statically linked wolfSSL
  components. wolfSSL is dual-licensed and its exact downstream grant was not
  present in this source repository. Do not redistribute that runtime until
  the archive supplier provides an SBOM and confirms the applicable license.

This repository does not commit MDK/CDM binaries and does not represent their
licensing as BSD-3-Clause.

## Flutter templates and dependencies

The example includes Flutter-generated platform templates and default assets,
licensed under the Flutter Authors' BSD-3-Clause license. Runtime dependencies
retain their own licenses. Major direct dependencies include Flutter and
`video_player` (BSD-3-Clause), `fc_native_video_thumbnail` (BSD-3-Clause), and
`multi_window_manager` (MIT).

Generated Flutter application notices must remain in distributed artifacts.
