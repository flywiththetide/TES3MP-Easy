import os
import shutil
from pathlib import Path
from rich.console import Console

console = Console()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def check_flatpak():
    if shutil.which("flatpak") is None:
        console.print("[bold red][!] Flatpak is not installed.[/bold red]")
        console.print("    The Client setup requires Flatpak. Please install it.")
        return False
    return True

def get_project_root():
    # Returns the root of the repo (parent of src)
    # NOTE: With pip install, this might point to site-packages, so relying on this for data files is brittle.
    # We kept it for backward compat in checks.py but we should prefer config.
    return Path(__file__).parent.parent.parent

def get_config_dir():
    """
    Returns a standard location to store user preferences/data.
    Usually: ~/.config/tes3mp-easy/
    """
    path = Path.home() / ".config" / "tes3mp-easy"
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_data_path(path):
    """Remembers where the user said their Morrowind files were."""
    config_file = get_config_dir() / "data_location.txt"
    with open(config_file, 'w') as f:
        f.write(str(path))

def load_stored_data_path():
    """Recalls the Morrowind location."""
    config_file = get_config_dir() / "data_location.txt"
    if config_file.exists():
        with open(config_file, 'r') as f:
            return Path(f.read().strip())
    return None
