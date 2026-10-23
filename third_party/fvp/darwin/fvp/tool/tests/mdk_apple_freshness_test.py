"""Exercise the production CLI and resolver without a network or native SDK."""

import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
import plistlib
import shutil
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "mdk_apple_freshness", Path(__file__).resolve().parents[1] / "mdk_apple_freshness.py"
)
mdk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mdk)

NOW = "2026-10-21T00:00:00"
STAMP = b"Oct 20 2026\x0012:00:00\x00%b %e %Y %H:%M:%S\x00"
OLD_STAMP = b"Aug 14 2026\x0012:00:00\x00%b %e %Y %H:%M:%S\x00"
HEADER = b"#define MDK_MAJOR 0\n#define MDK_MINOR 39\n"


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.work = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(mock.patch.dict(os.environ, {
            "MDK_APPLE_SDK_SOURCE": "",
            "MDK_APPLE_SDK_URL": "",
            "MDK_APPLE_SDK_SHA256": "",
            "MDK_FRESHNESS_MARGIN_DAYS": "7",
        }))
        self.stack.enter_context(mock.patch.object(
            mdk.urllib.request, "urlopen",
            side_effect=AssertionError("tests must not access the network"),
        ))
        self.target = self.work / "installed" / "mdk.xcframework"
        self.root = self.work / "fixture" / "lib" / "mdk.xcframework"
        self.archive = self.work / "sdk.zip"
        self.make_framework()

    def make_framework(self):
        for identifier in ("ios-arm64", "ios-arm64_x86_64-simulator"):
            framework = self.root / identifier / "mdk.framework"
            (framework / "Headers/c").mkdir(parents=True)
            (framework / "Headers/c/global.h").write_bytes(HEADER)
            (framework / "mdk").write_bytes(b"fixture binary\x00" + STAMP)
        framework = self.root / "macos-arm64_x86_64" / "mdk.framework"
        (framework / "Versions/A/Headers/c").mkdir(parents=True)
        (framework / "Versions/A/Headers/c/global.h").write_bytes(HEADER)
        (framework / "Versions/A/mdk").write_bytes(b"fixture binary\x00" + STAMP)
        (framework / "Versions/Current").symlink_to("A")
        (framework / "Headers").symlink_to("Versions/Current/Headers")
        (framework / "mdk").symlink_to("Versions/Current/mdk")
        (self.root / "Info.plist").write_bytes(plistlib.dumps({
            "AvailableLibraries": [
                {"LibraryIdentifier": identifier}
                for identifier in (
                    "ios-arm64", "ios-arm64_x86_64-simulator", "macos-arm64_x86_64"
                )
            ]
        }))

    def pack(self):
        with zipfile.ZipFile(self.archive, "w") as bundle:
            for path in sorted(self.root.rglob("*")):
                name = str(path.relative_to(self.work / "fixture"))
                if path.is_symlink():
                    entry = zipfile.ZipInfo(name)
                    entry.create_system = 3
                    entry.external_attr = (stat.S_IFLNK | 0o755) << 16
                    bundle.writestr(entry, os.readlink(path))
                elif path.is_file():
                    bundle.write(path, name)
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def invoke(self, command="refresh", *options):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = mdk.main([
                "--destination", str(self.target), command, "--now", NOW, *options,
            ])
        return status, output.getvalue()

    def download_fixture(self, _url, destination):
        shutil.copyfile(self.archive, destination)

    def install(self):
        os.environ["MDK_APPLE_SDK_URL"] = "https://example.invalid/sdk.zip"
        os.environ["MDK_APPLE_SDK_SHA256"] = self.pack()
        with mock.patch.object(mdk, "_download", side_effect=self.download_fixture):
            status, output = self.invoke()
        self.assertEqual(status, 0, output)

    def test_custom_url_requires_a_valid_digest_before_download(self):
        os.environ["MDK_APPLE_SDK_URL"] = "https://example.invalid/sdk.zip"
        for digest in ("", "abc", "g" * 64):
            with self.subTest(digest=digest), mock.patch.object(mdk, "_download") as fetch:
                os.environ["MDK_APPLE_SDK_SHA256"] = digest
                status, output = self.invoke()
                self.assertEqual(status, 1, output)
                self.assertIn("64 hex", output)
                fetch.assert_not_called()

    def test_custom_url_digest_mismatch_prevents_extraction(self):
        self.pack()
        os.environ["MDK_APPLE_SDK_URL"] = "https://example.invalid/sdk.zip"
        os.environ["MDK_APPLE_SDK_SHA256"] = "0" * 64
        with mock.patch.object(mdk, "_download", side_effect=self.download_fixture), \
                mock.patch.object(mdk, "_extract") as extract:
            status, output = self.invoke()
        self.assertEqual(status, 1, output)
        self.assertIn("digest mismatch", output)
        extract.assert_not_called()
        self.assertFalse(self.target.exists())

    def test_url_environment_selects_url_mode_and_preserves_symlinks(self):
        self.install()
        headers = self.target / "macos-arm64_x86_64/mdk.framework/Headers"
        self.assertTrue(headers.is_symlink())
        self.assertEqual((headers / "c/global.h").read_bytes(), HEADER)
        record = json.loads((self.target.parent / "mdk-version.json").read_text())
        self.assertEqual(record["source"]["kind"], "explicit-url")
        self.assertEqual(record["sdk_version"], "0.39")
        self.assertIn("ios_simulator", record["files_sha256"])
        with mock.patch.object(mdk, "_download") as fetch:
            status, output = self.invoke("check")
        self.assertEqual(status, 0, output)
        fetch.assert_not_called()

    def test_explicit_url_source_accepts_uppercase_digest(self):
        os.environ["MDK_APPLE_SDK_SHA256"] = self.pack().upper()
        with mock.patch.object(mdk, "_download", side_effect=self.download_fixture):
            status, output = self.invoke(
                "refresh", "--source", "url", "--url", "https://example.invalid/sdk.zip"
            )
        self.assertEqual(status, 0, output)

    def test_unverified_sourceforge_fails_before_downloading(self):
        os.environ["MDK_APPLE_SDK_SOURCE"] = "sourceforge"
        with mock.patch.object(mdk, "_download") as fetch:
            status, output = self.invoke()
        self.assertEqual(status, 1, output)
        self.assertIn("no verified SHA-256", output)
        fetch.assert_not_called()

    def test_source_conflicts_and_unsafe_urls_are_refused(self):
        os.environ["MDK_APPLE_SDK_SHA256"] = "a" * 64
        cases = [
            ("--source", "upstream", "--url", "https://example.invalid/sdk.zip"),
            ("--source", "url", "--url", "http://example.invalid/sdk.zip"),
            ("--source", "url", "--url", "https://user:fixture@example.invalid/sdk.zip"),
            ("--source", "url", "--url", "https://example.invalid/sdk.zip?fixture=1"),
        ]
        for options in cases:
            with self.subTest(options=options), mock.patch.object(mdk, "_download") as fetch:
                status, output = self.invoke("refresh", *options)
                self.assertEqual(status, 1, output)
                fetch.assert_not_called()
                self.assertNotIn("user:fixture", output)
                self.assertNotIn("fixture=1", output)

    def test_upstream_requires_published_digest_and_detects_mismatch(self):
        self.pack()
        for digest in (None, "sha256:abc", "sha256:" + "0" * 64):
            response = io.BytesIO(json.dumps({"assets": [{
                "name": "mdk-sdk-apple.zip", "digest": digest,
                "browser_download_url": "https://example.invalid/sdk.zip",
            }]}).encode())
            with self.subTest(digest=digest), \
                    mock.patch.object(mdk.urllib.request, "urlopen", return_value=response), \
                    mock.patch.object(mdk, "_download", side_effect=self.download_fixture) as fetch, \
                    mock.patch.object(mdk, "_extract") as extract:
                status, output = self.invoke("refresh", "--upstream-tag", "v0.39.0")
                self.assertEqual(status, 1, output)
                if digest != "sha256:" + "0" * 64:
                    fetch.assert_not_called()
                extract.assert_not_called()

    def test_upstream_success_installs_the_verified_archive(self):
        digest = self.pack()
        with mock.patch.object(mdk, "_newest_release_tag", return_value="v0.39.0"), \
                mock.patch.object(mdk, "_github_release_asset", return_value=(
                    "https://example.invalid/sdk.zip", digest
                )), mock.patch.object(mdk, "_download", side_effect=self.download_fixture):
            status, output = self.invoke()
        self.assertEqual(status, 0, output)

    def test_default_resolver_skips_drafts_and_prereleases(self):
        response = io.BytesIO(json.dumps([
            {"tag_name": "draft", "draft": True},
            {"tag_name": "preview", "prerelease": True},
            {"tag_name": "v0.39.0", "draft": False, "prerelease": False},
        ]).encode())
        with mock.patch.object(mdk.urllib.request, "urlopen", return_value=response):
            self.assertEqual(mdk._newest_release_tag(), "v0.39.0")

    def test_stale_macos_or_simulator_is_refused_even_with_fresh_ios(self):
        for platform in ("macos", "ios_simulator"):
            with self.subTest(platform=platform):
                binary = mdk.required_members(self.root)[platform]
                binary.write_bytes(OLD_STAMP)
                os.environ["MDK_APPLE_SDK_URL"] = "https://example.invalid/sdk.zip"
                os.environ["MDK_APPLE_SDK_SHA256"] = self.pack()
                with mock.patch.object(mdk, "_download", side_effect=self.download_fixture):
                    status, output = self.invoke()
                self.assertEqual(status, 1, output)
                self.assertIn("past the", output)
                self.assertFalse(self.target.exists())
                binary.write_bytes(STAMP)

    def test_missing_simulator_slice_is_refused(self):
        shutil.rmtree(self.root / "ios-arm64_x86_64-simulator")
        os.environ["MDK_APPLE_SDK_URL"] = "https://example.invalid/sdk.zip"
        os.environ["MDK_APPLE_SDK_SHA256"] = self.pack()
        with mock.patch.object(mdk, "_download", side_effect=self.download_fixture):
            status, output = self.invoke()
        self.assertEqual(status, 1, output)
        self.assertIn("ios_simulator", output)

    def test_invalid_framework_plist_is_refused(self):
        (self.root / "Info.plist").write_bytes(b"invalid plist")
        os.environ["MDK_APPLE_SDK_URL"] = "https://example.invalid/sdk.zip"
        os.environ["MDK_APPLE_SDK_SHA256"] = self.pack()
        with mock.patch.object(mdk, "_download", side_effect=self.download_fixture):
            status, output = self.invoke()
        self.assertEqual(status, 1, output)
        self.assertIn("invalid Info.plist", output)

    def test_sdk_versions_below_floor_or_inconsistent_are_refused(self):
        header = mdk.required_members(self.root)["macos_header"]
        for minor in (38, 40):
            with self.subTest(minor=minor):
                header.write_bytes(HEADER.replace(b"39", str(minor).encode()))
                os.environ["MDK_APPLE_SDK_URL"] = "https://example.invalid/sdk.zip"
                os.environ["MDK_APPLE_SDK_SHA256"] = self.pack()
                with mock.patch.object(mdk, "_download", side_effect=self.download_fixture):
                    status, output = self.invoke()
                self.assertEqual(status, 1, output)
                self.assertFalse(self.target.exists())

    def test_check_refuses_missing_provenance_and_modified_installed_files(self):
        self.install()
        binary = mdk.required_members(self.target)["macos"]
        binary.write_bytes(binary.read_bytes() + b"modified")
        status, output = self.invoke("check")
        self.assertEqual(status, 1, output)
        self.assertIn("no longer matches", output)
        (self.target.parent / "mdk-version.json").unlink()
        status, output = self.invoke("check")
        self.assertEqual(status, 1, output)
        self.assertIn("provenance", output)

    def test_check_refuses_an_installed_sdk_after_its_window(self):
        self.install()
        status, output = self.invoke("check", "--now", "2026-12-01T00:00:00")
        self.assertEqual(status, 1, output)
        self.assertIn("past the", output)

    def test_freshness_boundaries_future_stamps_and_invalid_margins(self):
        stamp = datetime.datetime(2026, 10, 1)
        boundary = stamp + datetime.timedelta(days=37)
        mdk._check_freshness(stamp, boundary, 7)
        for now, margin in (
            (boundary + datetime.timedelta(seconds=1), 7),
            (stamp - datetime.timedelta(seconds=1), 7),
            (stamp, -1), (stamp, 44),
        ):
            with self.subTest(now=now, margin=margin), self.assertRaises(mdk.RefreshError):
                mdk._check_freshness(stamp, now, margin)


if __name__ == "__main__":
    unittest.main()
