import sys
import re
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/bump_version.py <new_version>")
        print("Example: python scripts/bump_version.py 0.1.2")
        sys.exit(1)
        
    new_version = sys.argv[1].strip()
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print(f"Error: Version must be in major.minor.patch format (e.g. 0.1.2). Got: {new_version}")
        sys.exit(1)
        
    root = Path(__file__).resolve().parent.parent
    version_file = root / "VERSION"
    if not version_file.exists():
        print("Error: VERSION file not found.")
        sys.exit(1)
        
    old_version = version_file.read_text(encoding="utf-8").strip()
    if old_version == new_version:
        print(f"Version is already {new_version}. Nothing to do.")
        sys.exit(0)
        
    print(f"Bumping version from {old_version} to {new_version}...\n")
    
    files_to_update = [
        (
            root / "VERSION",
            "VERSION file",
            lambda c: new_version
        ),
        (
            root / "desktop-tauri" / "package.json",
            "package.json version field",
            lambda c: c.replace(f'"version": "{old_version}"', f'"version": "{new_version}"')
        ),
        (
            root / "desktop-tauri" / "package-lock.json",
            "package-lock.json version field",
            lambda c: c.replace(f'"version": "{old_version}"', f'"version": "{new_version}"')
        ),
        (
            root / "desktop-tauri" / "src-tauri" / "tauri.conf.json",
            "tauri.conf.json version field",
            lambda c: c.replace(f'"version": "{old_version}"', f'"version": "{new_version}"')
        ),
        (
            root / "desktop-tauri" / "src-tauri" / "Cargo.toml",
            "tauri Cargo.toml version field",
            lambda c: c.replace(f'version = "{old_version}"', f'version = "{new_version}"')
        ),
        (
            root / "desktop-tauri" / "src" / "components" / "AppShell" / "Sidebar.tsx",
            "Sidebar.tsx footer version",
            lambda c: c.replace(f'Ubahin {old_version}', f'Ubahin {new_version}')
        ),
        (
            root / "pyproject.toml",
            "pyproject.toml version field",
            lambda c: c.replace(f'version = "{old_version}"', f'version = "{new_version}"')
        ),
        (
            root / "engine-python" / "engine_main.py",
            "engine_main.py ENGINE_VERSION",
            lambda c: c.replace(f'ENGINE_VERSION = "{old_version}"', f'ENGINE_VERSION = "{new_version}"')
        ),
        (
            root / "src" / "ubahin" / "desktop" / "bridge.py",
            "bridge.py VERSION",
            lambda c: c.replace(f'VERSION = "{old_version}"', f'VERSION = "{new_version}"')
        ),
        (
            root / "installer_script.iss",
            "Inno Setup MyAppVersion",
            lambda c: c.replace(f'#define MyAppVersion "{old_version}"', f'#define MyAppVersion "{new_version}"')
        ),
    ]
    
    updated_count = 0
    for path, desc, update_fn in files_to_update:
        if not path.exists():
            print(f"Warning: {path.relative_to(root)} ({desc}) not found. Skipping.")
            continue
            
        content = path.read_text(encoding="utf-8")
        updated_content = update_fn(content)
        if content != updated_content:
            path.write_text(updated_content, encoding="utf-8")
            print(f"[UPDATED] {path.relative_to(root)} - {desc}")
            updated_count += 1
        else:
            print(f"[NO CHANGE] {path.relative_to(root)} - {desc} (value already matches or pattern not found)")
            
    print(f"\nDone! Updated {updated_count} files.")
    print(f"To compile the new release setup installer, run:")
    print(f"  .\\build_release_windows.bat")

if __name__ == "__main__":
    main()
