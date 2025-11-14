#!/usr/bin/env python3
import os
import subprocess
import semver

# ----------------------------
# Helper to run shell commands
# ----------------------------
def run(cmd):
    print(f"🧩 Running: {cmd}")
    result = subprocess.check_output(cmd, shell=True).decode().strip()
    return result


# ----------------------------
# Determine bump type from labels
# ----------------------------
def determine_bump(labels):
    labels = [l.lower() for l in labels]

    if "publish" in labels:
        return "none"        # publishing only, no bump

    if "major" in labels:
        return "major"
    if "enhancement" in labels:
        return "minor"
    if "bug" in labels:
        return "patch"

    return "patch"  # default fallback


# ----------------------------
# Get latest version tag
# ----------------------------
def get_latest_tag(pattern):
    cmd = f"git tag --list '{pattern}' | sort -V | tail -n 1"
    try:
        latest = run(cmd)
        return latest if latest else None
    except:
        return None


# ----------------------------
# Bump SemVer properly
# ----------------------------
def bump_version(current, bump):
    v = semver.VersionInfo.parse(current)

    if bump == "major":
        return v.bump_major()
    if bump == "minor":
        return v.bump_minor()
    if bump == "patch":
        return v.bump_patch()
    return v  # no bump


# ----------------------------
# MAIN LOGIC
# ----------------------------
def main():
    labels_raw = os.getenv("PR_LABELS", "")
    branch = os.getenv("BRANCH", "")

    labels = [l.strip() for l in labels_raw.split(",") if l.strip()]
    print(f"🔖 Labels: {labels}")
    print(f"🌿 Branch: {branch}")

    bump = determine_bump(labels)

    # ----------------------------
    # DEVELOP BRANCH (pre-release)
    # ----------------------------
    if branch == "develop":
        latest = get_latest_tag("dev-*")

        if latest:
            current_version = latest.replace("dev-", "")
        else:
            current_version = "0.1.0"

        next_version = bump_version(current_version, bump)
        new_tag = f"dev-{next_version}"
        print(f"🚀 New pre-release tag: {new_tag}")

        run(f"git tag {new_tag}")
        run(f"git push origin {new_tag}")
        return

    # ----------------------------
    # MAIN BRANCH (stable release)
    # ----------------------------
    if branch == "main":
        latest = get_latest_tag("v*")

        if latest:
            current_version = latest.replace("v", "")
        else:
            current_version = "0.1.0"

        next_version = bump_version(current_version, bump)
        new_tag = f"v{next_version}"
        print(f"🎉 New stable release tag: {new_tag}")

        run(f"git tag {new_tag}")
        run(f"git push origin {new_tag}")
        return

    print("⚠️ No tagging performed — branch not supported.")


if __name__ == "__main__":
    main()
