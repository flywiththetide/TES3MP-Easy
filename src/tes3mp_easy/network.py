import subprocess
import socket
import platform
import shutil
from rich.console import Console
from rich.panel import Panel

console = Console()

def get_local_ip():
    """Gets the local Tailscale IP if available, otherwise LAN IP."""
    # Try getting tailscale IP first
    try:
        if shutil.which("tailscale"):
            cmd = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True)
            if cmd.returncode == 0:
                return cmd.stdout.strip()
    except Exception:
        pass
    
    # Fallback to standard socket method
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def test_peer_connection(target_ip):
    """
    Runs a diagnostic battery against a target IP.
    1. Standard ICMP Ping
    2. Tailscale Tunnel Ping (DISCO)
    """
    console.print(f"\n[bold blue]--- Diagnostic: Connecting to {target_ip} ---[/bold blue]")

    # --- Test 1: Basic Reachability (ICMP) ---
    console.print("[dim]Step 1: Standard Ping...[/dim]", end=" ")
    # Windows uses -n, Linux/Mac uses -c
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', target_ip]
    
    icmp_success = False
    try:
        subprocess.check_call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        console.print("[green]✅ Success[/green]")
        icmp_success = True
    except subprocess.CalledProcessError:
        console.print("[red]❌ Failed (Request Timed Out)[/red]")

    # --- Test 2: Tailscale Mesh Ping ---
    # This is superior because it tests the actual P2P tunnel
    ts_success = False
    # Heuristic check to see if it looks like a Tailscale IP (100.x or fd7a:)
    is_ts_ip = target_ip.startswith("100.") or target_ip.startswith("fd7a:")
    
    if is_ts_ip:
        console.print("[dim]Step 2: Tailscale Tunnel Test...[/dim]", end=" ")
        if shutil.which("tailscale"):
            try:
                # 'tailscale ping' tests the encrypted path (DERP vs Direct)
                # We use a 5-second timeout because establishing a tunnel takes a moment
                cmd = subprocess.run(["tailscale", "ping", "--timeout=5s", "--c=1", target_ip], 
                                   capture_output=True, text=True)
                
                if cmd.returncode == 0:
                    console.print("[green]✅ Tunnel Active[/green]")
                    # We can even tell the user HOW they are connected (Direct vs Relay)
                    if "via DERP" in cmd.stdout:
                        console.print("   [yellow]⚠️  Note: Connection is relayed (slower). Combat might lag.[/yellow]")
                    else:
                        console.print("   [green]✨ Connection is Direct (Fast).[/green]")
                    ts_success = True
                else:
                    console.print(f"[red]❌ Tunnel Broken[/red]")
                    if cmd.stderr:
                        console.print(f"[dim]{cmd.stderr.strip()}[/dim]")
            except Exception as e:
                console.print(f"[red]Error running tailscale: {e}[/red]")
        else:
            console.print("[yellow]⚠️  Tailscale CLI not found. Skipping.[/yellow]")
    else:
        console.print("[dim]Step 2: Skipped (Not a Tailscale IP)[/dim]")
    
    # --- Summary ---
    verdict_text = get_verdict(icmp_success, ts_success, is_ts_ip)
    
    console.print(Panel(f"""
[bold]Diagnostic Results for {target_ip}[/bold]

1. [bold]Ping Reachability:[/bold] {"[green]PASS[/green]" if icmp_success else "[red]FAIL[/red]"}
2. [bold]Tailscale Tunnel:[/bold]  {"[green]PASS[/green]" if ts_success else ("[dim]N/A[/dim]" if not is_ts_ip else "[red]FAIL[/red]")}

[bold]Verdict:[/bold]
{verdict_text}
    """, title="Connection Doctor", border_style="cyan"))

def get_verdict(icmp, ts, is_ts_target):
    if ts:
        return "[green]SYSTEM GREEN.[/green] You can connect. If the game still fails, check the Server Password or Port 25565."
    if icmp and not ts and is_ts_target:
        return "[yellow]CAUTION.[/yellow] We can see them via ping, but the Tailscale tunnel isn't verified. Check if their Tailscale is online."
    if icmp and not is_ts_target:
         return "[green]LAN CONNECTION.[/green] Setup looks good for local play."
    return "[red]CRITICAL FAIL.[/red] Computer cannot see the target. \n1. Is their computer on?\n2. Is their Tailscale 'Last Seen' green?\n3. Are you both connected to the internet?"
