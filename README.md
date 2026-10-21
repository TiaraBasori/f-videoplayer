# F Video Player

F Video Player is a reusable Flutter video-player stack with responsive,
accessible controls and explicit integration points for product-specific
navigation. It was extracted from Mithka so the player can evolve and be
tested independently of one application.

The repository contains:

- `f_videoplayer`: the backend-neutral player UI, controller lifecycle,
  playlists hooks, scrub previews, captions, volume, keyboard/pointer/touch
  controls, fullscreen requests, and independent desktop windows.
- `f_videoplayer_pip`: native system Picture-in-Picture sessions on Android,
  iOS, and macOS, including playback-state restoration and fractional volume.
- `f_videoplayer_fvp`: an optional FVP/libmdk adapter for Linux, Windows, and
  deliberate backend overrides on other native platforms.
- `third_party/fvp`: the pinned BSD-3-Clause FVP fork used by the adapter. It
  contains source only; native MDK archives remain upstream downloads.
- A buildable example for mobile, web, and desktop.

The default chrome uses foundational Flutter widgets and custom-painted
glyphs. It has no Material or Cupertino dependency and can be replaced in full
through immutable state plus safe player actions.

## Highlights

- Network, asset, local-file, injected-controller, and asynchronous controller
  factory sources.
- Play/pause, replay, previous/next, seeking, buffering, captions, playback
  speed, mute, and continuous volume controls across normal layouts.
- Additive surface gestures, blocking/passive host overlays, one compact
  bottom action, host buffering augmentation, and delegated system volume.
- Controlled chrome suppression for native PiP capture plus independently
  hideable built-in fullscreen and PiP buttons for a combined host mode action.
- Responsive fallback that retains an accessible mute action when a tiny
  embedded surface cannot physically fit a level slider.
- Drag, double-tap, pointer, wheel, keyboard, focus, RTL, and screen-reader
  interaction.
- Provider-driven scrub thumbnails with time-only degradation when a backend
  cannot decode preview frames.
- Host-controlled fullscreen so applications can choose routes, orientation,
  system UI, or in-place layouts without fighting the player.
- System PiP on Android 8+, iOS, and macOS where the OS reports it available.
- Multiple concurrent native player windows on Linux, macOS, and Windows.
- Optional FVP backend with typed configuration and a local-WebM alpha route
  for Android applications that need it.

## Platform support

| Platform | Default playback | Volume | Fullscreen contract | System PiP | Separate windows |
| --- | --- | ---: | ---: | ---: | ---: |
| Android | Flutter `video_player` | Yes | Yes | Android 8+ | No |
| iOS | Flutter `video_player` | Yes | Yes | Yes | No |
| macOS | Flutter `video_player` or FVP | Yes | Yes | Yes | Yes |
| Web | Flutter `video_player_web` | Yes | Yes | Host/browser integration | No |
| Windows | FVP | Yes | Yes | Host mini-player | Yes |
| Linux | FVP | Yes | Yes | Host mini-player | Yes |

“Fullscreen contract” means the player renders the control and invokes the
host's asynchronous callback. Route selection, orientation, and window policy
remain under application control. “Host mini-player” is intentionally not
called system PiP: Windows and Linux do not expose the same native Flutter
contract used on Android and Apple platforms.

## Install from Git

Pin all packages and the FVP override to the same release tag. The adapter's
core dependency deliberately uses that tag too, which keeps Pub's Git source
identity consistent across the monorepo packages:

```yaml
dependencies:
  f_videoplayer:
    git:
      url: https://github.com/iebb/f-videoplayer.git
      ref: v0.5.9
      path: packages/f_videoplayer
  f_videoplayer_pip:
    git:
      url: https://github.com/iebb/f-videoplayer.git
      ref: v0.5.9
      path: packages/f_videoplayer_pip

# Add only when the final application uses FVP.
  f_videoplayer_fvp:
    git:
      url: https://github.com/iebb/f-videoplayer.git
      ref: v0.5.9
      path: packages/f_videoplayer_fvp
  fvp: ^0.37.3

dependency_overrides:
  fvp:
    git:
      url: https://github.com/iebb/f-videoplayer.git
      ref: v0.5.9
      path: third_party/fvp
```

Applications using only the official Android, iOS, macOS, and web backends
should omit both FVP entries so its native runtime is not added to artifacts.

For development from `master` or a specific commit, add an application-level
`dependency_overrides` entry for `f_videoplayer` using the same Git ref. Pub
otherwise treats a tag, branch, and commit as distinct sources even when they
resolve to the same object.

## Basic player

```dart
FVideoPlayer(
  source: const FVideoSource.network('https://media.example/video.mp4'),
  autoplay: false,
  onPrevious: playPrevious,
  onNext: playNext,
  onToggleFullscreen: toggleFullscreen,
)
```

See [`packages/f_videoplayer/README.md`](packages/f_videoplayer/README.md) for
the complete chrome, source, lifecycle, window, and accessibility APIs.

## Picture in Picture

The PiP package preserves position, play state, speed, mute, and normalized
volume. Android keeps the existing Flutter activity/texture in PiP. Apple
platforms hand playback to AVKit; the optional FVP fork can use its active
iOS player instead of opening a second decoder.

Android hosts must opt the activity into PiP in the manifest and forward its
lifecycle callbacks. The exact implementation is documented in
[`packages/f_videoplayer_pip/README.md`](packages/f_videoplayer_pip/README.md).

## DRM status

DRM is architecturally possible, but it is not part of v0.5.0. Secure playback
requires separate platform backends: Media3/Widevine on Android,
AVFoundation/FairPlay on Apple platforms, EME on web, and PlayReady or a
browser-backed CDM on Windows. FVP/FFmpeg is not treated as a secure DRM path.

See [`docs/DRM.md`](docs/DRM.md) for the support matrix, proposed API, output
restrictions, credential handling, and implementation roadmap.

## Development

```sh
cd packages/f_videoplayer && flutter pub get && flutter test
cd ../f_videoplayer_fvp && flutter pub get && flutter test
cd ../f_videoplayer_pip && flutter pub get && flutter test
cd ../f_videoplayer/example && flutter pub get && flutter test
```

CI additionally analyzes every package and compile-smokes Android, iOS, web,
Linux, macOS, and Windows examples.

## License

Original project code is BSD-3-Clause. The FVP fork keeps Wang Bin's upstream
BSD-3-Clause notice. libmdk and its downloaded native dependencies are not
relicensed by this repository. Read [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
before distributing native artifacts.
