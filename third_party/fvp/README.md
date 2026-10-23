# FVP

A plugin for official [Flutter Video Player](https://pub.dev/packages/video_player) to support all desktop and mobile platforms, with hardware accelerated decoding and optimal rendering. Based on [libmdk](https://github.com/wang-bin/mdk-sdk). You can also create your own players other than official `video_player` with [backend player api](#backend-player-api)

Prebuilt example can be download from artifacts of [github actions](https://github.com/wang-bin/fvp/actions).

[More examples are here](https://github.com/wang-bin/mdk-examples/tree/master/flutter)

project is create with `flutter create -t plugin --platforms=linux,macos,windows,android,ios -i objc -a java fvp`

## Features
- All platforms: Windows x64(including win7) and arm64, Linux x64 and arm64, [embedded linux](https://github.com/sony/flutter-elinux), macOS, iOS, Android(requires flutter > 3.19 because of minSdk 21) and HarmonyOS 5.0+.
- You can choose official implementation or this plugin's
- Optimal render api: d3d11 for windows, metal for macOS/iOS, OpenGL for Linux, Android(Impeller support) and HarmonyOS.
- Hardware decoders are enabled by default
- Dolby Vision support on all platforms
- Minimal code change for existing [Video Player](https://pub.dev/packages/video_player) apps
- Support most formats via FFmpeg demuxer and software decoders if not supported by gpu. You can use your own ffmpeg 4.0~7.1(or master branch) by removing bundled ffmpeg dynamic library.
- High performance. Lower cpu, gpu and memory load than libmpv based players.
- Support audio without video
- HEVC, VP8 and VP9 transparent video
- Small footprint. Only about 10MB size increase per cpu architecture(platform dependent).


## How to Use

- Add [fvp](https://pub.dev/packages/fvp) in your pubspec.yaml dependencies: `flutter pub add fvp`. Since flutter 3.27, fvp must be a direct dependency in your app's pubspec.yaml.
- **(Optional)** Add 2 lines in your video_player examples. Without this step, this plugin will be used for video_player unsupported platforms(windows, linux), official implementation will be used otherwise.

```dart
import 'package:fvp/fvp.dart' as fvp;

fvp.registerWith(); // in main() or anywhere before creating a player. use fvp for all platforms.
```

You can also select the platforms to enable fvp implementation

```dart
registerWith(options: {'platforms': ['windows', 'macos', 'linux']}); // only these platforms will use this plugin implementation
```

To select [other decoders](https://github.com/wang-bin/mdk-sdk/wiki/Decoders), pass options like this
```dart
fvp.registerWith(options: {
    'video.decoders': ['D3D11', 'NVDEC', 'FFmpeg']
    //'lowLatency': 1, // optional for network streams
    }); // windows
```

[The document](https://pub.dev/documentation/fvp/latest/fvp/registerWith.html) lists all options for `registerWith()`

### Error Handling
Errors are usually produced when loading a media.
```dart
_controller.addListener(() {
  if (_controller.value.hasError && !_controller.value.isCompleted) {
    ...
```

### Backend Player API

```dart
import 'package:fvp/mdk.dart';
```

The plugin implements [VideoPlayerPlatform](https://pub.dev/packages/video_player_platform_interface) via [a thin wrapper](https://github.com/wang-bin/fvp/blob/master/lib/video_player_mdk.dart) on [player.dart](https://github.com/wang-bin/fvp/blob/master/lib/src/player.dart).

Now we also expose this backend player api so you can create your own players easily, and gain more features than official [video_player](https://pub.dev/packages/video_player), for example, play from a given position, loop in a range, decoder selection, media information detail etc. You can also reuse the Player instance without unconditionally create and dispose, changing the `Player.media` is enough.
[This is an example](https://github.com/wang-bin/mdk-examples/blob/master/flutter/simple/lib/multi_textures.dart)

### VideoPlayerController Extensions

With this extension, we can leverage mature `video_player` code without rewriting a new one via backend player api, but gain more features, for example `snapshot()`, `record()`, `fastSeekTo()`, `setExternalSubtitle()`.


```dart
import 'package:fvp/fvp.dart' as fvp;

fvp.registerWith(); // in main() or anywhere before creating a player. use fvp for all platforms.

// somewhere after controller is initialized
_controller.record('rtmp://127.0.0.1/live/test');
```

# Upgrade Dependencies Manually
Upgrading binary dependencies can bring new features and backend bug fixes. For macOS and iOS, in your project dir, run
```bash
pod cache clean mdk
find . -name Podfile.lock -delete
rm -rf {mac,i}os/Pods
```

This fork pins non-Apple native archives to the official 2026-08-14 MDK
nightly (0.38.0, git 5411f17), mirrored at the repository's immutable
`mdk-nightly-2026-08-14` release, and verifies their SHA-256 before extraction.
`FVP_DEPS_LATEST` is intentionally disabled. An audited mirror or version
override must provide both an HTTPS `FVP_DEPS_URL` and the exact selected
archive hash in `FVP_DEPS_SHA256`. Update the package name, version, checksum
table, Apple package checksum, notices, and native build matrix together when
upgrading.

Apple targets cannot be pinned that way. libmdk's key-free path stops working
44 days after the library was built: `App::checkLicense` in
[wang-bin/appkey](https://github.com/wang-bin/appkey) (`app.cpp`, the
`3600*24*44` freshness test) compares the build stamp compiled into the binary
with the current clock, and once it is older the player draws an
"MDK SDK is outdated" QR frame over the video. The stamp is the binary's own
build time — not the release tag, the commit, or the archive mtime — so no
committed URL can stay valid.

The Swift package therefore declares
`third_party/fvp/darwin/fvp/mdk.xcframework` as a local binary target, and the
build fills it with `darwin/fvp/tool/mdk_apple_freshness.py`:

```bash
python3 darwin/fvp/tool/mdk_apple_freshness.py \
  --destination darwin/fvp/mdk.xcframework refresh      # resolve + verify + install
python3 darwin/fvp/tool/mdk_apple_freshness.py \
  --destination darwin/fvp/mdk.xcframework check        # verify only
```

Run these commands before Flutter/SwiftPM resolves native dependencies; the
manifest does not download a missing local target. The example's GitHub Actions
iOS and macOS jobs perform this preparation before their builds.

By default, `refresh` resolves the newest stable
[wang-bin/mdk-sdk](https://github.com/wang-bin/mdk-sdk) release and requires the
asset's GitHub-published SHA-256. For an explicit HTTPS archive, provide both
`MDK_APPLE_SDK_URL` and `MDK_APPLE_SDK_SHA256` (64 hex characters from a trusted
source). A URL alone selects `url` mode, or select it with `--source url` /
`MDK_APPLE_SDK_SOURCE=url`. Credentials and query strings are refused in URLs
because the URL is recorded in provenance. Conflicting source/URL options fail.
SourceForge automatic resolution is disabled: computing a hash of downloaded
bytes is not expected-digest verification. A nightly can only be installed using
explicit URL mode with a separately verified SHA-256.

Every mode verifies the expected archive digest before extraction. The tool
checks the build stamps of the iOS, simulator and macOS slices and refuses an SDK
outside the 44-day window minus `MDK_FRESHNESS_MARGIN_DAYS` (default 7, allowed
0–43). Each slice must meet the API floor and their versions must agree.
`mdk-version.json` records provenance and installed file hashes; `check`
re-verifies those files and freshness without downloading. Missing provenance,
modified checked files, stale binaries and missing slices fail the build.

This policy only keeps new builds inside the key-free window. The SDK embedded
in an installed app continues to age and may expire 44 days after its own build;
an affected installation still needs an app update or a separately authorized
keyed build. The tool does not install a key, bypass the window or guarantee
indefinite playback. A stale upstream release is a hard stop, requiring a fresh,
verified archive rather than an unverified fallback.


# Design
- Playback control api in dart via ffi
- Manage video renderers in platform specific manners. Receive player ptr via `MethodChannel` to construct player instance and set a renderer target.
- Callbacks and events in C++ are notified by ReceivePort
- Function with a one time callback is async and returns a future

# Enable Hardware Decoders for Embedded Linux
delete libffmpeg.so.* in your app bundle, which is copied from libmdk sdk.
- Raspberry Pi: install ffmpeg and system ffmpeg libraries with v4l2 acceleration will be used.
- Rockchip: build and install https://github.com/nyanmisaka/ffmpeg-rockchip . You may also need environment var `export GL_UBO=1` for arm mali driver on linux 6.x kernel to avoid gl driver bug.

# Enable Subtitles

libass is required, and it's added to your app automatically for windows, macOS, ohos and android(remove ass.dll, libass.dylib and libass.so from mdk-sdk if you don't need it). For iOS, [download](https://sourceforge.net/projects/mdk-sdk/files/deps/dep.7z/download) and add `ass.framework` to your xcode project. For linux, system libass can be used, you may have to install manually via system package manager.

If required subtitle font is not found in the system(e.g. android), you can add [assets/subfont.ttf](https://github.com/mpv-android/mpv-android/raw/master/app/src/main/assets/subfont.ttf) in pubspec.yaml assets as the fallback. Optionally you can also download the font file by fvp like this
```dart
  fvp.registerWith(options: {
    'subtitleFontFile': 'https://github.com/mpv-android/mpv-android/raw/master/app/src/main/assets/subfont.ttf'
  });
```

# DO NOT use flutter-snap
Flutter can be installed by snap, but it will add some [enviroment vars(`CPLUS_INCLUDE_PATH` and `LIBRARY_PATH`) which may break C++ compiler](https://github.com/canonical/flutter-snap/blob/main/env.sh#L15-L18). It's not recommended to use snap, althrough building for linux is [fixed](https://github.com/wang-bin/fvp/commit/567c68270ba16b95b1198ae58850707ae4ad7b22), but it's not possible for android.

# Screenshots
![fpv_android](https://user-images.githubusercontent.com/785206/248862591-40f458e5-d7ca-4513-b709-b056deaaf421.jpeg)
![fvp_ios](https://user-images.githubusercontent.com/785206/250348936-e5e1fb14-9c81-4652-8f53-37e8d64195a3.jpg)
![fvp_win](https://user-images.githubusercontent.com/785206/248859525-920bdd51-6947-4a00-87b4-9c1a21a68d51.jpeg)
![fvp_win7](https://user-images.githubusercontent.com/785206/266754957-883d05c9-a057-4c1c-b824-0dc385a13f78.jpg)
![fvp_linux](https://user-images.githubusercontent.com/785206/248859533-ce2ad50b-2ead-43bb-bf25-6e2575c5ebe1.jpeg)
![fvp_macos](https://user-images.githubusercontent.com/785206/248859538-71de39a4-c5f0-4c8f-9920-d7dfc6cd0d9a.jpg)

The refreshed `mdk.xcframework` and its `mdk-version.json` record are build
outputs: they are git-ignored, and CI rejects a committed Apple SDK the same way
it rejects any other native runtime binary.
