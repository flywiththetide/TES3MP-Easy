import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from pathlib import Path
import subprocess

# Import our modules
from . import checks
from . import network
from .client import setup_client
from .server import setup_server
from .utils import clear_screen, get_project_root

console = Console()

def run_system_check():
    """Runs a visual pre-flight check of the system."""
    while True: # Loop until healthy or user bails
        clear_screen()
        console.print(Panel("[bold cyan]System Status Check[/bold cyan]", expand=False))
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="dim")
        table.add_column("Status")
        table.add_column("Action Needed", style="bold red")

        # -- 1. Flatpak Check --
        if checks.is_flatpak_installed():
            flatpak_status = "[green]✅ Installed[/green]"
            flatpak_action = ""
            has_flatpak = True
        else:
            flatpak_status = "[red]❌ Missing[/red]"
            flatpak_action = "Install Flatpak"
            has_flatpak = False
        table.add_row("Flatpak System", flatpak_status, flatpak_action)

        # -- 2. TES3MP Engine Check --
        if has_flatpak and checks.is_tes3mp_installed():
            engine_status = "[green]✅ Installed[/green]"
            engine_action = ""
            has_engine = True
        else:
            engine_status = "[red]❌ Missing[/red]"
            engine_action = "Run Client Setup" if has_flatpak else "Fix Flatpak First"
            has_engine = False
        table.add_row("TES3MP Engine", engine_status, engine_action)

        # -- 3. Data Files Check --
        data_status = checks.check_data_files(get_project_root())
        if data_status["config_linked"]:
            files_status = "[green]✅ Linked[/green]"
            files_action = ""
        elif data_status["local_present"]:
            files_status = "[yellow]⚠️ Found (Not Linked)[/yellow]"
            files_action = "Run Client Setup"
        else:
            files_status = "[red]❌ Missing[/red]"
            files_action = "Drop files in folder"
        table.add_row("Morrowind Data", files_status, files_action)

        # -- 4. Tailscale Check --
        if checks.is_tailscale_installed():
            ts_status = "[green]✅ Installed[/green]"
            if checks.is_tailscale_running():
                ts_status += " (Running)"
                ts_action = ""
            else:
                ts_status += " [yellow](Stopped)[/yellow]"
                ts_action = "Start Service"
        else:
            ts_status = "[red]❌ Missing[/red]"
            ts_action = "Install Tailscale"
        table.add_row("Tailscale Network", ts_status, ts_action)

        # -- 5. Port Status Check --
        if checks.is_port_free(25565):
            port_status = "[green]✅ Free[/green]"
            port_action = "Ready to Host"
        else:
            port_status = "[yellow]⚠️  In Use[/yellow]"
            port_action = "Server Running?"
        table.add_row("UDP Port 25565", port_status, port_action)

        console.print(table)
        console.print("\n")
        
        # --- Auto-Fix Logic ---
        
        # Priority 1: Flatpak
        if not has_flatpak:
            console.print("[red]CRITICAL: Flatpak is required. Please install it with your distro's package manager.[/red]")
            sys.exit(1)

        # Priority 2: Engine
        if not has_engine:
            if Confirm.ask("[bold yellow]TES3MP Engine is missing. Install it now?[/bold yellow]"):
                console.print("[dim]Running installation...[/dim]")
                setup_client() 
                continue # Re-run checks
            else:
                # User declined, stop nagging but warn
                console.print("[yellow]Warning: You cannot play without the engine.[/yellow]")

        # Priority 3: Data Linkage
        # If we found files but config isn't ready
        if not data_status["config_linked"] and data_status["local_present"]:
             if Confirm.ask("[bold yellow]Data files found but not linked. Link them now?[/bold yellow]"):
                 setup_client()
                 continue

        break # If we get here, pass-through to main menu

def main():
    # 1. Run the Health Check immediately on start
    run_system_check()
    
    # 2. Main Menu
    while True:
        clear_screen()
        console.print(Panel("[bold magenta]TES3MP Manager[/bold magenta]", subtitle="Ready to Play"))
        console.print("1. [bold]Launch Game[/bold] (Start Client)")
        console.print("2. [bold]Server Settings[/bold]")
        console.print("3. [bold]Connection Doctor[/bold] (Test Peer)")
        console.print("4. [bold]Re-run Health Check[/bold]")
        console.print("5. Exit")
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5"])
        
        if choice == "1":
            console.print("[green]Launching TES3MP...[/green]")
            try:
                subprocess.Popen(["flatpak", "run", "org.tes3mp.TES3MP"])
                time.sleep(2) # Give it a second to see any immediate errors
            except Exception as e:
                console.print(f"[red]Failed to launch: {e}[/red]")
                Prompt.ask("Press Enter to continue")
            sys.exit()
        elif choice == "2":
            setup_server()
            Prompt.ask("Press Enter to continue")
        elif choice == "3":
            console.print("\n[bold]Who are you trying to join?[/bold]")
            console.print("Enter their Tailscale IP (e.g., 100.101.50.5)")
            target = Prompt.ask("Target IP")
            network.test_peer_connection(target)
            Prompt.ask("\nPress Enter to return...")
        elif choice == "4":
            run_system_check()
        elif choice == "5":
            console.print("[green]Goodbye![/green]")
            sys.exit()

def tailscale_print():
    # Quick re-implementation of the guide
    console.print(Panel("""
[bold green]1. Install Tailscale[/bold green]
   curl -fsSL https://tailscale.com/install.sh | sh
   
[bold green]2. Connect[/bold green]
   sudo tailscale up

[bold green]3. Play[/bold green]
   Host IP: Run 'tailscale ip'
   Port: 25565
    """, title="Tailscale Guide", border_style="blue"))
    Prompt.ask("Press Enter to return")

if __name__ == "__main__":
    main()
