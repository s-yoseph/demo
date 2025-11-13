import json
import os
import subprocess
from pathlib import Path
import semver

def run(cmd):
    print(f"🧩 Running: {cmd}")
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def get_labels(event_path):
    with open(event_path) as f:
        event = json.load(f)
    return [lbl["name"] for lbl in event["pull_request"]["labels"]], event

def get_branch():
    ref = os.getenv("GITHUB_REF", "")
    return ref.split("/")[-1]

def get_latest_tag(prefix):
    try:
        tags = run(f"git tag --list '{prefix}*' | sort -V").splitlines()
        return tags[-1] if tags else f"{prefix}0.0.0"
    except subprocess.CalledProcessError:
        return f"{prefix}0.0.0"

def get_commits_since_tag(tag):
    try:
        return run(f"git log {tag}..HEAD --pretty=format:'%s|%an'").splitlines()
    except subprocess.CalledProcessError:
        return []

def categorize_changes(commits):
    sections = {
        "🚀 Features": [],
        "🐛 Fixes": [],
        "💥 Breaking Changes": [],
        "🧰 Other": []
    }
    for c in commits:
        message, author = (c.split("|") + [""])[:2]
        msg_lower = message.lower()
        line = f"- {message} (_{author}_)"
        if "feature" in msg_lower or "enhanc" in msg_lower:
            sections["🚀 Features"].append(line)
        elif "bug" in msg_lower or "fix" in msg_lower:
            sections["🐛 Fixes"].append(line)
        elif "breaking" in msg_lower:
            sections["💥 Breaking Changes"].append(line)
        else:
            sections["🧰 Other"].append(line)
    return sections

def build_changelog(sections, current_tag, next_tag):
    changelog = [f"## {next_tag} — Changes since {current_tag}\n"]
    for section, items in sections.items():
        if items:
            changelog.append(f"### {section}\n" + "\n".join(items) + "\n")
    return "\n".join(changelog)

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

def main():
    event_path = os.getenv("GITHUB_EVENT_PATH")
    labels, event = get_labels(event_path)
    branch = get_branch()

    print(f"🔖 Labels: {labels}")
    print(f"🌿 Branch: {branch}")

    # Determine bump type
    if "Breaking change" in labels:
        bump = "major"
    elif "Enhancment" in labels or "Feature" in labels:
        bump = "minor"
    else:
        bump = "patch"

    publish = "Publish" in labels
    prefix = "dev-" if branch == "develop" else ""

    current_tag = get_latest_tag(prefix)
    current_version = current_tag.replace(prefix, "")
    next_version = semver.VersionInfo.parse(current_version).bump_part(bump)
    next_tag = f"{prefix}{next_version}"

    print(f"➡️ Current tag: {current_tag}")
    print(f"➡️ Next tag: {next_tag}")

    # Generate changelog
    commits = get_commits_since_tag(current_tag)
    sections = categorize_changes(commits)
    changelog = build_changelog(sections, current_tag, next_tag)
    print("\n📝 Generated changelog:\n")
    print(changelog)

    # Update and commit to repo
    update_changelog_repo(changelog)

    # Create and push tag
    run(f"git tag {next_tag}")
    run(f"git push origin {next_tag}")
    print(f"✅ Created and pushed tag {next_tag}")

    # Optionally publish release
    if publish:
        Path("RELEASE_NOTES.md").write_text(changelog, encoding="utf-8")
        run(f'gh release create {next_tag} --notes-file RELEASE_NOTES.md')
        print(f"🚀 Published release for {next_tag}")
    else:
        print("📦 Skipping release (no Publish label)")

if __name__ == "__main__":
    main()
