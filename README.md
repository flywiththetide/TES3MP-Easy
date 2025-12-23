# 🐉 TES3MP Easy (openmw-multi)

**The "Easy Button" for playing Morrowind Multiplayer on Linux.**

A Python CLI tool that automates the installation, configuration, and network diagnostics for TES3MP (Morrowind via OpenMW).

[![PyPI version](https://badge.fury.io/py/tes3mp-easy.svg)](https://badge.fury.io/py/tes3mp-easy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features
* **Global Command:** `openmw-multi` works anywhere on your system.
* **Auto-Setup:** Installs Flatpak, detects the Engine, and links your Data Files automatically.
* **Smart Config:** Remembers your Data Files location forever (`~/.config/tes3mp-easy/`).
* **Connection Doctor:** Built-in network diagnostics for Ping and Tailscale tunnels.
* **Zombie Check:** Detects if a server process is stuck in the background ("Port 25565 In Use").

## 🚀 Installation

### Option A: The Easy Way (PyPI)
Install the latest stable version from the official Python Package Index:
```bash
pip install tes3mp-easy
```

### Option B: The Developer Way (GitHub)
Install the latest bleeding-edge version directly from source:
```bash
pip install git+https://github.com/YOUR_USERNAME/tes3mp-easy.git
```

## 🎮 How to Use
Once installed, simply type this in your terminal:
```bash
openmw-multi
```
The interactive menu will guide you through Setup, Server Hosting, and Diagnostics.

## 📂 Requirements
- **OS**: Linux (Ubuntu, Arch, Fedora, SteamOS, etc.)
- **Python**: 3.8 or higher.
- **Game Files**: You must own Morrowind and have the `Data Files` folder ready.
- **Engine**: System must support Flatpak (the tool can help you verify this).

## 🤝 Contributing
Found a bug?
1. Open an issue on [GitHub](https://github.com/YOUR_USERNAME/tes3mp-easy/issues).
2. Fork the repo and submit a PR.
