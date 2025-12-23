# 🌐 Networking with Tailscale

The easiest way to play TES3MP is using **Tailscale**.
It creates a "virtual LAN" over the internet.

## Why use it?
- **No Port Forwarding:** You do not need to log into your router.
- **Secure:** Only people you invite can join.
- **Easy:** Works on Linux, Windows, Mac, Android.

## Step-by-Step

### 1. Host Setup
1. Install: `curl -fsSL https://tailscale.com/install.sh | sh`
2. Start: `sudo tailscale up`
3. Launch your TES3MP Server.
4. Find your IP: Run `tailscale ip` (e.g., `100.50.20.1`)

### 2. Client Setup (Your Friend)
1. Install Tailscale (Same command).
2. Start: `sudo tailscale up`
3. Launch TES3MP Client.
4. Click **Direct Connect**.
5. Enter **Host's Tailscale IP** and Port `25565`.

## Alternative: Linode / VPS
If you want a 24/7 server, you can rent a small Linux server ($5/month).
1. SSH into the server.
2. Clone this repo.
3. Run `./setup.sh` -> Choose "Setup Server".
4. You **must** open the firewall port:
   ```bash
   ufw allow 25565/udp
   ```
