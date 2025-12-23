import shutil
import tarfile
import requests
import os
import stat
from rich.prompt import Prompt
from rich.panel import Panel
from .utils import console, save_data_path, load_stored_data_path
from .checks import get_install_dir

def download_file(url, target_path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(target_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)

def setup_client():
    console.print(Panel("[bold blue]Client Setup (Latest Release)[/bold blue]", expand=False))
    
    install_dir = get_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if installed
    if not (install_dir / "tes3mp-browser").exists():
        console.print("[yellow][*] Downloading TES3MP 0.8.1...[/yellow]")
        
        # Hardcoded 0.8.1 release for stability (and direct link ease)
        # Using a reliable mirror or github release
        url = "https://github.com/TES3MP/TES3MP/releases/download/tes3mp-0.8.1/tes3mp-GNU+Linux-x86_64-release-0.8.1-68954091c5-8472f82156.tar.gz"
        tar_path = install_dir / "tes3mp.tar.gz"
        
        try:
            download_file(url, tar_path)
            console.print("[green][+] Download complete. Extracting...[/green]")
            
            with tarfile.open(tar_path, "r:gz") as tar:
                # Extract stripping top level folder if possible, but standard extract is fine.
                # Usually it extracts into a folder like 'TES3MP-...'
                tar.extractall(path=install_dir)
                
            # Cleanup
            tar_path.unlink()
            
            # Move files up if they are in a subdir
            # The tarball usually contains a single folder named like 'tes3mp-GNU+Linux...'
            # We want contents directly in install_dir or known subdir.
            # Let's check subdirs
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
    
    if data_path and data_path.exists():
        console.print(f"[green][*] Using remembered data path: {data_path}[/green]")
    else:
        console.print("[yellow]We need to know where your Morrowind Data Files are located.[/yellow]")
        console.print("Common paths: ~/Games/Morrowind/Data Files")
        
        path_str = Prompt.ask("Enter full path to 'Data Files'")
        data_path = Path(path_str).expanduser().resolve()
        
        if not (data_path / "Morrowind.esm").exists():
             console.print("[bold red][!] Error: Could not find Morrowind.esm in that folder.[/bold red]")
             return
             
        save_data_path(data_path)

    # 3. Config Setup
    # TES3MP 0.8.1 stores config in ~/.config/openmw/openmw.cfg usually, OR inside the folder?
    # Actually, standalone binaries often look in their own folder or ~/.config/openmw.
    # Let's ensure ~/.config/openmw exists.
    cfg_dir = Path.home() / ".config" / "openmw"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "openmw.cfg"
    
    # If not exists, create minimal
    if not cfg_path.exists():
        console.print("[*] Creating new openmw.cfg header...")
        with open(cfg_path, 'w') as f:
            f.write("[General]\n")

    # 4. Inject Config
    console.print(f"[*] Updating config at: {cfg_path}")
    try:
        with open(cfg_path, 'r') as f:
            lines = f.readlines()
    except Exception:
        lines = []

    # Prepend data path if missing
    if not any(str(data_path) in l for l in lines):
        lines.insert(0, f'data="{data_path}"\n')
        console.print(f"[green][+] Added data path.[/green]")
    else:
        console.print(f"[yellow][*] Data path already present.[/yellow]")
        
    # Ensure ESMs
    content_added = False
    for esm in ["Morrowind.esm", "Tribunal.esm", "Bloodmoon.esm"]:
        if not any(f"content={esm}" in l for l in lines):
            lines.append(f"\ncontent={esm}")
            content_added = True
    
    if content_added:
        console.print(f"[green][+] Registered ESM files.[/green]")

    with open(cfg_path, 'w') as f:
        f.writelines(lines)
    
    # Make sure binaries are executable
    for binary in ["tes3mp-browser", "tes3mp-server", "tes3mp"]:
        bin_path = install_dir / binary
        if bin_path.exists():
             st = os.stat(bin_path)
             os.chmod(bin_path, st.st_mode | stat.S_IEXEC)

    console.print(f"[bold green][SUCCESS] Client setup complete! You can play now.[/bold green]")
