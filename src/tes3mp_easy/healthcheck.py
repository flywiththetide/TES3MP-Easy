"""
Health check functions for TES3MP Easy.
System status checks for both client and server modes.
"""
import sys
import shutil
import subprocess
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from .utils import console, clear_screen, get_project_root, load_stored_data_path
from . import checks


def run_system_check(interactive=False, setup_client_func=None):
    """
    Runs a visual pre-flight check of the system (client mode).
    
    Args:
        interactive: If True, pause for user input after check
        setup_client_func: Function to call for client setup if needed
    """
    while True:  # Loop until healthy or user bails
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

        # -- 3. System Dependencies --
        missing_deps = checks.check_dependencies()
        if not missing_deps:
            dep_status = "[green]✅ Ready[/green]"
            dep_action = ""
        else:
            dep_status = f"[red]❌ Missing: {', '.join(missing_deps)}[/red]"
            dep_action = "Install System Libs"
        table.add_row("System Deps", dep_status, dep_action)

        # -- 4. Data Files Check --
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

        # -- 5. Tailscale Check --
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

        # -- 6. Port Status Check --
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
        
        # Priority 0: Deps
        if missing_deps:
            console.print("[red bold]CRITICAL: Missing system libraries![/red bold]")
            console.print(f"Required: {', '.join(missing_deps)}")
            
            # Detect package manager
            install_cmd = None
            pkg_manager = None
            
            # Map library names to package names for common distros
            pkgs = []
            
            def add_if_missing(lib_substr, deb_pkg, rpm_pkg, arch_pkg):
                for m in missing_deps:
                    if lib_substr in m:
                        if shutil.which("apt-get"):
                            pkgs.append(deb_pkg)
                        elif shutil.which("dnf"):
                            pkgs.append(rpm_pkg)
                        elif shutil.which("pacman"):
                            pkgs.append(arch_pkg)
                        break

            # Add known dependencies
            add_if_missing("libzvbi", "libzvbi0", "zvbi", "zvbi")
            add_if_missing("libsnappy", "libsnappy1v5", "snappy", "snappy")
            add_if_missing("libgsm", "libgsm1", "gsm", "gsm")
            add_if_missing("libxml2", "libxml2", "libxml2", "libxml2")
            add_if_missing("libosg", "libopenscenegraph-dev", "OpenSceneGraph", "openscenegraph")
            add_if_missing("libOpenThreads", "libopenscenegraph-dev", "OpenSceneGraph", "openscenegraph")
            add_if_missing("libboost_system", "libboost-system-dev", "boost-system", "boost-libs")
            add_if_missing("libboost_filesystem", "libboost-filesystem-dev", "boost-filesystem", "boost-libs")
            add_if_missing("libboost_program_options", "libboost-program-options-dev", "boost-program-options", "boost-libs")
            add_if_missing("libboost_iostreams", "libboost-iostreams-dev", "boost-iostreams", "boost-libs")
            add_if_missing("libopenal", "libopenal1", "openal-soft", "openal")
            add_if_missing("libavcodec", "libavcodec-dev", "ffmpeg-libs", "ffmpeg")
            add_if_missing("libavformat", "libavformat-dev", "ffmpeg-libs", "ffmpeg")
            add_if_missing("libavutil", "libavutil-dev", "ffmpeg-libs", "ffmpeg")
            add_if_missing("libswscale", "libswscale-dev", "ffmpeg-libs", "ffmpeg")
            add_if_missing("libswresample", "libswresample-dev", "ffmpeg-libs", "ffmpeg")
            add_if_missing("libMyGUIEngine", "libmygui-dev", "mygui", "mygui")
            add_if_missing("libBullet", "libbullet-dev", "bullet", "bullet")
            add_if_missing("libLinearMath", "libbullet-dev", "bullet", "bullet")
            add_if_missing("libluajit", "libluajit-5.1-2", "luajit", "luajit")

            if shutil.which("apt-get"):
                pkg_manager = "apt"
                install_cmd = ["sudo", "apt-get", "install", "-y"] + pkgs
            elif shutil.which("dnf"):
                pkg_manager = "dnf"
                install_cmd = ["sudo", "dnf", "install", "-y"] + pkgs
            elif shutil.which("pacman"):
                pkg_manager = "pacman"
                install_cmd = ["sudo", "pacman", "-S", "--noconfirm"] + pkgs

            if install_cmd:
                console.print(f"[yellow]We can try to install these mostly automatically using {pkg_manager}.[/yellow]")
                if Confirm.ask("Install missing libraries now?"):
                    try:
                        subprocess.check_call(install_cmd)
                        console.print("[green]Installation successful! Re-checking...[/green]")
                        continue
                    except subprocess.CalledProcessError:
                        console.print("[red]Installation failed. Please install manually.[/red]")
            
            # Fallback manual instructions
            console.print("[yellow]For Debian/Ubuntu/Mint:[/yellow] sudo apt install libzvbi0")
            console.print("[yellow]For Fedora:[/yellow] sudo dnf install zvbi")
            console.print("[yellow]For Arch:[/yellow] sudo pacman -S zvbi")
            
            if not Confirm.ask("Continue anyway?", default=False):
                sys.exit(1)

        # Priority 1: Flatpak
        if not has_flatpak:
            console.print("[red]CRITICAL: Flatpak is required. Please install it with your distro's package manager.[/red]")
            sys.exit(1)

        # Priority 2: Engine
        if not has_engine and setup_client_func:
            if Confirm.ask("[bold yellow]TES3MP Engine is missing. Install it now?[/bold yellow]"):
                console.print("[dim]Running installation...[/dim]")
                setup_client_func() 
                continue  # Re-run checks
            else:
                console.print("[yellow]Warning: You cannot play without the engine.[/yellow]")

        # Priority 3: Data Linkage
        if not data_status["config_linked"] and data_status["local_present"] and setup_client_func:
            if Confirm.ask("[bold yellow]Data files found but not linked. Link them now?[/bold yellow]"):
                setup_client_func()
                continue

        # If we are here, everything is either good or user declined fixes.
        any_issues_remaining = not (has_engine and data_status["config_linked"])
        
        if interactive or any_issues_remaining:
            Prompt.ask("Press Enter to continue")

        break  # If we get here, pass-through to main menu


def run_server_check(get_server_root_func=None):
    """
    Runs a server-specific health check (no Flatpak or client requirements).
    
    Args:
        get_server_root_func: Function to get server root directory
        
    Returns:
        server_root path or None
    """
    clear_screen()
    console.print(Panel("[bold cyan]Server Status Check[/bold cyan]", expand=False))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="dim")
    table.add_column("Status")
    table.add_column("Notes")

    # -- 1. Server Binary Check --
    server_root = get_server_root_func() if get_server_root_func else None
    if server_root and (server_root / "tes3mp-server").exists():
        server_status = "[green]✅ Installed[/green]"
        server_notes = str(server_root)
    else:
        server_status = "[yellow]⚠️ Not Installed[/yellow]"
        server_notes = "Will install on first run"
    table.add_row("Server Binary", server_status, server_notes)

    # -- 2. ESM Files Check --
    esm_path = load_stored_data_path()
    if esm_path and (esm_path / "Morrowind.esm").exists():
        esm_status = "[green]✅ Found[/green]"
        esm_notes = str(esm_path)
    else:
        esm_status = "[yellow]⚠️ Not Set[/yellow]"
        esm_notes = "Configure in Server Menu"
    table.add_row("ESM Files", esm_status, esm_notes)

    # -- 3. Port Check --
    if checks.is_port_free(25565):
        port_status = "[green]✅ Free[/green]"
        port_notes = "Ready to host"
    else:
        port_status = "[yellow]⚠️ In Use[/yellow]"
        port_notes = "Another server running?"
    table.add_row("UDP Port 25565", port_status, port_notes)

    # -- 4. Public IP --
    try:
        import urllib.request
        public_ip = urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode('utf8')
        ip_status = f"[green]{public_ip}[/green]"
        ip_notes = "Share this with players"
    except Exception:
        ip_status = "[yellow]Unknown[/yellow]"
        ip_notes = "Could not detect"
    table.add_row("Public IP", ip_status, ip_notes)

    # -- 5. Tailscale (optional) --
    if checks.is_tailscale_installed():
        if checks.is_tailscale_running():
            ts_status = "[green]✅ Running[/green]"
            ts_notes = "Private network available"
        else:
            ts_status = "[yellow]Stopped[/yellow]"
            ts_notes = "Run: sudo tailscale up"
    else:
        ts_status = "[dim]Not Installed[/dim]"
        ts_notes = "Optional for private hosting"
    table.add_row("Tailscale", ts_status, ts_notes)

    console.print(table)
    console.print()
    return server_root
