#!/usr/bin/env python3
import os
import subprocess
import semver
import re
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
    return v

# ----------------------------
# Get merged PR commits since tag
# ----------------------------
def get_commits_since_tag(tag):
    try:
        # only PR merge commits
        return run(f"git log {tag}..HEAD --merges --pretty=format:'%s|%h'").splitlines()
    except subprocess.CalledProcessError:
        return []

# ----------------------------
# Categorize commits for changelog
# ----------------------------
def categorize_commits(commits):
    sections = {
        "🚀 Enhancements": [],
        "🐛 Bug Fixes": [],
        "🧰 Other": []
    }

    pr_merge_re = re.compile(r"Merge pull request #(\d+) from .*? (.+)", re.IGNORECASE)

    for c in commits:
        parts = c.split("|")
        msg = parts[0].strip()
        commit_hash = parts[1].strip() if len(parts) > 1 else ""

        m = pr_merge_re.match(msg)
        if m:
            pr_number = m.group(1)
            pr_title = m.group(2)
            line = f"{pr_title} (#{pr_number})"
        else:
            line = f"{msg} (#{commit_hash})"

        msg_lower = msg.lower()
        if "feature" in msg_lower or "enhanc" in msg_lower:
            sections["🚀 Enhancements"].append(line)
        elif "bug" in msg_lower or "fix" in msg_lower:
            sections["🐛 Bug Fixes"].append(line)
        else:
            sections["🧰 Other"].append(line)

    return sections

# ----------------------------
# Build changelog string
# ----------------------------
def build_changelog(sections, current_tag, next_tag):
    changelog = [f"{next_tag}\nChanges\n"]
    for section, items in sections.items():
        if items:
            changelog.append(section)
            changelog.extend(items)
    return "\n".join(changelog)

# ----------------------------
# Update changelog file in repo
# ----------------------------
def update_changelog_repo(changelog, changelog_path="CHANGELOG.md"):
    changelog_file = Path(changelog_path)
    previous_content = changelog_file.read_text(encoding="utf-8") if changelog_file.exists() else ""
    new_content = f"{changelog}\n\n{previous_content}"
    changelog_file.write_text(new_content, encoding="utf-8")

    run("git config user.name 'github-actions[bot]'")
    run("git config user.email 'github-actions[bot]@users.noreply.github.com'")
    run("git add CHANGELOG.md")
    run('git commit -m "chore: update changelog [skip ci]" || echo "No changes to commit"')
    run("git push origin HEAD")

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

        commits = get_commits_since_tag(latest) if latest else get_commits_since_tag("HEAD~10")
        sections = categorize_commits(commits)
        changelog = build_changelog(sections, latest, new_tag)
        print(changelog)

        update_changelog_repo(changelog)
        run(f"git tag {new_tag}")
        run(f"git push origin {new_tag}")

        if publish:
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
        print(f"🎉 New stable release tag: {new_tag}")

        commits = get_commits_since_tag(latest) if latest else get_commits_since_tag("HEAD~10")
        sections = categorize_commits(commits)
        changelog = build_changelog(sections, latest, new_tag)
        print(changelog)

        update_changelog_repo(changelog)
        run(f"git tag {new_tag}")
        run(f"git push origin {new_tag}")

        if publish:
            Path("RELEASE_NOTES.md").write_text(changelog, encoding="utf-8")
            run(f'gh release create {new_tag} --notes-file RELEASE_NOTES.md')
            print(f"🎉 Published stable release {new_tag}")
        return

    print("⚠️ No tagging performed — branch not supported.")

if __name__ == "__main__":
    main()
