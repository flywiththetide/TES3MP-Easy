# 🔧 Troubleshooting Guide

## Common Issues

### 1. "Config not found"
**Symptom:** The script says it can't find `openmw.cfg`.
**Cause:** Flatpak OpenMW only generates config files after the first run.
**Fix:** 
1. Run `flatpak run org.tes3mp.TES3MP` in your terminal.
2. Wait for the launcher/window to appear.
3. Close it.
4. Run `./setup.sh` again.

### 2. "Morrowind.esm not found"
**Symptom:** The script rejects your Data Files folder.
**Cause:** You might be selecting the parent folder (e.g., `Morrowind`) instead of the subfolder `Data Files`.
**Fix:** Ensure you start the script pointing explicitly to the folder that contains `.esm` files. Or, just put them in the `data_files_here` folder in this repository.

### 3. No Audio on Linux
**Symptom:** Game runs but has no sound.
**Fix:** Linux Flatpaks sometimes lack the FFMPEG plugin. Run this:
```bash
flatpak install org.freedesktop.Platform.ffmpeg-full
```

### 4. Connection Failed
**Checklist:**
- Are both you and the host running `sudo tailscale up`?
- Did you use the **Tailscale IP** (starts with `100.x`), not the local IP (`192.168.x`)?
- Is the server actually running?
