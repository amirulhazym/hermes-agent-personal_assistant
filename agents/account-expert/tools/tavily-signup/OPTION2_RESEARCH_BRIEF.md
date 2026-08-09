# OPTION 2: Hermes Agent on Windows PC — Research Brief

## Purpose

Enable remote browser automation from VPS → Windows PC on-demand. PC is NOT always-on (user uses phone hotspot). Only active when user explicitly turns on PC.

## Architecture Goal

```
VPS (Hermes Primary, 24/7)
  ↓ delegate tasks (when PC is on)
Windows PC (Hermes Secondary, on-demand)
  → Local browser automation (Playwright/Computer Use)
  → Return results to VPS
  → Auto-shutdown after tasks complete
```

## Research Questions

### 1. Installation
- How to install Hermes Agent on Windows 11?
- What are the prerequisites (Python, Node.js, etc.)?
- Is there a Windows-specific installer?
- Can it run alongside existing software?

### 2. On-Demand Operation
- Can Hermes run as a service that starts/stops on demand?
- Or must it run as a foreground process?
- How to start Hermes remotely (e.g., from phone)?
- How to auto-shutdown after tasks complete?

### 3. Delegation from VPS
- How can VPS Hermes delegate tasks to PC Hermes?
- Is there a built-in delegation mechanism?
- Or do we need custom solution (SSH, API, message queue)?

### 4. Browser Automation
- Does Computer Use work on Windows?
- What browsers are supported (Brave, Edge, Chrome)?
- Can it control existing browser sessions?
- How to handle user interaction (captchas, etc.)?

### 5. Networking
- PC uses phone hotspot (NAT, no public IP)
- How can VPS reach PC?
  - Reverse SSH tunnel?
  - Tailscale/ZeroTier VPN?
  - Cloudflare Tunnel?
  - Message-based (Telegram/Discord as relay)?

### 6. Power Management
- Can Hermes trigger auto-shutdown after tasks?
- How to prevent PC from sleeping during tasks?
- How to handle task queue when PC is off?

### 7. Limitations
- What tasks can PC Hermes do that VPS cannot?
- What are the latency implications?
- How to handle PC going offline mid-task?

## Constraints

- PC NOT always-on (user's constraint)
- Phone hotspot = unreliable for 24/7
- VPS handles all 24/7 tasks
- PC handles burst automation only (e.g., "run 7 Tavily signups")
- User should be able to start/stop PC Hermes from phone

## Expected Output

- Step-by-step installation guide
- Architecture diagram
- Delegation mechanism options (ranked by feasibility)
- Known limitations and workarounds
- Recommended approach with rationale
