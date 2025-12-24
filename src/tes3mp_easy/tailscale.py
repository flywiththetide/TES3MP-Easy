"""
Tailscale integration for TES3MP Easy.
Handles Tailscale installation, startup, and network management.
"""
import subprocess
import shutil
import time
from pathlib import Path
from rich.panel import Panel
from rich.prompt import Confirm
from .utils import console

# Default server port for reference in invite messages
SERVER_PORT = 25565


def get_tailscale_socket():
    """Get the tailscale socket path (handles userspace mode)."""
    custom_socket = Path.home() / ".tailscale" / "tailscaled.sock"
    if custom_socket.exists():
        return str(custom_socket)
    return None


def get_tailscale_ip():
    """Get the user's Tailscale IP address."""
    socket_path = get_tailscale_socket()
    
    # Try with custom socket first (userspace mode)
    if socket_path:
        try:
            result = subprocess.run(
                ["tailscale", "--socket", socket_path, "ip", "-4"], 
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
    
    # Try default socket
    try:
        result = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    
    return None


def is_tailscale_running():
    """Check if Tailscale daemon is running."""
    socket_path = get_tailscale_socket()
    
    # Try with custom socket first (userspace mode)
    if socket_path:
        try:
            result = subprocess.run(
                ["tailscale", "--socket", socket_path, "status"], 
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
    
    # Try default socket
    try:
        result = subprocess.run(["tailscale", "status"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def install_tailscale():
    """Offer to install Tailscale if not present."""
    console.print(Panel("[bold blue]Install Tailscale[/bold blue]", expand=False))
    console.print("[yellow]Tailscale provides secure private networking for your server.[/yellow]")
    console.print("[dim]This is optional - you can use public IP instead.[/dim]\n")
    
    if not Confirm.ask("Install Tailscale now?"):
        return False
    
    console.print("[cyan][*] Installing Tailscale...[/cyan]")
    try:
        # Use the official install script
        subprocess.run(
            "curl -fsSL https://tailscale.com/install.sh | sh",
            shell=True, check=True
        )
        console.print("[green][+] Tailscale installed![/green]")
        console.print("[yellow]Run 'sudo tailscale up' to connect.[/yellow]")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red][!] Installation failed: {e}[/red]")
        console.print("[dim]Try manually: curl -fsSL https://tailscale.com/install.sh | sh[/dim]")
        return False


def start_tailscale():
    """Start Tailscale if it's not running."""
    if is_tailscale_running():
        return True
    
    # Check if Tailscale is even installed
    if not shutil.which("tailscale"):
        console.print("[yellow][*] Tailscale is not installed.[/yellow]")
        if Confirm.ask("Install Tailscale now?"):
            install_tailscale()
        return False
        
    console.print("[yellow][*] Tailscale is not running.[/yellow]")
    
    if Confirm.ask("Start Tailscale now?"):
        # Check if systemd is available
        has_systemd = False
        try:
            result = subprocess.run(["systemctl", "is-system-running"], capture_output=True, text=True)
            has_systemd = result.returncode == 0 or "running" in result.stdout
        except Exception:
            pass
        
        try:
            if has_systemd:
                # Systemd is available - use systemctl
                console.print("[cyan][*] Starting Tailscale via systemd...[/cyan]")
                subprocess.run(["sudo", "systemctl", "start", "tailscaled"], check=True)
                subprocess.run(["sudo", "tailscale", "up"], check=True)
                console.print("[green][+] Tailscale started![/green]")
                return True
            else:
                # Non-systemd environment (Docker, Cloud Shell, Colab, etc.)
                console.print("[yellow][*] Systemd not available. Starting tailscaled directly...[/yellow]")
                
                # Check if tailscaled is already running
                try:
                    subprocess.run(["pgrep", "-x", "tailscaled"], check=True, capture_output=True)
                    console.print("[dim]tailscaled already running[/dim]")
                except subprocess.CalledProcessError:
                    # Start tailscaled in background with userspace networking (for containers)
                    console.print("[cyan][*] Starting tailscaled daemon...[/cyan]")
                    
                    # Use state directory that's writable
                    state_dir = Path.home() / ".tailscale"
                    state_dir.mkdir(exist_ok=True)
                    
                    # Start tailscaled with userspace networking for restricted environments
                    # nohup ensures it survives terminal close
                    cmd = f"nohup sudo tailscaled --state={state_dir}/tailscaled.state --socket={state_dir}/tailscaled.sock --tun=userspace-networking > {state_dir}/tailscaled.log 2>&1 &"
                    subprocess.run(cmd, shell=True)
                    
                    console.print("[dim]Waiting for tailscaled to start...[/dim]")
                    time.sleep(3)
                
                # Now bring up tailscale
                console.print("[cyan][*] Connecting to Tailscale network...[/cyan]")
                socket_path = Path.home() / ".tailscale" / "tailscaled.sock"
                
                if socket_path.exists():
                    subprocess.run(["sudo", "tailscale", "--socket", str(socket_path), "up"])
                else:
                    subprocess.run(["sudo", "tailscale", "up"])
                
                console.print("[green][+] Tailscale started![/green]")
                return True
                
        except subprocess.CalledProcessError as e:
            console.print(f"[red][!] Failed to start Tailscale: {e}[/red]")
            console.print("[dim]For non-systemd systems, try manually:[/dim]")
            console.print("[dim]  sudo tailscaled --tun=userspace-networking &[/dim]")
            console.print("[dim]  sudo tailscale up[/dim]")
            return False
    return False


def tailscale_invite(server_port=SERVER_PORT):
    """Generate Tailscale invite instructions for friends."""
    console.print(Panel("[bold blue]Invite Friends via Tailscale[/bold blue]", expand=False))
    
    # Check if Tailscale is running and get our IP
    ts_ip = get_tailscale_ip()
    if not ts_ip:
        console.print("[yellow]Tailscale is not running. Start it first![/yellow]")
        if Confirm.ask("Start Tailscale now?"):
            start_tailscale()
            ts_ip = get_tailscale_ip()
    
    if not ts_ip:
        console.print("[red]Could not get Tailscale IP. Please start Tailscale first.[/red]")
        return
    
    # Get machine info
    try:
        socket_path = get_tailscale_socket()
        if socket_path:
            result = subprocess.run(
                ["tailscale", "--socket", socket_path, "status", "--json"], 
                capture_output=True, text=True
            )
        else:
            result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True)
        import json
        status = json.loads(result.stdout)
        machine_name = status.get("Self", {}).get("HostName", "your-server")
        tailnet = status.get("MagicDNSSuffix", "")
    except Exception:
        machine_name = "your-server"
        tailnet = ""
    
    console.print(f"\n[green]Your server's Tailscale IP:[/green] [bold cyan]{ts_ip}[/bold cyan]")
    console.print(f"[green]Server name:[/green] [cyan]{machine_name}[/cyan]")
    if tailnet:
        console.print(f"[green]Tailnet:[/green] [cyan]{tailnet}[/cyan]")
    
    console.print("\n" + "="*60)
    console.print("[bold yellow]Option 1: Invite via Tailscale Admin Console (Recommended)[/bold yellow]")
    console.print("="*60)
    console.print("""
1. Go to: [link]https://login.tailscale.com/admin/users[/link]
2. Click \"Invite users\"
3. Enter your friend's email address
4. They'll get an email with instructions to join your network
""")
    
    console.print("="*60)
    console.print("[bold yellow]Option 2: Share Node (Quick Access)[/bold yellow]")
    console.print("="*60)
    
    # Try to enable node sharing
    try:
        # Check if funnel/share is available
        result = subprocess.run(["tailscale", "share", "--help"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("""
You can share this specific server with external users:
""")
            console.print(f"[cyan]tailscale share {machine_name}[/cyan]")
            console.print("\nThis allows users outside your Tailnet to connect temporarily.")
    except Exception:
        pass
    
    console.print("\n" + "="*60)
    console.print("[bold yellow]Option 3: Give Friends This Command[/bold yellow]")
    console.print("="*60)
    console.print("""
[bold]Your friends should run these commands:[/bold]
""")
    console.print("[cyan]# 1. Install Tailscale[/cyan]")
    console.print("curl -fsSL https://tailscale.com/install.sh | sh")
    console.print()
    console.print("[cyan]# 2. Connect to Tailscale (they'll need to be in your network)[/cyan]")
    console.print("sudo tailscale up")
    console.print()
    console.print("[cyan]# 3. Launch TES3MP and connect to:[/cyan]")
    console.print(f"[bold green]{ts_ip}:{server_port}[/bold green]")
    
    console.print("\n" + "="*60)
    console.print("[bold yellow]One-Liner for Friends:[/bold yellow]")
    console.print("="*60)
    oneliner = f"""
pip install tes3mp-easy && curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up
# Then connect to: {ts_ip}:{server_port}
"""
    console.print(f"[dim]{oneliner}[/dim]")
