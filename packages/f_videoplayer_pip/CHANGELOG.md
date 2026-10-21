## 0.5.9

- Coordinate the package with the Apple MDK build-time freshness fix.

## 0.5.8

- Coordinate the package with the player keyboard shortcut fixes.

## 0.5.6

- Coordinated the package release with the corrected Apple FVP FFI packaging.

## 0.5.5

- Coordinated the package release with the child-engine MDK initialization fix.

## 0.5.4

- Coordinated the PiP package with the child-engine MDK initialization fix.

## 0.5.3

- Coordinated the PiP package with the 2026-08-14 MDK nightly.

## 0.5.2

- Coordinated the PiP package version with the MDK 0.38.0 playback runtime
  refresh.

## 0.5.1

- Coordinated the PiP package with the core player's cross-platform built-in
  surface-control interaction fix.

## 0.5.0

- Coordinated native PiP packaging with the core player's controlled chrome
  suppression and host-overlay integration release.

## 0.4.2

- Coordinated the Picture-in-Picture package with the corrected standalone
  Apple Swift Package Manager release.

## 0.4.1

- Kept Android PiP session identity alive while an active stop waits for the
  operating-system exit callback, so Dart receives exactly one final stop and
  later sessions can start normally.
- Added native lifecycle-state regression tests to the Android CI lane.

## 0.4.0

- Extracted Android, iOS, and macOS system Picture-in-Picture sessions from
  Mithka into a reusable Flutter plugin.
- Preserves position, play state, speed, mute, and fractional volume across
  handoff and restoration.
- Supports Swift Package Manager and CocoaPods on Apple platforms.
- Requires Flutter 3.44 and Dart 3.12 and uses Android's built-in Kotlin
  support instead of applying the legacy Kotlin Gradle plugin.
