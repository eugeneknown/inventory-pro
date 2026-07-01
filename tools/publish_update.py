import os
import json
import subprocess
import hashlib

# Configuration
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(APP_ROOT, "update_manifest.json")
VERSION_PATH = os.path.join(APP_ROOT, "version.txt")

def run_git_command(command):
    try:
        result = subprocess.run(command, cwd=APP_ROOT, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return []

def get_changed_files():
    """Get all files that have changed in the working directory or staging area."""
    # Files modified but not committed
    modified = run_git_command(["git", "diff", "--name-only"])
    # Files staged
    staged = run_git_command(["git", "diff", "--cached", "--name-only"])
    # Untracked files
    untracked = run_git_command(["git", "ls-files", "--others", "--exclude-standard"])
    
    all_files = set(modified + staged + untracked)
    
    # Filter out empty strings, non-app files, and the manifest itself
    valid_extensions = ('.py', '.txt', '.json', '.md')
    return [
        f for f in all_files 
        if f and f.endswith(valid_extensions) and f != "update_manifest.json"
    ]

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    full_path = os.path.join(APP_ROOT, filepath)
    if not os.path.exists(full_path):
        return None
    with open(full_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def main():
    print("🚀 InventoryPRO Auto-Update Publisher 🚀")
    print("-" * 40)
    
    # 1. Get Repo Name
    repo_name = input("Enter your GitHub Repository (e.g. eugenedev/inventorypro): ").strip()
    if not repo_name:
        print("❌ Repository name is required!")
        return

    # 2. Get Version Number
    try:
        with open(VERSION_PATH, "r") as f:
            current_version = f.read().strip()
    except Exception:
        current_version = "1.0.0"

    print(f"\nCurrent Version: {current_version}")
    new_version = input("Enter NEW Version Number (e.g. 1.0.1): ").strip()
    if not new_version:
        print("❌ Version number is required!")
        return

    # 3. Find Changed Files
    print("\n🔍 Detecting changed files...")
    changed_files = get_changed_files()
    
    # If no uncommitted changes, ask if they want to build from the last commit
    if not changed_files:
        print("No uncommitted changes found. Checking last commit...")
        changed_files = run_git_command(["git", "diff", "--name-only", "HEAD~1", "HEAD"])
        changed_files = [f for f in changed_files if f and f != "update_manifest.json"]

    if not changed_files:
        print("❌ No changed files found to update!")
        return

    print(f"Found {len(changed_files)} files to update:")
    for f in changed_files:
        print(f"  - {f}")

    # 4. Generate Manifest
    print("\n📝 Generating update_manifest.json...")
    manifest_files = []
    
    for filepath in changed_files:
        file_hash = get_file_hash(filepath)
        if file_hash:
            manifest_files.append({
                "path": filepath.replace("\\", "/"),
                "url": f"https://raw.githubusercontent.com/{repo_name}/main/{filepath.replace(chr(92), '/')}",
                "sha256": file_hash
            })

    manifest = {
        "version": new_version,
        "files": manifest_files
    }

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    # 5. Update version.txt
    with open(VERSION_PATH, "w") as f:
        f.write(new_version + "\n")

    print("\n✅ Success!")
    print(f"1. Updated version.txt to {new_version}")
    print(f"2. Created update_manifest.json with {len(manifest_files)} files")
    print("\nNext Steps:")
    print('  git add .')
    print(f'  git commit -m "Release v{new_version}"')
    print('  git push')

if __name__ == "__main__":
    main()
