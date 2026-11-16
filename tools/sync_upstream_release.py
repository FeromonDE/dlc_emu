#!/usr/bin/env python3
"""Merge a new stable upstream release and request a patched build."""
import json
import os
from pathlib import Path
import subprocess
import sys


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def sync():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    config_path = Path(".github/upstream-release.json")
    config = json.loads(config_path.read_text())
    upstream = config["repository"]
    repository = os.environ["GITHUB_REPOSITORY"]
    release = json.loads(run("gh", "api", f"repos/{upstream}/releases/latest"))
    if release.get("draft") or release.get("prerelease"):
        raise RuntimeError("Expected a published stable upstream release")
    tag = release["tag_name"]
    ref = f"refs/tags/{tag}"
    run("git", "check-ref-format", ref)
    run("git", "fetch", "--no-tags", f"https://github.com/{upstream}.git", ref)
    upstream_sha = run("git", "rev-parse", "FETCH_HEAD^{commit}")
    if upstream_sha != config["sha"]:
        if run("git", "status", "--porcelain"):
            raise RuntimeError("Refusing to update a checkout with local changes")
        run("git", "config", "user.name", "github-actions[bot]")
        run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        result = subprocess.run(["git", "merge", "--no-commit", "--no-ff", upstream_sha])
        # The fork owns its build and update workflows. Keep them while
        # merging upstream source, recipes, dependencies and tests.
        run("git", "restore", "--source=HEAD", "--staged", "--worktree", ".github/workflows")
        conflicts = run("git", "diff", "--name-only", "--diff-filter=U")
        if conflicts:
            raise RuntimeError(f"Upstream merge needs review: {conflicts}")
        if result.returncode and not (Path(".git") / "MERGE_HEAD").exists():
            raise RuntimeError("Upstream merge failed before it could be applied")
        run(sys.executable, "tools/patch_download_log.py")
        run(sys.executable, "tools/patch_download_log.py", "--check")
        config.update(tag=tag, sha=upstream_sha)
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        run("git", "add", "-A")
        run("git", "commit", "-m", f"Merge {upstream} {tag} with diagnostic logs in /download")
        run("git", "push", "origin", "HEAD:main")
        sha = run("git", "rev-parse", "HEAD")
    else:
        sha = run("git", "rev-parse", "HEAD")
        releases = json.loads(run("gh", "api", f"repos/{repository}/releases?per_page=100"))
        for published in releases:
            if published.get("draft") or not published["tag_name"].endswith("-" + sha[:7]):
                continue
            if any(a["name"] == config["release_asset"] for a in published.get("assets", [])):
                print(f"Upstream {tag} already built; skipping")
                return
        # Retry a missing or failed build without creating another commit.
    output = Path(os.environ["GITHUB_OUTPUT"])
    with output.open("a") as stream:
        stream.write(f"sha={sha}\n")
    print(f"Build requested for {sha}")


if __name__ == "__main__":
    sync()
