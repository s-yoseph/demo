#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import semver
import json

# ----------------------------
# Run shell command
# ----------------------------
def run(cmd):
    print(f"🧩 Running: {cmd}")
    return subprocess.check_output(cmd, shell=True, text=True).strip()

# ----------------------------
# Get PR labels
# ----------------------------
def get_labels(event_path):
    with open(event_path) as f:
        event = json.load(f)
    return [lbl["name"].lower() for lbl in event["pull_request"]["labels"]]

# ----------------------------
# Determine bump
# ----------------------------
def determine_bump(labels):
    if "major" in labels:
        return "major"
    if "enhancement" in labels or "feature" in labels:
        return "minor"
    if "bug" in labels:
        return "patch"
    return "patch"

# ----------------------------
# Latest tag
# ----------------------------
def get_latest_tag(pattern):
    try:
        tags = run(f"git tag --list '{pattern}' | sort -V").splitlines()
        return tags[-1] if tags else None
    except:
        return None

# ----------------------------
# Bump version
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
# Get commits
# ----------------------------
def get_commits_since_tag(tag):
    try:
        # Format: <commit short message>|<commit hash>
        return run(f'git log {tag}..HEAD --pretty=format:"%s|%h"').splitlines()
    except:
        return []

# ----------------------------
# Categorize commits
# ----------------------------
def categorize_commits(commits):
    sections = {
        "🚀 Enhancements": [],
        "🐛 Bug Fixes": [],
        "🧰 Other": []
    }
    for c in commits:
        parts = c.split("|")
        msg = parts[0].strip()
        pr_hash = parts[1].strip() if len(parts) > 1 else ""
        line = f"{msg} (#{pr_hash})"  # short commit + PR hash
        msg_lower = msg.lower()
        if "feature" in msg_lower or "enhanc" in msg_lower:
            sections["🚀 Enhancements"].append(line)
        elif "bug" in msg_lower or "fix" in msg_lower:
            sections["🐛 Bug Fixes"].append(line)
        else:
            sections["🧰 Other"].append(line)
    return sections

# ----------------------------
# Build changelog text
# ----------------------------
def build_changelog(sections, tag):
    lines = [f"{tag}\nChanges"]
    for section, items in sections.items():
        if items:
            lines.append(section)
            lines.extend(items)
    return "\n".join(lines)

# ----------------------------
# Update changelog file
# ----------------------------
def update_changelog(changelog):
    path = Path("CHANGELOG.md")
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    new_content = f"{changelog}\n\n{previous}"
    path.write_text(new_content, encoding="utf-8")

    run("git config user.name 'github-actions[bot]'")
    run("git config user.email 'github-actions[bot]@users.noreply.github.com'")
    run("git add CHANGELOG.md")
    run('git commit -m "chore: update changelog [skip ci]" || echo "No changes to commit"')
    run("git push origin HEAD")

# ----------------------------
# Main function
# ----------------------------
def main():
    event_path = os.getenv("GITHUB_EVENT_PATH")
    branch = os.getenv("GITHUB_REF", "").split("/")[-1]

    labels = get_labels(event_path)
    print(f"🔖 Labels: {labels}")
    print(f"🌿 Branch: {branch}")

    bump = determine_bump(labels)
    publish = "publish" in labels

    # Determine tag
    if branch == "develop":
        latest = get_latest_tag("dev-*")
        current_version = latest.replace("dev-", "") if latest else "0.1.0"
        next_version = bump_version(current_version, bump)
        new_tag = f"dev-{next_version}"
    elif branch == "main":
        latest = get_latest_tag("v*")
        current_version = latest.replace("v", "") if latest else "0.1.0"
        next_version = bump_version(current_version, bump)
        new_tag = f"v{next_version}"
    else:
        print("⚠️ No tagging performed — branch not supported.")
        return

    print(f"➡️ Current tag: {current_version}")
    print(f"➡️ Next tag: {new_tag}")

    # Generate changelog
    commits = get_commits_since_tag(latest) if latest else []
    sections = categorize_commits(commits)
    changelog = build_changelog(sections, new_tag)
    print("\n📝 Generated changelog:\n")
    print(changelog)

    # Update CHANGELOG.md
    update_changelog(changelog)

    # Create and push tag
    run(f"git tag {new_tag}")
    run(f"git push origin {new_tag}")
    print(f"✅ Created and pushed tag {new_tag}")

    # Publish GitHub release if label exists
    if publish:
        Path("RELEASE_NOTES.md").write_text(changelog, encoding="utf-8")
        run(f'gh release create {new_tag} --notes-file RELEASE_NOTES.md')
        print(f"🚀 Published release {new_tag}")
    else:
        print("📦 Skipping release (no Publish label)")

if __name__ == "__main__":
    main()
