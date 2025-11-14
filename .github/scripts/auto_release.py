#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import semver
import json

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
    if "enhancement" in labels:
        return "minor"
    if "bug" in labels:
        return "patch"
    return "patch"

# ----------------------------
# Get latest tag
# ----------------------------
def get_latest_tag(pattern):
    try:
        tags = run(f"git tag --list '{pattern}' | sort -V").splitlines()
        return tags[-1] if tags else None
    except subprocess.CalledProcessError:
        return None

# ----------------------------
# Get commits since last tag
# ----------------------------
def get_commits_since_tag(tag):
    if tag:
        return run(f"git log {tag}..HEAD --merges --pretty=format:'%s|%h'").splitlines()
    else:
        return run("git log --merges --pretty=format:'%s|%h'").splitlines()

# ----------------------------
# Categorize commits
# ----------------------------
def categorize_commits(commits):
    sections = {
        "🚀 Features": [],
        "🐛 Fixes": [],
        "💥 Breaking Changes": [],
        "🧰 Other": []
    }
    for c in commits:
        title, pr_hash = c.split("|") if "|" in c else (c, "")
        title_lower = title.lower()
        line = f"{title} ({pr_hash})"
        if "feature" in title_lower or "enhanc" in title_lower:
            sections["🚀 Features"].append(line)
        elif "bug" in title_lower or "fix" in title_lower:
            sections["🐛 Fixes"].append(line)
        elif "breaking" in title_lower:
            sections["💥 Breaking Changes"].append(line)
        else:
            sections["🧰 Other"].append(line)
    return sections

# ----------------------------
# Build changelog text
# ----------------------------
def build_changelog(sections, current_tag, next_tag):
    changelog = [f"{next_tag}\nChanges\n"]
    for section, items in sections.items():
        if items:
            changelog.append(f"{section}\n" + "\n".join(items) + "\n")
    return "\n".join(changelog)

# ----------------------------
# Update CHANGELOG.md
# ----------------------------
def update_changelog_repo(changelog, changelog_path="CHANGELOG.md"):
    changelog_file = Path(changelog_path)
    previous_content = changelog_file.read_text(encoding="utf-8") if changelog_file.exists() else ""
    new_content = f"{changelog}\n{previous_content}"
    changelog_file.write_text(new_content, encoding="utf-8")

    run("git config user.name 'github-actions[bot]'")
    run("git config user.email 'github-actions[bot]@users.noreply.github.com'")
    run("git add CHANGELOG.md")
    run('git commit -m "chore: update changelog [skip ci]" || echo "No changes to commit"')
    run("git push origin HEAD")

# ----------------------------
# Bump version
# ----------------------------
def bump_version(current, bump):
    v = semver.VersionInfo.parse(current)
    if bump == "major":
        return v.bump_major()
    elif bump == "minor":
        return v.bump_minor()
    elif bump == "patch":
        return v.bump_patch()
    return v

# ----------------------------
# Main function
# ----------------------------
def main():
    # Get PR labels from GitHub Actions
    event_path = os.getenv("GITHUB_EVENT_PATH")
    branch = os.getenv("GITHUB_REF", "").split("/")[-1]

    labels = []
    if event_path and Path(event_path).exists():
        with open(event_path) as f:
            event = json.load(f)
        if "pull_request" in event:
            labels = [lbl["name"] for lbl in event["pull_request"].get("labels", [])]

    print(f"🔖 Labels: {labels}")
    print(f"🌿 Branch: {branch}")

    bump = determine_bump(labels)

    # ----------------------------
    # DEVELOP BRANCH (pre-release)
    # ----------------------------
    if branch == "develop":
        latest = get_latest_tag("dev-*")
        current_version = latest.replace("dev-", "") if latest else "0.1.0"
        next_version = bump_version(current_version, bump)
        new_tag = f"dev-{next_version}"

        commits = get_commits_since_tag(latest)
        sections = categorize_commits(commits)
        changelog = build_changelog(sections, latest, new_tag)
        print(changelog)
        update_changelog_repo(changelog)

        run(f"git tag {new_tag}")
        run(f"git push origin {new_tag}")

        # Always create pre-release
        Path("RELEASE_NOTES.md").write_text(changelog, encoding="utf-8")
        run(f'gh release create {new_tag} --prerelease --notes-file RELEASE_NOTES.md')
        print(f"🚀 Published pre-release {new_tag}")
        return

    # ----------------------------
    # MAIN BRANCH (stable release)
    # ----------------------------
    if branch == "main":
        latest = get_latest_tag("v*")
        current_version = latest.replace("v", "") if latest else "0.1.0"
        next_version = bump_version(current_version, bump)
        new_tag = f"v{next_version}"

        commits = get_commits_since_tag(latest)
        sections = categorize_commits(commits)
        changelog = build_changelog(sections, latest, new_tag)
        print(changelog)
        update_changelog_repo(changelog)

        run(f"git tag {new_tag}")
        run(f"git push origin {new_tag}")

        # Stable release
        Path("RELEASE_NOTES.md").write_text(changelog, encoding="utf-8")
        run(f'gh release create {new_tag} --notes-file RELEASE_NOTES.md')
        print(f"🎉 Published stable release {new_tag}")
        return

    print("⚠️ No tagging performed — branch not supported.")


if __name__ == "__main__":
    main()
