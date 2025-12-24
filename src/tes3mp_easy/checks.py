import shutil
import subprocess
import os
import socket
import ctypes.util
from pathlib import Path

def check_dependencies():
    """
    Checks for required system libraries by running ldd on the tes3mp binary.
    Returns a list of missing library names.
    """
    missing = []
    
    # Locate the binary - tes3mp.x86_64 is the actual binary, tes3mp-browser/server are scripts
    install_dir = get_install_dir()
    
    # We might have different binary names depending on version, generic catch
    binaries = ["tes3mp.x86_64", "tes3mp"]
    target_bin = None
    
    for b in binaries:
        p = install_dir / b
        if p.exists():
            target_bin = p
            break
            
    if not target_bin:
        # If binary isn't installed yet, valid to return empty list or handle elsewhere
        return []

    # TES3MP bundles its own libraries in lib/ folder
    # We need to include this in LD_LIBRARY_PATH when running ldd
    lib_dir = install_dir / "lib"
    env = os.environ.copy()
    if lib_dir.exists():
        existing_ld = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{lib_dir}:{existing_ld}" if existing_ld else str(lib_dir)

    try:
        # Run ldd with bundled lib path
        result = subprocess.run(["ldd", str(target_bin)], capture_output=True, text=True, env=env)
        if result.returncode != 0:
            return []
            
        # Parse output
        # Example line: "libzvbi.so.0 => not found"
        for line in result.stdout.splitlines():
            if "not found" in line:
                # Extract lib name. Usually "   libname.so.X => not found"
                parts = line.split("=>")
                if len(parts) > 0:
                    lib = parts[0].strip()
                    if lib:
                        missing.append(lib)
                        
    except Exception:
        pass
    
    return missing

def is_flatpak_installed():
    return shutil.which("flatpak") is not None

def get_install_dir():
    return Path.home() / ".local" / "share" / "tes3mp"

def is_tes3mp_installed():
    """Checks if TES3MP binary exists in the local user folder."""
    exe = get_install_dir() / "tes3mp-browser"
    return exe.exists()

def is_tailscale_installed():
    return shutil.which("tailscale") is not None

def is_tailscale_running():
    if not is_tailscale_installed():
        return False
    try:
        # Check if the daemon is active via systemctl (systemd based distros)
        # Note: This might not work on all distros (like Alpine), but covers 99% of desktop Linux users.
        cmd = subprocess.run(["systemctl", "is-active", "tailscaled"], capture_output=True, text=True)
        return "active" in cmd.stdout
    except Exception:
        # Fallback check: try to ping tailscale socket or just assume if binary works
        try:
             res = subprocess.run(["tailscale", "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             return res.returncode == 0
        except Exception:
             return False

from .utils import load_stored_data_path

def check_data_files(project_root):
    # Check via the persistent config
    stored_path = load_stored_data_path()
    local_present = stored_path is not None and stored_path.exists()
    
    # Check the actual config file to see if it's already linked
    home = Path.home()
    # Check both Flatpak and standard config locations
    cfg_candidates = [
        home / ".var/app/org.tes3mp.TES3MP/config/openmw/openmw.cfg",
        home / ".config/openmw/openmw.cfg"
    ]
    
    config_linked = False
    
    for cfg in cfg_candidates:
        if cfg.exists():
            try:
                with open(cfg, 'r') as f:
                    content = f.read()
                    # We check for 'data=' and ensure it's not just the default
                    # A robust check is hard without parsing, but finding our repo path or just any custom data path is a good signal.
                    # For now, let's just check if it has a data= line that matches our local path if local path exists
                    if 'data="' in content:
                         config_linked = True
            except:
                pass
            
    return {
        "local_present": local_present,
        "config_linked": config_linked
    }

def is_port_free(port=25565):
    """
    Checks if the game port is currently in use by another process.
    Returns True if the port is FREE (good for starting server).
    Returns False if the port is TAKEN (bad for starting, good for joining).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False
