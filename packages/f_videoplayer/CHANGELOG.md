## 0.5.9

- Coordinate the package with the Apple MDK build-time freshness fix.

## 0.5.8

- Preserve Command, Control, Option, and Shift shortcuts in player buttons and sliders.

## 0.5.6

- Restored the dynamic Apple FVP framework required to keep Dart FFI callback
  bridge symbols available in signed iOS release archives.

## 0.5.5

- Coordinated child-engine playback with the FVP adapter's current MDK license
  handling so detached windows cannot fall back to a QR frame.

## 0.5.4

- Coordinated the player release with synchronous MDK key installation for
  explicitly initialized Flutter engines, including detached video windows.

## 0.5.3

- Replaced the tagged MDK runtime with the official 2026-08-14 nightly while
  isolating MDK's outdated-SDK QR watermark.

## 0.5.2

- Coordinated the package release with the MDK 0.38.0 runtime refresh.

## 0.5.1

- Placed the built-in tap/double-tap interaction layer above native Android
  video surfaces while keeping host drag recognizers in the same gesture arena,
  so tapping outside the controls hides them without breaking playback
  gestures.

## 0.5.0

- Added additive surface-interaction, host-overlay, and fixed 44-pixel
  bottom-action builders without requiring replacement chrome.
- Composed built-in tap and double-tap handling outside additive host drag
  wrappers so taps still toggle chrome while actual drags remain host-owned.
- Removed the duplicate bottom-row play/pause action from regular-height
  layouts while retaining the compact merged transport below 220 pixels.
- Added controlled chrome suppression for native PiP capture surfaces and
  independent visibility flags for the built-in fullscreen and PiP buttons.
- Added host buffering augmentation and authoritative asynchronous
  platform-volume delegation with external updates and stale-result safety.
- Exposed effective chrome volume in `FVideoChromeSnapshot` and documented
  overlay layering, gesture ownership, and presentation-control composition.

## 0.4.2

- Coordinated the standalone packages with the corrected FVP Apple Swift
  Package Manager integration.

## 0.4.1

- Coordinated the standalone core package with the first production-tagged
  adapter and Picture-in-Picture plugin release.

## 0.3.0

- Added compact and wide continuous volume controls with 44-pixel interaction
  height, mute-first micro-layout fallback, mute-level restoration, and an
  `onVolumeChanged` callback for host-owned playlist persistence.
- Added `FVideoChromeStyle` with high-contrast transport, scrim, timeline,
  focus, hover, border, shadow, size, and spacing defaults that can be tailored
  without replacing the ready chrome.
- Added a safe-area- and RTL-aware top-trailing default-chrome builder for host
  actions and finite inline menus, including focus retention, semantics
  containment, close-button clearance, and bounded vertical placement without
  Material, Cupertino, or Overlay dependencies.
- Added a controlled, asynchronous picture-in-picture contract with a
  responsive default control, localized labels, keyboard support, custom-chrome
  snapshot/actions, request coalescing, and non-fatal error reporting.
- Made pending picture-in-picture controls visibly busy and noninteractive,
  with tests for callback errors, request coalescing, custom snapshots, and
  disposal during an outstanding host transition.
- Sized native and injected video surfaces at their final painted dimensions
  for every `BoxFit` mode instead of compositing an arbitrary 1000-unit texture
  through a scale transform.
- Added an immutable custom-chrome scope with playback snapshots, localized
  labels, optional previous/next navigation, and a controller-safe actions
  facade for play, seek, scrub, volume, speed, visibility, and fullscreen.
- Added `FVideoInteractionMode.delegateToChrome` so project-owned mobile
  gestures can exclusively own surface taps and drags while the package keeps
  the video surface, buffering, captions, focus, keyboard, and state updates.
- Added accessible, custom-painted previous/play/next transport controls to the
  default chrome whenever host navigation callbacks are supplied.
- Made fullscreen default controls and captions honor top, bottom, and
  horizontal safe-area insets without changing embedded spacing.
- Rendered already-initialized caller-owned controllers immediately while
  applying changed initial settings asynchronously as nonfatal commands.
- Merged center transport into the bottom row below 220 logical pixels high,
  preventing compact 16:9 chrome from painting controls over each other.
- Expanded the example and tests to cover custom chrome, navigation callbacks,
  gesture delegation, and caller-owned controller lifetime.

## 0.2.0

- Moved FVP initialization and typed backend configuration into the optional
  `f_videoplayer_fvp` adapter so official-backend applications do not
  inherit FVP native binaries.
- Made source and thumbnail creation web-safe, including a clear unsupported
  file-source contract, injectable providers, and graceful thumbnail fallback.
- Replaced the mobile-only thumbnail dependency with
  `fc_native_video_thumbnail` for Android, iOS, Linux, macOS, and Windows,
  including Swift Package Manager compatibility.
- Added network headers, caption sources, controller options, custom controller
  builders, and value equality to video source descriptions.
- Added caller-vs-player controller ownership rules and hardened controller
  replacement, initialization, listener cleanup, and disposal.
- Added configurable lifecycle behavior, focus, seek interval, controls timeout,
  fit/alignment, captions, fullscreen state, loading/error builders, and richer
  playback/error callbacks.
- Reworked controls and state views without Material/Cupertino dependencies;
  improved keyboard, pointer-wheel, touch, focus, and semantics behavior.
- Prevented premature/looping completion, preserved play intent across delayed
  scrub commands and lifecycle transitions, and made controller replacement
  cancel in-flight scrub/thumbnail state deterministically.
- Made controls focus- and accessible-navigation-aware, excluded hidden chrome
  from focus/semantics, resolved mouse-wheel ownership correctly, and prevented
  narrow/high-text-scale control overflow.
- Debounced, serialized, cached, and timeout-bounded scrub thumbnails; ignored
  stale results and sized previews from the effective video aspect ratio.
- Added keyboard/screen-reader-adjustable and RTL-aware timeline behavior with
  visible focus indication and accumulated key-repeat input.
- Hardened independent desktop windows with versioned/sanitized arguments,
  concurrent lifecycle tracking, startup timeout/error reporting, close/closeAll,
  and safe no-op implementations on unsupported platforms.
- Added a six-platform example covering package-owned and injected controllers,
  network/asset/file sources, fullscreen, callbacks, and multiple independent
  desktop windows.
- Added deterministic source, window, thumbnail, slider, design-policy, adapter,
  and example tests plus path-filtered cross-platform CI compile smoke coverage.

## 0.1.0

- Initial standalone responsive player.
- Added reusable timeline and thumbnail helpers.
- Added independent desktop video-window lifecycle support.
