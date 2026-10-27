#!/usr/bin/env python3
"""Prepare a reviewed formula update only after npm has published the artifact."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import urllib.request


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="an exact published stable npm version")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version):
        parser.error("use an exact stable version")
    meta = json.loads(fetch(f"https://registry.npmjs.org/@heyditto%2fcli/{args.version}"))
    assert meta["name"] == "@heyditto/cli" and meta["version"] == args.version
    commit = meta["gitHead"]
    assert re.fullmatch(r"[0-9a-f]{40}", commit), "npm must identify its source commit"
    url = f"https://registry.npmjs.org/@heyditto/cli/-/cli-{args.version}.tgz"
    assert meta["dist"]["tarball"] == url
    archive = fetch(url)
    expected = "sha512-" + base64.b64encode(hashlib.sha512(archive).digest()).decode()
    assert meta["dist"]["integrity"] == expected, "npm tarball integrity mismatch"
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        package = json.load(tar.extractfile("package/package.json"))
    assert package["name"] == meta["name"] and package["version"] == args.version
    assert package["bin"]["heyditto"] == "dist/cli.js", "review launcher changes manually"
    assert package["license"] == "MIT", "review license changes manually"
    minimum = re.search(r"(?:^| \|\| )\^24\.(\d+\.\d+)(?:$| \|\| )", package["engines"]["node"])
    assert minimum, "review changed Node support manually"
    node_version = "24." + minimum[1]
    lock_url = f"https://raw.githubusercontent.com/ditto-assistant/ditto-cli/{commit}/package-lock.json"
    lock_bytes = fetch(lock_url)
    lock = json.loads(lock_bytes)
    root = lock["packages"][""]
    assert root["name"] == package["name"] and root["version"] == args.version
    for key in ("dependencies", "optionalDependencies", "engines", "bin"):
        assert root.get(key) == package.get(key), f"published package/source lock mismatch: {key}"
    formula = Path(__file__).resolve().parents[1] / "Formula/heyditto.rb"
    content = formula.read_text()
    content, count = re.subn(r'https://registry.npmjs.org/@heyditto/cli/-/cli-[0-9.]+\.tgz', url, content)
    assert count == 1
    checksums = iter((hashlib.sha256(archive).hexdigest(), hashlib.sha256(lock_bytes).hexdigest()))
    content, count = re.subn(r'sha256 "[0-9a-f]{64}"', lambda _: f'sha256 "{next(checksums)}"', content)
    assert count == 2
    content, count = re.subn(r'https://raw.githubusercontent.com/ditto-assistant/ditto-cli/[0-9a-f]{40}/package-lock.json', lock_url, content)
    assert count == 1
    content, count = re.subn(r'24\.\d+\.\d+', node_version, content)
    assert count == 2
    formula.write_text(content)
    print(f"Prepared {args.version}; source {commit}; Node >= {node_version} <25")
    print("Review the diff, install/test it, then publish a PR. No release or push performed.")


if __name__ == "__main__":
    main()
