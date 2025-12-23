import subprocess
from pathlib import Path
from rich.prompt import Prompt
from rich.panel import Panel
from .utils import console, check_flatpak, get_project_root, save_data_path, load_stored_data_path

def setup_client():
    console.print(Panel("[bold blue]Client Setup (Flatpak)[/bold blue]", expand=False))
    
    if not check_flatpak():
        return

    # 1. Install Check - auto install if missing
    try:
        subprocess.run(["flatpak", "info", "org.tes3mp.TES3MP"], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError:
        console.print("[yellow][*] TES3MP Flatpak not found. Installing...[/yellow]")
        subprocess.run(["flatpak", "install", "flathub", "org.tes3mp.TES3MP", "-y"])

    # 2. Data Files Detection (Global Mode)
    # Check if we already know the path
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
             
        # Remember for next time
        save_data_path(data_path)

    # 3. Find Config
    home = Path.home()
    # Flatpak config locations
    cfg_candidates = [
        home / ".var/app/org.tes3mp.TES3MP/config/openmw/openmw.cfg",
        home / ".config/openmw/openmw.cfg"
    ]
    
    cfg_path = next((p for p in cfg_candidates if p.exists()), None)
    
    if not cfg_path:
        console.print("[yellow][!] Config file not found.[/yellow]")
        console.print("    Running the game launcher once to generate defaults...")
        console.print("    (Close the launcher window after it opens to continue)")
        try:
             # Run blindly, user has to close it. 
             # We use Popen so we don't necessarily block forever if they don't close, 
             # but strictly we need it to finish writing.
             # Actually, simpler to just ask user to do it.
             subprocess.run(["flatpak", "run", "org.tes3mp.TES3MP"], timeout=30)
        except Exception:
            pass
            
        # Try finding it again
        cfg_path = next((p for p in cfg_candidates if p.exists()), None)
        if not cfg_path:
            console.print("[bold red][!] Still could not find openmw.cfg. Aborting.[/bold red]")
            return

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
    
    console.print(f"[bold green][SUCCESS] Client setup complete! You can play now.[/bold green]")
