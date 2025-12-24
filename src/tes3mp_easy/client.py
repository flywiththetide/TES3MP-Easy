import re
import shutil
import tarfile
import requests
import os
import stat
from pathlib import Path
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from .utils import console, save_data_path, load_stored_data_path
from .checks import get_install_dir


def download_file(url, target_path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(target_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)


def update_openmw_configs(data_path):
    """
    Updates both standard and TES3MP openmw.cfg files.
    - Global config: Gets data path + content files + archives (Master list)
    - Local config: Gets data path + REMOVES content files (Slave list, inherits from Global)
    This prevents the "content files specified more than once" error.
    """
    install_dir = get_install_dir()
    
    global_cfg = Path.home() / ".config" / "openmw" / "openmw.cfg"
    local_cfg = install_dir / "openmw.cfg"
    
    # 1. Update Global Config (Master source of truth)
    _update_single_config(global_cfg, data_path, include_content=True)
    
    # 2. Update Local Config (Inherits from master)
    # We explicitly REMOVE content/archives from here to avoid duplication
    _update_single_config(local_cfg, data_path, include_content=False)


def _update_single_config(cfg_path, data_path, include_content=True):
    """Helper to update a single config file."""
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read existing content or create empty
    if cfg_path.exists():
        try:
            with open(cfg_path, 'r') as f:
                lines = f.readlines()
        except Exception:
            lines = []
    else:
        lines = []
    
    # IMPORTANT: Remove ALL existing data= lines, content= lines, and fallback-archive= lines for base files
    # Use regex to handle variable whitespace
    new_lines = []
    for line in lines:
        line_strip = line.strip()
        # Skip data lines
        if line_strip.startswith('data=') and not line_strip.startswith('data="?'):
            continue
        # Skip base content lines
        if re.match(r'^content\s*=\s*Morrowind\.esm', line_strip, re.IGNORECASE): continue
        if re.match(r'^content\s*=\s*Tribunal\.esm', line_strip, re.IGNORECASE): continue
        if re.match(r'^content\s*=\s*Bloodmoon\.esm', line_strip, re.IGNORECASE): continue
        # Skip base archive lines
        if re.match(r'^fallback-archive\s*=\s*Morrowind\.bsa', line_strip, re.IGNORECASE): continue
        if re.match(r'^fallback-archive\s*=\s*Tribunal\.bsa', line_strip, re.IGNORECASE): continue
        if re.match(r'^fallback-archive\s*=\s*Bloodmoon\.bsa', line_strip, re.IGNORECASE): continue
        
        new_lines.append(line)
    
    lines = new_lines
    
    # Build the header
    header_lines = [f'data="{data_path}"\n']
    
    if include_content:
        header_lines.extend([
            'content=Morrowind.esm\n',
            'content=Tribunal.esm\n',
            'content=Bloodmoon.esm\n',
            'fallback-archive=Morrowind.bsa\n',
            'fallback-archive=Tribunal.bsa\n',
            'fallback-archive=Bloodmoon.bsa\n',
        ])
    
    # Prepend header to remaining lines
    lines = header_lines + lines
    
    with open(cfg_path, 'w') as f:
        f.writelines(lines)
    
    console.print(f"[green][+] Updated {cfg_path.name} (Content: {include_content})[/green]")


def configure_data_path():
    """Prompts user to set the Morrowind Data Files path and updates all configs."""
    console.print(Panel("[bold blue]Configure Data Files[/bold blue]", expand=False))
    
    current_path = load_stored_data_path()
    if current_path:
        console.print(f"Current path: [cyan]{current_path}[/cyan]")
        if not Confirm.ask("Do you want to change it?"):
            return current_path

    console.print("[yellow]We need to know where your Morrowind Data Files are located.[/yellow]")
    console.print("Common paths: ~/Games/Morrowind/Data Files")
    
    while True:
        path_str = Prompt.ask("Enter full path to 'Data Files'")
        data_path = Path(path_str).expanduser().resolve()
        
        if (data_path / "Morrowind.esm").exists():
            # Save to our config file
            save_data_path(data_path)
            console.print(f"[green]✅ Path saved: {data_path}[/green]")
            
            # ALSO update the openmw.cfg files immediately
            update_openmw_configs(data_path)
            
            return data_path
        else:
            console.print("[bold red][!] Error: Could not find Morrowind.esm in that folder.[/bold red]")
            if not Confirm.ask("Try again?"):
                return None


def setup_client():
    console.print(Panel("[bold blue]Client Setup (Latest Release)[/bold blue]", expand=False))
    
    install_dir = get_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if installed
    if not (install_dir / "tes3mp-browser").exists():
        console.print("[yellow][*] Downloading TES3MP 0.8.1...[/yellow]")
        
        # Hardcoded 0.8.1 release for stability (and direct link ease)
        url = "https://github.com/TES3MP/TES3MP/releases/download/tes3mp-0.8.1/tes3mp-GNU+Linux-x86_64-release-0.8.1-68954091c5-6da3fdea59.tar.gz"
        tar_path = install_dir / "tes3mp.tar.gz"
        
        try:
            download_file(url, tar_path)
            console.print("[green][+] Download complete. Extracting...[/green]")
            
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=install_dir)
                
            # Cleanup
            tar_path.unlink()
            
            # Move files up if they are in a subdir
            subdirs = [d for d in install_dir.iterdir() if d.is_dir()]
            if len(subdirs) == 1:
                src_dir = subdirs[0]
                for item in src_dir.iterdir():
                    shutil.move(str(item), str(install_dir))
                src_dir.rmdir()

            console.print("[green][+] Installed successfully.[/green]")
        except Exception as e:
            console.print(f"[red][!] Installation failed: {e}[/red]")
            return
    else:
        console.print("[green][*] TES3MP is already installed.[/green]")

    # 2. Data Files Detection
    data_path = load_stored_data_path()
    if not data_path or not data_path.exists():
         data_path = configure_data_path()
         if not data_path:
             return
    else:
         console.print(f"[green][*] Using remembered data path: {data_path}[/green]")
         # Always update configs to ensure they're in sync
         update_openmw_configs(data_path)
    
    # Make sure binaries are executable
    for binary in ["tes3mp-browser", "tes3mp-server", "tes3mp"]:
        bin_path = install_dir / binary
        if bin_path.exists():
             st = os.stat(bin_path)
             os.chmod(bin_path, st.st_mode | stat.S_IEXEC)

    console.print(f"[bold green][SUCCESS] Client setup complete! You can play now.[/bold green]")
