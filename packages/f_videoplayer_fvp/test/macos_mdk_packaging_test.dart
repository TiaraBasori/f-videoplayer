import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('explicit registration installs MDK setup synchronously', () {
    final entrypoint = File(
      '../../third_party/fvp/lib/fvp.dart',
    ).readAsStringSync();
    final backend = File(
      '../../third_party/fvp/lib/src/video_player_mdk.dart',
    ).readAsStringSync();

    expect(
      entrypoint,
      contains('deferSetupUntilMain: true'),
      reason: 'Only the automatic pre-main registrant should defer setup.',
    );
    expect(backend, contains('if (deferSetupUntilMain)'));
    expect(backend, contains('Future<void>.delayed(Duration.zero, _setupMdk)'));
    expect(
      backend,
      contains('} else {\n      _setupMdk();\n    }'),
      reason: 'Manual registerWith must install the key before returning.',
    );
  });

  test('every native player reasserts an explicit process-wide MDK key', () {
    final backend = File(
      '../../third_party/fvp/lib/src/video_player_mdk.dart',
    ).readAsStringSync();
    final createStart = backend.indexOf(
      'Future<int?> create(DataSource dataSource) async',
    );
    final keyInstall = backend.indexOf('_installMdkKey();', createStart);
    final playerCreate = backend.indexOf(
      'final player = MdkVideoPlayer();',
      createStart,
    );

    expect(createStart, greaterThanOrEqualTo(0));
    expect(keyInstall, greaterThan(createStart));
    expect(
      keyInstall,
      lessThan(playerCreate),
      reason: 'The key must be installed before MDK constructs a player.',
    );
    expect(
      backend,
      isNot(contains('_kDefaultMdkKey')),
      reason: 'The stale historical key makes MDK 0.38 render a QR frame.',
    );
    expect(
      backend,
      contains("if (mdkKey is! String || mdkKey.isEmpty) return"),
    );
  });

  test('Apple packaging refreshes MDK instead of pinning an expiring archive', () {
    final manifest = File(
      '../../third_party/fvp/darwin/fvp/Package.swift',
    ).readAsStringSync();
    final cmake = File(
      '../../third_party/fvp/cmake/deps.cmake',
    ).readAsStringSync();

    // libmdk's key-free path expires 44 days after its own build stamp, so an
    // Apple binary target that names one archive is a latent
    // "MDK SDK is outdated" QR frame. The build installs a verified SDK at the
    // local path instead.
    expect(manifest, contains('path: "mdk.xcframework"'));
    expect(manifest, isNot(contains('mdk-nightly-2026-08-14')));
    expect(manifest, isNot(contains('mdk.xcframework.zip')));

    // Non-Apple archives keep their immutable nightly mirror and digests.
    expect(cmake, contains('releases/download/mdk-nightly-2026-08-14'));
    for (final digest in [
      'e61c38782b13198732749caaca436b7c0e13d34cf8d9050f5e5505838ab5529b',
      'c541fa13dd12e17414eb05e6a176f3fb40a93cc5c38aaf85dbce1cd68d2828f0',
      '580c657e635023fe588a007fb8acf06d1e11c5c28fefe3ae3302850b8be2d800',
      'de5a8ff0a104b220601775019b350810a73c13354571100b9a649b46faf33d3d',
      'd89195411c42d213013f3e48f2ae707dffc6b750a73a56bdf7793dade582d6ae',
      '0e0aee20b1c12cbc2e5b362ad028e556748a39ba9785a1065bed0dea1148a882',
    ]) {
      expect(cmake, contains(digest));
    }
  });

  test('the MDK freshness gate reads the binary stamp, not the release', () {
    final tool = File(
      '../../third_party/fvp/darwin/fvp/tool/mdk_apple_freshness.py',
    ).readAsStringSync();

    // 44 days is MDK's own window (wang-bin/appkey checkLicense).
    expect(tool, contains('FREE_WINDOW_DAYS = 44'));
    expect(tool, contains('DEFAULT_MARGIN_DAYS = 7'));
    // The stamp sits between the license diagnostics and the strptime format
    // MDK parses it with, so the reader must key on that format string.
    expect(tool, contains(r'%b %e %Y %H:%M:%S'));
    // An SDK may not silently move past the API the bridge compiles against.
    expect(tool, contains('REQUIRED_MINOR = 39'));
    expect(tool, contains('MDK_MAJOR'));
    expect(tool, contains('MDK_MINOR'));
    // GitHub publishes per-asset sha256 digests; an unverifiable archive is
    // refused rather than trusted.
    expect(tool, contains('sha256:'));
    // The macOS slice keeps its headers behind a Headers symlink; extracting
    // with Python's zipfile would write that entry as a regular file.
    expect(tool, contains('unzip'));
    expect(
      tool,
      contains('def check('),
      reason: 'A prepared checkout must be re-verifiable without a download.',
    );
  });

  test('Apple SPM embeds the FFI bridge as a dynamic product', () {
    final manifest = File(
      '../../third_party/fvp/darwin/fvp/Package.swift',
    ).readAsStringSync();

    expect(
      manifest,
      contains(
        '.package(name: "FlutterFramework", path: "../FlutterFramework")',
      ),
    );
    expect(
      manifest,
      contains(
        '.product(name: "FlutterFramework", package: "FlutterFramework")',
      ),
    );
    expect(
      manifest,
      contains('.library(name: "fvp", type: .dynamic, targets: ["fvp"])'),
    );
    expect(manifest, isNot(contains('type: .static')));
    expect(manifest, contains('DynamicLibrary.process()'));
    expect(manifest, contains('MdkCallbacks*'));
    expect(
      manifest,
      contains('.linkedFramework("Flutter", .when(platforms: [.iOS]))'),
    );
    expect(
      manifest,
      contains('.linkedFramework("FlutterMacOS", .when(platforms: [.macOS]))'),
    );

    // Native Apple SDK frameworks remain explicit because the generated
    // FlutterFramework product supplies only Flutter's engine framework.
    expect(
      manifest,
      contains('.linkedFramework("UIKit", .when(platforms: [.iOS]))'),
    );
    for (final framework in [
      'AVFoundation',
      'AVKit',
      'CoreMedia',
      'CoreVideo',
      'Metal',
    ]) {
      expect(manifest, contains('.linkedFramework("$framework")'));
    }
  });

  test('macOS hosts sanitize embedded MDK before final app signing', () {
    final script = File(
      '../../third_party/fvp/darwin/fvp/tool/sanitize_mdk_macos.sh',
    ).readAsStringSync();
    final exampleProject = File(
      '../f_videoplayer/example/macos/Runner.xcodeproj/project.pbxproj',
    ).readAsStringSync();

    expect(script, contains('set -euo pipefail'));
    expect(script, contains(r'mdk_binary="$mdk_framework/Versions/A/mdk"'));
    expect(script, contains('install_name_tool'));
    expect(script, contains('-delete_rpath'));
    expect(script, contains('/opt/homebrew/lib'));
    expect(script, contains('/usr/local/lib'));
    expect(script, isNot(contains('grep -Fq')));
    expect(script, contains(r'load_commands="$(/usr/bin/otool -l'));
    expect(script, contains('EXPANDED_CODE_SIGN_IDENTITY'));
    expect(script, contains("-type f -name '*.dylib' -print0"));
    expect(script, contains(r'codesign --verify --strict "$nested_dylib"'));
    expect(script, contains('codesign --verify --deep --strict'));
    expect(
      script.indexOf(r'--sign "$signing_identity"'),
      lessThan(script.lastIndexOf(r'--sign "$signing_identity"')),
    );
    expect(
      script.indexOf(r'"$nested_dylib"'),
      lessThan(script.indexOf(r'"$mdk_framework"')),
    );

    expect(exampleProject, contains('Sanitize embedded MDK'));
    expect(exampleProject, contains('/bin/bash'));
    expect(
      exampleProject,
      contains(
        r'$SRCROOT/Flutter/ephemeral/Packages/.packages/fvp/tool/'
        'sanitize_mdk_macos.sh',
      ),
    );
    expect(
      exampleProject.indexOf('3399D490228B24CF009A79C7 /* ShellScript */,'),
      lessThan(exampleProject.indexOf('Sanitize embedded MDK */,')),
    );
  });
}
