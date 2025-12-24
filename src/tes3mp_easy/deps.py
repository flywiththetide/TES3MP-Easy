"""
Server dependency checking and installation for TES3MP Easy.
Uses ldd to find missing shared libraries and offers to install them.
"""
import os
import subprocess
import shutil
from pathlib import Path
from rich.prompt import Confirm
from .utils import console


def check_server_dependencies(server_root=None, get_server_root_func=None):
    """
    Check and install required dependencies for the server.
    Uses ldd to find ALL missing shared libraries.
    
    Args:
        server_root: Path to server installation, or None to auto-detect
        get_server_root_func: Function to call to get server root if server_root is None
    """
    console.print("[cyan][*] Checking server dependencies...[/cyan]")
    
    # If we have the server installed, use ldd on the actual binary
    if server_root is None and get_server_root_func:
        server_root = get_server_root_func()
    
    missing_libs = []
    
    if server_root:
        server_bin = server_root / "tes3mp-server.x86_64"
        if server_bin.exists():
            try:
                # Use ldd to find missing libraries
                # Set LD_LIBRARY_PATH to include bundled libs
                lib_dir = server_root / "lib"
                env = os.environ.copy()
                if lib_dir.exists():
                    existing_ld = env.get("LD_LIBRARY_PATH", "")
                    env["LD_LIBRARY_PATH"] = f"{lib_dir}:{existing_ld}" if existing_ld else str(lib_dir)
                
                result = subprocess.run(["ldd", str(server_bin)], capture_output=True, text=True, env=env)
                
                for line in result.stdout.splitlines():
                    if "not found" in line:
                        lib_name = line.split("=>")[0].strip()
                        missing_libs.append(lib_name)
                        
            except Exception as e:
                console.print(f"[dim]Could not run ldd: {e}[/dim]")
    
    # Fallback: Check for commonly missing libraries via ldconfig
    if not missing_libs:
        try:
            result = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True)
            ldconfig_output = result.stdout
            
            # List of libraries the server commonly needs
            common_libs = ["libluajit", "libboost_system", "libboost_filesystem", 
                           "libboost_program_options", "libboost_iostreams"]
            
            for lib in common_libs:
                if lib not in ldconfig_output:
                    missing_libs.append(lib)
        except Exception:
            pass
    
    if not missing_libs:
        console.print("[green]✓ All dependencies satisfied[/green]")
        return True
    
    console.print(f"[yellow][!] Missing libraries: {', '.join(missing_libs)}[/yellow]")
    
    # Map library names to package names for common distros
    # Format: {lib_substring: {apt, yum/dnf, pacman, apk}}
    LIB_TO_PKG = {
        "libluajit": {"apt": "libluajit-5.1-2", "yum": "luajit", "pacman": "luajit", "apk": "luajit"},
        "libboost_system": {"apt": "libboost-system1.74.0", "yum": "boost-system", "pacman": "boost-libs", "apk": "boost-system"},
        "libboost_filesystem": {"apt": "libboost-filesystem1.74.0", "yum": "boost-filesystem", "pacman": "boost-libs", "apk": "boost-filesystem"},
        "libboost_program_options": {"apt": "libboost-program-options1.74.0", "yum": "boost-program-options", "pacman": "boost-libs", "apk": "boost"},
        "libboost_iostreams": {"apt": "libboost-iostreams1.74.0", "yum": "boost-iostreams", "pacman": "boost-libs", "apk": "boost-iostreams"},
    }
    
    # Determine package manager
    pkg_manager = None
    pkg_cmd = None
    if shutil.which("apt-get"):
        pkg_manager = "apt"
        pkg_cmd = ["sudo", "apt-get", "install", "-y"]
    elif shutil.which("dnf"):
        pkg_manager = "yum"  # Same packages as yum
        pkg_cmd = ["sudo", "dnf", "install", "-y"]
    elif shutil.which("yum"):
        pkg_manager = "yum"
        pkg_cmd = ["sudo", "yum", "install", "-y"]
    elif shutil.which("pacman"):
        pkg_manager = "pacman"
        pkg_cmd = ["sudo", "pacman", "-S", "--noconfirm"]
    elif shutil.which("apk"):
        pkg_manager = "apk"
        pkg_cmd = ["sudo", "apk", "add"]
    
    if not pkg_manager:
        console.print("[red][!] Unknown package manager. Please install these libraries manually:[/red]")
        for lib in missing_libs:
            console.print(f"  - {lib}")
        return False
    
    # Build package list
    packages_to_install = set()
    for lib in missing_libs:
        for lib_key, pkg_map in LIB_TO_PKG.items():
            if lib_key in lib:
                if pkg_manager in pkg_map:
                    packages_to_install.add(pkg_map[pkg_manager])
                break
    
    if not packages_to_install:
        console.print("[yellow]Could not map all libraries to packages. You may need to install manually.[/yellow]")
        return False
    
    console.print(f"[cyan]Packages to install: {', '.join(packages_to_install)}[/cyan]")
    
    if not Confirm.ask("Install missing dependencies now?"):
        return False
    
    try:
        # Update package cache for apt
        if pkg_manager == "apt":
            console.print("[cyan][*] Updating package cache...[/cyan]")
            subprocess.run(["sudo", "apt-get", "update"], check=False)
        
        # Install packages
        cmd = pkg_cmd + list(packages_to_install)
        console.print(f"[cyan][*] Running: {' '.join(cmd)}[/cyan]")
        subprocess.run(cmd, check=True)
        
        console.print("[green][+] Dependencies installed![/green]")
        return True
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red][!] Installation failed: {e}[/red]")
        return False
