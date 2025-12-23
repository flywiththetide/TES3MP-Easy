import os
import shutil
import urllib.request
import tarfile
import re
from pathlib import Path
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress
from .utils import console

# using 0.8.1
SERVER_URL = "https://github.com/TES3MP/TES3MP/releases/download/tes3mp-0.8.1/tes3mp-server-GNU+Linux-x86_64-release-0.8.1-68954091c5-6da3fdea59.tar.gz"
SERVER_DIR = Path.home() / "Games" / "TES3MP_Server"

def setup_server():
    console.print(Panel("[bold blue]Dedicated Server Setup[/bold blue]", expand=False))
    
    # 1. Download
    if not SERVER_DIR.exists():
        if not Prompt.ask(f"Install server to {SERVER_DIR}?", choices=["y", "n"]) == "y":
            return
            
        SERVER_DIR.mkdir(parents=True, exist_ok=True)
        tar_path = SERVER_DIR / "server.tar.gz"
        
        console.print("[cyan][*] Downloading Server binaries...[/cyan]")
        
        # Download with progress bar
        with Progress() as progress:
            task = progress.add_task("Downloading...", total=None)
            try:
                urllib.request.urlretrieve(SERVER_URL, tar_path)
                progress.update(task, completed=100, total=100)
            except Exception as e:
                console.print(f"[bold red][!] Download failed: {e}[/bold red]")
                return
        
        console.print("[*] Extracting...")
        with tarfile.open(tar_path) as tar:
            tar.extractall(path=SERVER_DIR)
        os.remove(tar_path)
    else:
        console.print(f"[yellow][*] Server directory {SERVER_DIR} already exists. checking config...[/yellow]")

    # 2. Configure
    # Find the dynamic inner folder
    server_root = next(SERVER_DIR.glob("TES3MP-Server*"), None)
    if not server_root:
        console.print("[bold red][!] Could not find extracted server folder.[/bold red]")
        return
        
    cfg_path = server_root / "tes3mp-server-default.cfg"
    if not cfg_path.exists():
        console.print("[bold red][!] Config file missing.[/bold red]")
        return

    name = Prompt.ask("Enter Server Name")
    password = Prompt.ask("Enter Password (leave empty for none)")

    with open(cfg_path, 'r') as f:
        cfg = f.read()

    if name:
        cfg = re.sub(r'hostname = ".*?"', f'hostname = "{name}"', cfg)
    if password:
        cfg = re.sub(r'password = ".*?"', f'password = "{password}"', cfg)

    with open(cfg_path, 'w') as f:
        f.write(cfg)
        
    console.print(f"\n[bold green][SUCCESS] Server configured![/bold green]")
    console.print(f"Run it here: [bold]{server_root}/tes3mp-server[/bold]")
