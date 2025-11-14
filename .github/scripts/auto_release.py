#!/usr/bin/env python3
import os
import json
import subprocess
import semver
from pathlib import Path

# ----------------------------
# Helper to run shell commands
# ----------------------------
def run(cmd):
    print(f"🧩 Running: {cmd}")
    return subprocess.check_output(cmd, shell=True, text=True).strip()

# ----------------------------
# Determine bump type from labels
# ----------------------------
def determine_bump(labels):
    labels = [l.lower() for l in labels]

    if "major" in labels:
        return "major"
    if "enhancement" in labels or "feature" in labels:
        return "minor"
    if "bug" in labels or "fix" in labels:
        return "patch"
    return "patch"

# ----------------------------
# Get latest tag
# ----------------------------
def get_latest_tag(pattern):
    try:
        tags = run(f"git tag --list '{pattern}' | sort -V").splitlines()
        return tags[-1] if tags else None
    except:
        return None

# ----------------------------
# Bump semver
# ----------------------------
def bump_version(current, bump):
    v = semver.VersionInfo.parse(current)
    if bump == "major":
        return v.bump_major()
    if bump == "minor":
        return v.bump_minor()
    if bump == "patch":
        return v.bump_patch()
    return v

# ----------------------------
# Main logic
# ----------------------------
def main():
    # Get branch and PR labels from environment
    branch = os.getenv("BRANCH", "")
    pr_labels_raw = os.getenv("PR_LABELS", "")
    labels = [l.strip() for l in pr_labels_raw.split(",") if l.strip()]
    
    print(f"🔖 Labels: {labels}")
    print(f"🌿 Branch: {branch}")

    bump = determine_bump(labels)
    publish = "publish" in [l.lower() for l in labels]

    # ----------------------------
    # DEVELOP BRANCH (pre-release)
    # ----------------------------
    if branch == "develop":
        latest = get_latest_tag("dev-*")
        current_version = latest.replace("dev-", "") if latest else "0.1.0"
        next_version = bump_version(current_version, bump)
        new_tag = f"dev-{next_version}"
        print(f"🚀 New pre-release tag: {new_tag}")

    # ----------------------------
    # MAIN BRANCH (stable release)
    # ----------------------------
    elif branch == "main":
        latest = get_latest_tag("v*")
        current_version = latest.replace("v", "") if latest else "0.1.0"
        next_version = bump_version(current_version, bump)
        new_tag = f"v{next_version}"
        print(f"🎉 New stable release tag: {new_tag}")

    else:
        print("⚠️ No tagging performed — branch not supported.")
        return

    # Create and push tag
    run(f"git tag {new_tag}")
    run(f"git push origin {new_tag}")
    print(f"✅ Created and pushed tag {new_tag}")

    # Optionally publish release
    if publish:
        changelog_path = Path("RELEASE_NOTES.md")
        changelog_path.write_text(f"# Release {new_tag}\n\nLabels: {', '.join(labels)}", encoding="utf-8")
        run(f"gh release create {new_tag} --notes-file RELEASE_NOTES.md")
        print(f"🚀 Published release for {new_tag}")
    else:
        print("📦 Skipping release (no Publish label)")

if __name__ == "__main__":
    main()
