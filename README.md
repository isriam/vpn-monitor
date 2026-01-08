# VPN Monitor

Monitor WireGuard and Tailscale VPN connections with email notifications when devices disconnect or reconnect.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/isriam/vpn-monitor.git
cd vpn-monitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Add your API keys and email settings

# Run
python vpn_monitor.py wireguard    # Monitor WireGuard
python vpn_monitor.py tailscale    # Monitor Tailscale
```

## Usage

```bash
python vpn_monitor.py wg              # Continuous WireGuard monitoring
python vpn_monitor.py ts              # Continuous Tailscale monitoring
python vpn_monitor.py wg --check-once # Single status check
python vpn_monitor.py ts --config-test # Test API connectivity
python vpn_monitor.py -v wg           # Verbose output
```

## Requirements

- Python 3.6+
- WireGuard Dashboard API access (for WireGuard monitoring)
- Tailscale API key (for Tailscale monitoring)
- SMTP email account for notifications

## Documentation

See [MANUAL.md](MANUAL.md) for detailed configuration, systemd setup, and troubleshooting.

## License

MIT License
