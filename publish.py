import os
import shutil
import subprocess
import sys
import getpass

def run_command(command):
    """Runs a shell command and exits if it fails."""
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError:
        print(f"Error running: {command}")
        sys.exit(1)

def main():
    print("--- 📦 PyPI Automated Publisher ---")
    
    # 1. Install/Update Build Tools
    print("[*] Installing build tools...")
    run_command(f"{sys.executable} -m pip install build twine --upgrade --quiet")

    # 2. Clean previous builds
    if os.path.exists("dist"):
        print("[*] Cleaning old 'dist/' folder...")
        shutil.rmtree("dist")

    # 3. Build the Package
    print("[*] Building package...")
    run_command(f"{sys.executable} -m build")

    # 4. Upload to PyPI
    print("\n[!] Ready to upload.")
    print("    Enter your API Token (starts with 'pypi-').")
    
    # Check if a token allows non-interactive usage or prompt
    token = os.environ.get("PYPI_TOKEN")
    if not token:
        token = getpass.getpass("Token: ").strip()

    if not token.startswith("pypi-"):
        print("[!] Warning: Token usually starts with 'pypi-'")
    
    print("\n[*] Uploading to PyPI...")
    try:
        subprocess.run(
            [sys.executable, "-m", "twine", "upload", "dist/*", "-u", "__token__", "-p", token],
            check=True
        )
        print("\n[SUCCESS] Package is live! 🚀")
        print("Install it with: pip install tes3mp-easy")
    except subprocess.CalledProcessError:
        print("\n[FAIL] Upload failed. Check your token and package name.")

if __name__ == "__main__":
    main()
