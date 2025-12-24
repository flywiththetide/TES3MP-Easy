"""
TES3MP Server management for TES3MP Easy.
Handles server installation, configuration, and startup.
"""
import os
import subprocess
import urllib.request
import tarfile
from pathlib import Path
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress
from rich.table import Table
from .utils import console

# Import from our modular files
from .tailscale import (
    get_tailscale_ip,
    is_tailscale_running,
    start_tailscale,
    tailscale_invite,
)
from .deps import check_server_dependencies

# Server configuration
SERVER_URL = "https://github.com/TES3MP/TES3MP/releases/download/tes3mp-0.8.1/tes3mp-server-GNU+Linux-x86_64-release-0.8.1-68954091c5-6da3fdea59.tar.gz"
SERVER_DIR = Path.home() / "Games" / "TES3MP_Server"
SERVER_PORT = 25565


def get_server_root():
    """Find the server installation folder."""
    if not SERVER_DIR.exists():
        return None
    for pattern in ["TES3MP-Server*", "TES3MP-server*", "tes3mp-server*"]:
        server_root = next(SERVER_DIR.glob(pattern), None)
        if server_root:
            return server_root
    return None


def install_server(interactive=True):
    """Download and extract the server binaries."""
    if SERVER_DIR.exists():
        console.print(f"[yellow][*] Server already installed at {SERVER_DIR}[/yellow]")
        server_root = get_server_root()
        # Check dependencies on existing install
        check_server_dependencies(server_root, get_server_root)
        return server_root
        
    if interactive:
        if not Confirm.ask(f"Install server to {SERVER_DIR}?"):
            return None
        
    SERVER_DIR.mkdir(parents=True, exist_ok=True)
    tar_path = SERVER_DIR / "server.tar.gz"
    
    console.print("[cyan][*] Downloading Server binaries...[/cyan]")
    
    with Progress() as progress:
        task = progress.add_task("Downloading...", total=None)
        try:
            urllib.request.urlretrieve(SERVER_URL, tar_path)
            progress.update(task, completed=100, total=100)
        except Exception as e:
            console.print(f"[bold red][!] Download failed: {e}[/bold red]")
            return None
    
    console.print("[*] Extracting...")
    with tarfile.open(tar_path) as tar:
        tar.extractall(path=SERVER_DIR)
    os.remove(tar_path)
    
    console.print("[green][+] Server installed![/green]")
    
    # Check dependencies AFTER installing (so ldd can work on the actual binary)
    server_root = get_server_root()
    if server_root:
        check_server_dependencies(server_root, get_server_root)
    
    return server_root


def configure_server(server_root, hostname=None, password=None):
    """Configure server name and password."""
    config_path = server_root / "tes3mp-server-default.cfg"
    if not config_path.exists():
        console.print("[red][!] Server config not found.[/red]")
        return
    
    console.print(Panel("[bold blue]Configure Server[/bold blue]", expand=False))
    
    # Read current config
    with open(config_path, 'r') as f:
        config = f.read()
    
    # Get new values
    current_name = "TES3MP Server"
    import re
    name_match = re.search(r'^hostname\s*=\s*(.+)$', config, re.MULTILINE)
    if name_match:
        current_name = name_match.group(1).strip()
    
    if hostname is None:
        new_name = Prompt.ask("Server name", default=current_name)
    else:
        new_name = hostname
        console.print(f"Server name: [cyan]{new_name}[/cyan]")
        
    if password is None:
        new_password = Prompt.ask("Server password (leave empty for none)", default="")
    else:
        new_password = password
        console.print(f"Server password: [cyan]******[/cyan]")
    
    # Update config
    config = re.sub(r'^hostname\s*=.*$', f'hostname = {new_name}', config, flags=re.MULTILINE)
    if new_password:
        # Enable and set password
        config = re.sub(r'^password\s*=.*$', f'password = {new_password}', config, flags=re.MULTILINE)
    else:
        # Clear password
        config = re.sub(r'^password\s*=.*$', 'password = ', config, flags=re.MULTILINE)
    
    with open(config_path, 'w') as f:
        f.write(config)
    
    console.print("[green][+] Server configured![/green]")


def install_systemd_service(server_root):
    """Generates and installs a systemd service for the server."""
    console.print(Panel("[bold blue]Install Systemd Service[/bold blue]", expand=False))
    
    if shutil.which("systemctl") is None:
        console.print("[red][!] Systemd (systemctl) not found on this system.[/red]")
        return False
        
    # Prepare service file content
    user = os.getlogin()
    service_content = f"""[Unit]
Description=TES3MP Server
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={server_root}
ExecStart={server_root}/tes3mp-server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    
    service_path = "/etc/systemd/system/tes3mp.service"
    
    try:
        # Write service file using sudo tee
        console.print(f"[cyan][*] Creating {service_path}...[/cyan]")
        subprocess.run(
            ["sudo", "tee", service_path],
            input=service_content.encode(),
            check=True,
            stdout=subprocess.DEVNULL
        )
        
        # Reload systemd
        console.print("[cyan][*] Reloading systemd daemon...[/cyan]")
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        
        # Enable service
        console.print("[cyan][*] Enabling tes3mp.service...[/cyan]")
        subprocess.run(["sudo", "systemctl", "enable", "tes3mp.service"], check=True)
        
        # Start service
        console.print("[cyan][*] Starting tes3mp.service...[/cyan]")
        subprocess.run(["sudo", "systemctl", "restart", "tes3mp.service"], check=True)
        
        console.print("[green][+] Service installed and running![/green]")
        console.print("[dim]Use 'sudo systemctl status tes3mp' to check status.[/dim]")
        return True
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red][!] Failed to install service: {e}[/red]")
        return False



def show_connection_info():
    """Display connection information for players."""
    ts_ip = get_tailscale_ip()
    
    console.print(Panel("[bold cyan]How to Connect[/bold cyan]", expand=False))
    
    table = Table(show_header=False, box=None)
    table.add_column("Label", style="bold")
    table.add_column("Value", style="green")
    
    if ts_ip:
        table.add_row("Tailscale IP:", ts_ip)
        table.add_row("Port:", str(SERVER_PORT))
        table.add_row("Full Address:", f"{ts_ip}:{SERVER_PORT}")
    else:
        table.add_row("Status:", "[red]Tailscale not running[/red]")
        
    console.print(table)
    console.print()
    
    if ts_ip:
        console.print("[bold]Share this with your friends:[/bold]")
        console.print(f"  [cyan]{ts_ip}:{SERVER_PORT}[/cyan]")
        console.print()
        console.print("[dim]Friends need:[/dim]")
        console.print("  1. TES3MP installed (pip install tes3mp-easy)")
        console.print("  2. Tailscale connected to your network")
        console.print("  3. Same Morrowind game files as you")


def start_server(server_root):
    """Start the server process."""
    server_bin = server_root / "tes3mp-server"
    
    if not server_bin.exists():
        console.print("[bold red][!] Server binary not found.[/bold red]")
        return
    
    # Offer to start Tailscale if not running
    start_tailscale()
    
    # Show connection info before starting
    show_connection_info()
    
    console.print("\n[bold green]Starting server...[/bold green]")
    console.print("[dim]Press Ctrl+C to stop the server[/dim]\n")
    
    try:
        # Set up environment to find libraries
        lib_dir = server_root / "lib"
        env = os.environ.copy()
        if lib_dir.exists():
            existing_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = f"{lib_dir}:{existing_ld}" if existing_ld else str(lib_dir)
        
        # Run server in foreground
        subprocess.run([str(server_bin)], cwd=server_root, env=env)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")


def configure_server_data():
    """Configure the path to game data files (ESM files for server)."""
    from .utils import save_data_path, load_stored_data_path
    
    console.print(Panel("[bold blue]Setup ESM Files[/bold blue]", expand=False))
    console.print("[dim]The server only needs the .esm files to enforce checksums.[/dim]")
    console.print("[dim]You don't need the full Morrowind install, just:[/dim]")
    console.print("  - Morrowind.esm")
    console.print("  - Tribunal.esm") 
    console.print("  - Bloodmoon.esm\n")
    
    current_path = load_stored_data_path()
    if current_path:
        console.print(f"[green]Current path:[/green] {current_path}")
        if not Confirm.ask("Change path?"):
            return current_path
    
    while True:
        path = Prompt.ask("Enter path containing ESM files")
        esm_path = Path(path).expanduser().resolve()
        
        if (esm_path / "Morrowind.esm").exists():
            save_data_path(esm_path)
            console.print(f"[green][+] ESM path saved: {esm_path}[/green]")
            return esm_path
        else:
            console.print("[bold red][!] Morrowind.esm not found in that folder.[/bold red]")
            if not Confirm.ask("Try again?"):
                return None


def get_public_ip():
    """Get the server's public IP address."""
    try:
        return urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode('utf8')
    except Exception:
        return None


def setup_server():
    """Main server menu."""
    console.print(Panel("[bold blue]Host a Server[/bold blue]", expand=False))
    
    # Ensure server is installed
    server_root = get_server_root()
    if not server_root:
        server_root = install_server()
        if not server_root:
            return
    
    while True:
        console.print()
        console.print("[bold]Server Menu:[/bold]")
        console.print("1. [green]Start Server[/green]")
        console.print("2. Show Connection Info")
        console.print("3. Configure (Name/Password)")
        console.print("4. Setup ESM Files")
        console.print("5. [magenta]Invite Friends (Tailscale)[/magenta]")
        console.print("6. Back to Main Menu")
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "6"])
        
        if choice == "1":
            start_server(server_root)
        elif choice == "2":
            show_connection_info()
            # Also show public IP
            public_ip = get_public_ip()
            if public_ip:
                console.print(f"\n[bold]Public IP:[/bold] [green]{public_ip}:{SERVER_PORT}[/green]")
                console.print("[dim]Use this if hosting on a VPS/cloud server[/dim]")
            Prompt.ask("\nPress Enter to continue")
        elif choice == "3":
            configure_server(server_root)
            Prompt.ask("\nPress Enter to continue")
        elif choice == "4":
            configure_server_data()
            Prompt.ask("\nPress Enter to continue")
        elif choice == "5":
            tailscale_invite(SERVER_PORT)
            Prompt.ask("\nPress Enter to continue")
        elif choice == "6":
            break
