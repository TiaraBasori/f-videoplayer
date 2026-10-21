// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.
import PackageDescription

let package = Package(
    name: "fvp",
    platforms: [
        .iOS("12.0"),
        .macOS("10.13"),
    ],
    products: [
        // Dart resolves the C callback bridge with DynamicLibrary.process().
        // Keep this product dynamic so release archives embed the framework
        // and preserve its exported MdkCallbacks* symbols for dlsym.
        .library(name: "fvp", type: .dynamic, targets: ["fvp"]),
    ],
    dependencies: [
        .package(name: "FlutterFramework", path: "../FlutterFramework"),
    ],
    targets: [
        .target(
            name: "fvp",
            dependencies: [
                .target(name: "mdk"),
                .product(name: "FlutterFramework", package: "FlutterFramework"),
            ],
            path: ".",
            sources: [
                "Sources/fvp/FvpPlugin.mm",
                "Sources/fvp/callbacks.cpp",
            ],
            resources: [
                .process("Resources/PrivacyInfo.xcprivacy"),
            ],
            publicHeadersPath: "Sources/fvp",
            cSettings: [
                .headerSearchPath("Sources/fvp"),
            ],
            cxxSettings: [
                .unsafeFlags(["-Wno-documentation"]),
            ],
            linkerSettings: [
                .linkedFramework("Flutter", .when(platforms: [.iOS])),
                .linkedFramework("FlutterMacOS", .when(platforms: [.macOS])),
                .linkedFramework("UIKit", .when(platforms: [.iOS])),
                .linkedFramework("AVFoundation"),
                .linkedFramework("AVKit"),
                .linkedFramework("CoreMedia"),
                .linkedFramework("CoreVideo"),
                .linkedFramework("Metal"),
            ]
        ),
        .binaryTarget(
            name: "mdk",
            // Build-time refresh target: `tool/mdk_apple_freshness.py refresh`
            // installs the verified SDK here. libmdk's key-free path expires 44
            // days after its own build stamp (wang-bin/appkey app.cpp
            // `checkLicense`), which no committed URL can stay ahead of, so the
            // build resolves and verifies a fresh SDK instead of pinning one
            // archive forever. Missing here means the build was not prepared —
            // fail loudly rather than silently resolving an expired SDK.
            path: "mdk.xcframework"
        ),
    ],
    cxxLanguageStandard: .cxx20
)
