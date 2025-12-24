import sys
import time
import subprocess
import argparse
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

# Import our modules
from . import checks
from . import network
from .client import setup_client
from .server import setup_server, get_server_root, install_server, configure_server, install_systemd_service
from .healthcheck import run_system_check, run_server_check
from .utils import console, clear_screen, load_stored_data_path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="TES3MP Easy Setup Tool")
    parser.add_argument("--server", "-s", action="store_true", help="Run in dedicated server mode")
    parser.add_argument("--install", action="store_true", help="Auto-install dependencies/server (non-interactive)")
    parser.add_argument("--name", help="Set server hostname")
    parser.add_argument("--password", help="Set server password")
    parser.add_argument("--service", action="store_true", help="Install as systemd service")
    return parser.parse_args()


def server_main(args):
    """Entry point for dedicated server mode options."""
    # Check if we are running in headless automation mode
    headless = args.install or args.name is not None or args.password is not None or args.service
    
    if headless:
        console.print(Panel("[bold blue]TES3MP Server Automation[/bold blue]", subtitle="Headless Mode"))
        
        # 1. Install (skips prompt if interactive=False)
        # Note: --install implies we want to install if missing without asking
        server_root = install_server(interactive=not args.install)
        
        if not server_root:
            console.print("[red]Server installation failed or aborted.[/red]")
            sys.exit(1)
            
        # 2. Configure (if args provided)
        if args.name is not None or args.password is not None:
            configure_server(server_root, hostname=args.name, password=args.password)
            
        # 3. Service
        if args.service:
            if not install_systemd_service(server_root):
                sys.exit(1)
        
        console.print("[green]✓ Automation complete.[/green]")
        return

    # Classic Interactive Mode
    clear_screen()
    console.print(Panel("[bold blue]TES3MP Dedicated Server[/bold blue]", subtitle="Server Mode"))
    console.print("[dim]Running in server-only mode (no Flatpak/client required)[/dim]\n")
    
    run_server_check(get_server_root)
    Prompt.ask("Press Enter to continue to Server Menu")
    
    # Go directly to server setup menu
    setup_server()


def main():
    """Main entry point for TES3MP Easy."""
    args = parse_args()
    
    # Check for server-only mode (explicit flag or automation args)
    if args.server or args.install or args.name or args.password or args.service:
        server_main(args)
        return
    
    # 1. Auto-Clean Configs (Fixes "duplicate content files" error)
    data_path = load_stored_data_path()
    if data_path:
        from .client import update_openmw_configs
        update_openmw_configs(data_path)

    # 2. Run the Health Check immediately on start (silent if good)
    run_system_check(interactive=False, setup_client_func=setup_client)
    
    # 3. Main Menu
    while True:
        clear_screen()
        console.print(Panel("[bold magenta]TES3MP Manager[/bold magenta]", subtitle="Ready to Play"))
        console.print("1. [bold]Launch Game[/bold] (Start Client)")
        console.print("2. [bold]Server Settings[/bold]")
        console.print("3. [bold]Connection Doctor[/bold] (Test Peer)")
        console.print("4. [bold]Re-run Health Check[/bold]")
        console.print("5. [bold]Set Data Files Path[/bold]")
        console.print("6. Exit")
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "6"])
        
        if choice == "1":
            console.print("[green]Launching TES3MP...[/green]")
            try:
                exe = checks.get_install_dir() / "tes3mp-browser"
                # Set working directory to installation so it finds configs/resources
                subprocess.Popen([str(exe)], cwd=str(checks.get_install_dir()))
                time.sleep(2)
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
            run_system_check(interactive=True, setup_client_func=setup_client)
        elif choice == "5":
            from .client import configure_data_path
            configure_data_path()
            Prompt.ask("Press Enter to continue")
        elif choice == "6":
            console.print("[green]Goodbye![/green]")
            sys.exit()


def tailscale_print():
    """Quick Tailscale setup guide."""
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
