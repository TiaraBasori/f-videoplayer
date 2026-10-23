#!/usr/bin/env python3
"""Refresh the Apple MDK slice to an SDK that is still inside MDK's free window.

libmdk's key-free path stops being valid 44 days after the binary was built:
`App::checkLicense` (wang-bin/appkey `app.cpp:292`) compares the build stamp
compiled into the library against the current clock, and once it is older than
`3600*24*44` it returns 0. The player then draws an "MDK SDK is outdated" QR
frame over the video and stops. The stamp is the only thing that matters: it is
not derived from the release tag, the repository commit, or the archive mtime.

A source-pinned fork cannot name a fresh archive in a manifest that is written
once, so this script runs at build time instead:

1. resolve an Apple `mdk.xcframework` source (upstream GitHub release or an
   explicit URL with a required SHA-256),
2. read the build stamp out of the ARM64 iOS binary that will be embedded,
3. refuse an SDK that is not inside the window with the remaining margin,
4. verify the SDK's major/minor version covers the API the fork compiles
   against, so a nightly that moved past it cannot be adopted silently,
5. install it at the path the Swift package manifest points at and record a
   provenance file beside it.

Nothing is trusted because of where it came from: the installed framework is
re-verified after extraction, and its stamp is re-read from the installed copy.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

# App::checkLicense marks a key-free SDK outdated once it is older than
# 3600*24*44 seconds.
FREE_WINDOW_DAYS = 44
# Adopt with room to spare, so a build that sits in a review queue or is
# rebuilt from a cached checkout a few days later still lands inside the window.
DEFAULT_MARGIN_DAYS = 7
# API the fork's Swift/Dart bridge is compiled against (MDK_MINOR in
# include/mdk/c/global.h, which is also what MDK_version() reports).
REQUIRED_MINOR = 39
REQUIRED_MAJOR = 0

UPSTREAM_REPOSITORY = "wang-bin/mdk-sdk"
UPDATER_VERSION = 2

_STAMP = re.compile(
    rb"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) ([ 0-9][0-9]) (20[0-9]{2})"
    rb"\x00([0-9]{2}:[0-9]{2}:[0-9]{2})\x00%b %e %Y %H:%M:%S"
)
_MINOR = re.compile(rb"^#define MDK_MINOR ([0-9]+)$", re.MULTILINE)
_MAJOR = re.compile(rb"^#define MDK_MAJOR ([0-9]+)$", re.MULTILINE)


class RefreshError(Exception):
    """A refresh that must stop the build rather than install a bad SDK."""


def _log(message: str) -> None:
    print(f"mdk-apple-freshness: {message}", flush=True)


def read_build_stamp(binary: Path) -> datetime.datetime:
    """Read the build stamp MDK compiled in, or refuse a binary without one.

    The stamp lives in the string pool between the license diagnostics and the
    `%b %e %Y %H:%M:%S` strptime format MDK parses it with, so the bytes after
    it identify the field order unambiguously.
    """
    data = binary.read_bytes()
    match = _STAMP.search(data)
    if match is None:
        raise RefreshError(
            f"{binary} carries no MDK build stamp; refusing to treat a binary "
            "with unreadable provenance as fresh"
        )
    month, day, year, clock = (part.decode("ascii") for part in match.groups())
    return datetime.datetime.strptime(
        f"{month} {day.strip()} {year} {clock}", "%b %d %Y %H:%M:%S"
    )


def read_sdk_version(header: Path) -> tuple[int, int]:
    data = header.read_bytes()
    major = _MAJOR.search(data)
    minor = _MINOR.search(data)
    if major is None or minor is None:
        raise RefreshError(f"{header} does not declare MDK_MAJOR/MDK_MINOR")
    return int(major.group(1)), int(minor.group(1))


def find_xcframework(root: Path) -> Path:
    """The single `mdk.xcframework` an extracted archive carries."""
    matches = sorted(
        path for path in root.rglob("mdk.xcframework") if path.is_dir()
    )
    if len(matches) != 1:
        raise RefreshError(
            f"expected exactly one mdk.xcframework under {root}, found {len(matches)}"
        )
    return matches[0]


def required_members(xcframework: Path) -> dict[str, Path]:
    """The slices this fork embeds, with the files checked after install."""
    return {
        "ios": xcframework / "ios-arm64/mdk.framework/mdk",
        "ios_header": xcframework / "ios-arm64/mdk.framework/Headers/c/global.h",
        "ios_simulator": xcframework
        / "ios-arm64_x86_64-simulator/mdk.framework/mdk",
        "ios_simulator_header": xcframework
        / "ios-arm64_x86_64-simulator/mdk.framework/Headers/c/global.h",
        "macos": xcframework / "macos-arm64_x86_64/mdk.framework/mdk",
        "macos_header": xcframework
        / "macos-arm64_x86_64/mdk.framework/Headers/c/global.h",
        "plist": xcframework / "Info.plist",
    }


def _verify_framework(
    target: Path, now: datetime.datetime, margin_days: int
) -> tuple[datetime.datetime, tuple[int, int], dict[str, str]]:
    members = required_members(target)
    missing = [name for name, path in members.items() if not path.is_file()]
    if missing:
        raise RefreshError(f"the framework is missing {', '.join(missing)}")
    try:
        with members["plist"].open("rb") as stream:
            plist = plistlib.load(stream)
        identifiers = {
            item["LibraryIdentifier"] for item in plist["AvailableLibraries"]
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RefreshError("the framework has an invalid Info.plist") from error
    if not {
        "ios-arm64", "ios-arm64_x86_64-simulator", "macos-arm64_x86_64"
    }.issubset(identifiers):
        raise RefreshError("Info.plist must declare iOS, iOS simulator and macOS")

    versions = []
    stamps = []
    for platform in ("ios", "ios_simulator", "macos"):
        stamp = read_build_stamp(members[platform])
        _check_freshness(stamp, now, margin_days)
        stamps.append(stamp)
        version = read_sdk_version(members[f"{platform}_header"])
        if version < (REQUIRED_MAJOR, REQUIRED_MINOR):
            raise RefreshError(
                f"the {platform} SDK is MDK {version[0]}.{version[1]}, below "
                f"the fork's {REQUIRED_MAJOR}.{REQUIRED_MINOR} API"
            )
        versions.append(version)
    if len(set(versions)) != 1:
        raise RefreshError("the iOS, simulator and macOS SDK versions disagree")
    return min(stamps), versions[0], {
        name: _sha256(path) for name, path in members.items()
    }


def _extract(archive: Path, destination: Path) -> None:
    """Extract with a tool that preserves the framework's symlinks.

    `mdk.framework` keeps its macOS headers behind a `Headers` symlink into
    `Versions/A`; Python's zipfile writes that entry as a regular file holding
    the link target, which leaves a framework SwiftPM cannot compile against.
    """
    if zipfile.is_zipfile(archive):
        if not shutil.which("unzip"):
            raise RefreshError("unzip is required to preserve framework symlinks")
        subprocess.run(
            ["unzip", "-q", str(archive), "-d", str(destination)], check=True
        )
        return
    if tarfile.is_tarfile(archive):
        if shutil.which("tar"):
            subprocess.run(
                ["tar", "-xf", str(archive), "-C", str(destination)], check=True
            )
            return
        with tarfile.open(archive) as bundle:
            bundle.extractall(destination)
        return
    raise RefreshError(f"{archive} is neither a zip nor a tar archive")


def _github_release_asset(tag: str, asset: str) -> tuple[str, str]:
    """Resolve an upstream release asset to its URL and GitHub-published digest."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{UPSTREAM_REPOSITORY}/releases/tags/{tag}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "mithka-mdk-freshness",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            release = json.load(response)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RefreshError(f"cannot read {UPSTREAM_REPOSITORY} release {tag}: {error}")
    for item in release.get("assets", []):
        if item.get("name") != asset:
            continue
        digest = str(item.get("digest") or "")
        if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
            raise RefreshError(
                f"{asset} in {tag} publishes no sha256 digest; refusing an "
                "unverifiable archive"
            )
        return str(item["browser_download_url"]), digest[7:].lower()
    raise RefreshError(f"{tag} has no asset named {asset}")


def _newest_release_tag() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{UPSTREAM_REPOSITORY}/releases"
        "?per_page=10",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "mithka-mdk-freshness",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            releases = json.load(response)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RefreshError(f"cannot list {UPSTREAM_REPOSITORY} releases: {error}")
    for release in releases:
        if (not release.get("draft") and not release.get("prerelease")
                and release.get("tag_name")):
            return str(release["tag_name"])
    raise RefreshError(f"{UPSTREAM_REPOSITORY} publishes no release")


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url, headers={"User-Agent": "mithka-mdk-freshness"}
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            with destination.open("wb") as target:
                shutil.copyfileobj(response, target, length=1 << 20)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RefreshError(f"cannot download the SDK archive: {error}") from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(
    source: str, upstream_tag: str | None, url: str | None, work: Path
) -> tuple[Path, dict[str, object]]:
    """Download the archive a source names; return it with provenance facts."""
    expected = os.environ.get("MDK_APPLE_SDK_SHA256", "").strip().lower()
    if source != "url" and (url or expected):
        raise RefreshError(
            "MDK_APPLE_SDK_URL/SHA256 require --source url; refusing to ignore "
            "an explicit archive or digest"
        )
    if source == "upstream":
        tag = upstream_tag or _newest_release_tag()
        link, digest = _github_release_asset(tag, "mdk-sdk-apple.zip")
        archive = work / "mdk-sdk-apple.zip"
        _log(f"downloading upstream {tag}")
        _download(link, archive)
        actual = _sha256(archive)
        if actual != digest:
            raise RefreshError(
                f"{link} digest mismatch: GitHub publishes sha256:{digest}, "
                f"downloaded {actual}"
            )
        return archive, {"kind": "upstream-release", "tag": tag, "url": link,
                         "sha256": actual}
    if source == "sourceforge":
        raise RefreshError(
            "SourceForge nightly resolution has no verified SHA-256. Use "
            "--source url with MDK_APPLE_SDK_URL and a trusted "
            "MDK_APPLE_SDK_SHA256 instead"
        )
    if source == "url":
        parsed = urllib.parse.urlsplit(url or "")
        if parsed.scheme != "https" or not parsed.hostname:
            raise RefreshError("MDK_APPLE_SDK_URL must be an https:// archive")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise RefreshError(
                "MDK_APPLE_SDK_URL must not contain credentials, query or fragment"
            )
        if upstream_tag:
            raise RefreshError("--upstream-tag cannot be combined with --source url")
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise RefreshError("MDK_APPLE_SDK_SHA256 must contain 64 hex characters")
        archive = work / "mdk-sdk-apple.zip"
        _log("downloading the explicit SDK archive")
        _download(url, archive)
        actual = _sha256(archive)
        if actual != expected:
            raise RefreshError(
                f"SDK digest mismatch: MDK_APPLE_SDK_SHA256 is {expected}, "
                f"downloaded {actual}"
            )
        return archive, {"kind": "explicit-url", "url": url, "sha256": actual}
    raise RefreshError(f"unknown source {source!r}")


def _check_freshness(
    stamp: datetime.datetime, now: datetime.datetime, margin_days: int
) -> None:
    if not 0 <= margin_days < FREE_WINDOW_DAYS:
        raise RefreshError("the safety margin must be between 0 and 43 days")
    age = now - stamp
    if age < datetime.timedelta(0):
        raise RefreshError(
            f"the SDK's build stamp {stamp.isoformat()} is in the future "
            f"relative to {now.isoformat()}; MDK rejects a system clock earlier "
            "than its build, so this build could not play video either"
        )
    if age > datetime.timedelta(days=FREE_WINDOW_DAYS - margin_days):
        raise RefreshError(
            f"the SDK was built {age.days} days ago ({stamp.date()}), past the "
            f"{FREE_WINDOW_DAYS}-day free window minus the {margin_days}-day "
            "safety margin. MDK draws its outdated-SDK frame over the last video "
            "frame and stops playback. Point MDK_APPLE_SDK_URL at a newer "
            "mdk.xcframework, or wait for the upstream mirror to refresh."
        )


def refresh(args: argparse.Namespace) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if args.now:
        now = datetime.datetime.fromisoformat(args.now)
    work = Path(tempfile.mkdtemp(prefix="mdk-apple-"))
    try:
        archive, provenance = _resolve(
            args.source, args.upstream_tag, args.url, work
        )
        extracted = work / "extracted"
        extracted.mkdir()
        _extract(archive, extracted)
        source_root = find_xcframework(extracted)
        stamp, (major, minor), hashes = _verify_framework(
            source_root, now, args.margin_days
        )

        target = Path(args.destination).resolve()
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_root, target, symlinks=True)

        installed_stamp, installed_version, installed_hashes = _verify_framework(
            target, now, args.margin_days
        )
        if (installed_stamp != stamp or installed_version != (major, minor)
                or installed_hashes != hashes):
            raise RefreshError("the installed framework differs from the verified SDK")

        record = {
            "updater": UPDATER_VERSION,
            "source": provenance,
            "build_stamp": stamp.isoformat(),
            "sdk_version": f"{major}.{minor}",
            "verified_at": now.isoformat(),
            "free_window_days": FREE_WINDOW_DAYS,
            "margin_days": args.margin_days,
            "files_sha256": installed_hashes,
        }
        (target.parent / "mdk-version.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n"
        )
        _log(
            f"installed MDK {major}.{minor} built {stamp.date()} "
            f"({(now - stamp).days} days old, "
            f"{FREE_WINDOW_DAYS - (now - stamp).days} days of key-free window left)"
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def check(args: argparse.Namespace) -> None:
    """Re-verify an installed framework without downloading anything."""
    target = Path(args.destination).resolve()
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if args.now:
        now = datetime.datetime.fromisoformat(args.now)
    stamp, (major, minor), hashes = _verify_framework(target, now, args.margin_days)
    try:
        record = json.loads((target.parent / "mdk-version.json").read_text())
    except (OSError, ValueError) as error:
        raise RefreshError("missing or unreadable SDK provenance; refresh again") from error
    if (not isinstance(record, dict)
            or record.get("updater") != UPDATER_VERSION
            or record.get("files_sha256") != hashes
            or record.get("build_stamp") != stamp.isoformat()
            or record.get("sdk_version") != f"{major}.{minor}"):
        raise RefreshError(
            "the installed SDK no longer matches its provenance; refresh again"
        )
    _log(f"installed MDK {major}.{minor} built {stamp.date()} is still fresh")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        required=True,
        help="where mdk.xcframework is installed (the Package.swift binary path)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh_parser = subparsers.add_parser("refresh", help="download and install")
    refresh_parser.add_argument(
        "--source",
        choices=("upstream", "sourceforge", "url"),
        default=os.environ.get("MDK_APPLE_SDK_SOURCE") or None,
        help="where to take the SDK from",
    )
    refresh_parser.add_argument(
        "--upstream-tag",
        default=None,
        help="wang-bin/mdk-sdk release tag; default is the newest release",
    )
    refresh_parser.add_argument(
        "--url", default=os.environ.get("MDK_APPLE_SDK_URL"), help="archive URL"
    )
    refresh_parser.add_argument(
        "--margin-days",
        type=int,
        default=int(os.environ.get("MDK_FRESHNESS_MARGIN_DAYS", DEFAULT_MARGIN_DAYS)),
        help="how much of the 44-day window to leave in reserve",
    )
    refresh_parser.add_argument("--now", default=None, help=argparse.SUPPRESS)
    refresh_parser.set_defaults(handler=refresh)

    check_parser = subparsers.add_parser("check", help="verify an installed SDK")
    check_parser.add_argument(
        "--margin-days",
        type=int,
        default=int(os.environ.get("MDK_FRESHNESS_MARGIN_DAYS", DEFAULT_MARGIN_DAYS)),
    )
    check_parser.add_argument("--now", default=None, help=argparse.SUPPRESS)
    check_parser.set_defaults(handler=check)

    args = parser.parse_args(argv)
    if args.command == "refresh" and args.source is None:
        args.source = "url" if args.url else "upstream"
    try:
        args.handler(args)
    except RefreshError as error:
        print(f"mdk-apple-freshness: error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
