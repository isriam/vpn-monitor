## Quick Start

1. **Clone and setup:**
   ```bash
   git clone https://github.com/isriam/wireguard-monitor.git
   cd wireguard-monitor
   sudo bash setup.sh
   ```

2. **Configure:**
   ```bash
   cp .env.example .env
   nano .env  # Add your API key and email settings
   ```

3. **Start monitoring:**
   ```bash
   sudo systemctl start wireguard-monitor
   ```

That's it! The monitor will start checking your WireGuard connections and send email alerts when issues are detected.

# Network Connection Monitor

A Python suite that monitors VPN connections and sends email notifications when connections fail or recover. Supports both WireGuard (via WireGuard Dashboard API) and Tailscale (via Tailscale API).

## Features

### WireGuard Monitor
- **Real-time Monitoring**: Continuously monitors WireGuard interface and peer connection status
- **Email Notifications**: Sends alerts when peers disconnect, reconnect, or when the interface goes down
- **Robust Error Handling**: Includes retry logic for API failures and network issues
- **Smart Notifications**: Prevents spam by only sending alerts on status changes

### Tailscale Monitor
- **Device Monitoring**: Tracks online/offline status of Tailscale devices
- **API Integration**: Uses Tailscale API to check device status
- **Email Notifications**: Sends alerts when devices go offline or come back online
- **Flexible Configuration**: Monitor specific devices or all devices in your tailnet

### Combined Monitor
- **Unified Monitoring**: Run both WireGuard and Tailscale monitors simultaneously
- **Independent Operation**: Each monitor runs in its own thread
- **Flexible Execution**: Run both or just one monitor as needed

### Common Features
- **Comprehensive Logging**: Logs all activity to both console and file with different verbosity levels
- **Configurable**: All settings managed through environment variables
- **Multiple Execution Modes**: Normal operation, single check, config test, and debug modes

## Requirements

- Python 3.6+
- For WireGuard: WireGuard Dashboard with API access
- For Tailscale: Tailscale account with API access
- SMTP email account (Gmail, Outlook, etc.)

## Installation

### Automated Setup (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/isriam/wireguard-monitor.git
   cd wireguard-monitor
   ```

2. **Run the setup script:**
   ```bash
   sudo bash setup.sh
   ```

   The setup script will:
   - Create a Python virtual environment
   - Install all dependencies
   - Create a systemd service
   - Set proper file permissions
   - Optionally start the service

3. **Configure your settings:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

4. **Start the service:**
   ```bash
   sudo systemctl start wireguard-monitor
   ```

### Manual Installation

If you prefer to set up manually:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/isriam/wireguard-monitor.git
   cd wireguard-monitor
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

## Setup Script Details

The `setup.sh` script automates the entire installation process:

### What it does:
- ✅ Checks for Python 3 installation
- ✅ Creates an isolated Python virtual environment
- ✅ Installs all required dependencies
- ✅ Creates a systemd service file with proper security settings
- ✅ Sets correct file permissions
- ✅ Enables the service to start on boot
- ✅ Optionally starts the service immediately

### Security Features:
- Runs the service as a non-root user
- Implements systemd security restrictions
- Sets proper file permissions (600 for .env)
- Uses virtual environment isolation

### Requirements:
- Must be run with `sudo` (for systemd service creation)
- Python 3 with venv support
- systemd-based Linux distribution

If the setup script doesn't work for your system, you can follow the manual installation steps instead.

### Required Environment Variables

Copy `.env.example` to `.env` and configure the following required variables:

#### Common (Required for Email Notifications)
| Variable | Description | Example |
|----------|-------------|---------|
| `SMTP_USERNAME` | Email account username | `your_email@gmail.com` |
| `SMTP_PASSWORD` | Email account password/app password | `your_app_password` |
| `FROM_EMAIL` | Sender email address | `your_email@gmail.com` |

#### WireGuard Monitor (Required if using WireGuard)
| Variable | Description | Example |
|----------|-------------|---------|
| `WG_API_KEY` | WireGuard Dashboard API key | `WuphoOM7MXGcTYjU0RCCXYvvt3uM-8AffhxaOnEI1LU` |
| `MONITORED_PEERS` | Comma-separated list of peer names to monitor | `Work Phone,Home PC` |

#### Tailscale Monitor (Required if using Tailscale)
| Variable | Description | Example |
|----------|-------------|---------|
| `TAILSCALE_TAILNET` | Your Tailscale tailnet name | `example.com` or `user@domain.com` |
| `TAILSCALE_API_KEY` | Tailscale API key from admin console | `tskey-api-xxx...` |
| `MONITORED_TAILSCALE_DEVICES` | Comma-separated list of device names to monitor | `laptop,phone,server` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WG_API_URL` | `http://localhost:10086/api` | WireGuard Dashboard API URL |
| `WG_CONFIG_NAME` | `wg0` | WireGuard configuration name |
| `SMTP_SERVER` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `TO_EMAILS` | `admin@example.com` | Comma-separated list of recipients |
| `MONITOR_ALL_PEERS` | `false` | Monitor all WireGuard peers automatically (true/false) |
| `MONITOR_ALL_TAILSCALE_DEVICES` | `false` | Monitor all Tailscale devices automatically (true/false) |
| `CHECK_INTERVAL` | `300` | Time between checks (seconds) |
| `CONNECTION_TIMEOUT` | `10` | API request timeout (seconds) |
| `MAX_RETRIES` | `3` | Maximum API retry attempts |
| `RETRY_DELAY` | `30` | Delay between retries (seconds) |
| `HANDSHAKE_TIMEOUT` | `300` | Consider peer disconnected after this many seconds |

### Email Provider Setup

#### Gmail
1. Enable 2-factor authentication
2. Generate an [App Password](https://support.google.com/accounts/answer/185833)
3. Use the app password in `SMTP_PASSWORD`

#### Other Providers
Update `SMTP_SERVER` and `SMTP_PORT` for your provider:

| Provider | SMTP Server | Port | Security |
|----------|-------------|------|----------|
| Gmail | smtp.gmail.com | 587 | STARTTLS |
| Outlook | smtp-mail.outlook.com | 587 | STARTTLS |
| Yahoo | smtp.mail.yahoo.com | 587 | STARTTLS |
| Custom | your.smtp.server | 587/465 | STARTTLS/SSL |

### Tailscale API Setup

To use the Tailscale monitor, you need to generate an API key:

1. Go to the [Tailscale Admin Console](https://login.tailscale.com/admin/settings/keys)
2. Navigate to **Settings** → **Keys**
3. Click **Generate API key**
4. Give it a description (e.g., "Network Monitor")
5. Copy the key (it starts with `tskey-api-`)
6. Add it to your `.env` file as `TAILSCALE_API_KEY`

For `TAILSCALE_TAILNET`, use:
- Your tailnet domain (e.g., `example.com`)
- Or your email domain if using personal account (e.g., `user@domain.com`)

To find device names for monitoring:
```bash
# Run config test to see all available devices
python3 tailscale_monitor.py --config-test -v
```

## Usage

### WireGuard Monitor Only

#### Manual Execution (Virtual Environment)
```bash
source venv/bin/activate
python3 wireguard_monitor.py
```

#### Manual Execution (System Python)
```bash
python3 wireguard_monitor.py

# Examples:
python3 wireguard_monitor.py                    # Normal operation
python3 wireguard_monitor.py -v                 # Verbose output
python3 wireguard_monitor.py -d                 # Debug mode with detailed logging
python3 wireguard_monitor.py --test-email       # Test email configuration
python3 wireguard_monitor.py --check-once       # Single status check (no loop)
python3 wireguard_monitor.py --config-test      # Test configuration and API
```

### Tailscale Monitor Only

```bash
python3 tailscale_monitor.py

# Examples:
python3 tailscale_monitor.py                    # Normal operation
python3 tailscale_monitor.py -v                 # Verbose output
python3 tailscale_monitor.py -d                 # Debug mode
python3 tailscale_monitor.py --test-email       # Test email configuration
python3 tailscale_monitor.py --check-once       # Single status check
python3 tailscale_monitor.py --config-test      # Test configuration and API
```

### Combined Monitor (Both Services)

Monitor both WireGuard and Tailscale simultaneously:

```bash
python3 combined_monitor.py

# Examples:
python3 combined_monitor.py                     # Monitor both services
python3 combined_monitor.py --wireguard-only    # Monitor only WireGuard
python3 combined_monitor.py --tailscale-only    # Monitor only Tailscale
python3 combined_monitor.py -v                  # Verbose output
python3 combined_monitor.py -d                  # Debug mode
python3 combined_monitor.py --check-once        # Single check and exit
python3 combined_monitor.py --config-test       # Test both configurations
```

### Service Management

If you used the setup script, the monitor is installed as a systemd service:

```bash
# Start the service
sudo systemctl start wireguard-monitor

# Stop the service
sudo systemctl stop wireguard-monitor

# Restart the service
sudo systemctl restart wireguard-monitor

# Check service status
sudo systemctl status wireguard-monitor

# View live logs
sudo journalctl -u wireguard-monitor -f

# Enable auto-start on boot (done automatically by setup script)
sudo systemctl enable wireguard-monitor

# Disable auto-start on boot
sudo systemctl disable wireguard-monitor
```

### Run as a Service (systemd) - Manual Setup

If you didn't use the automated setup script, you can manually create the service:

1. **Create service file:**
   ```bash
   sudo nano /etc/systemd/system/wireguard-monitor.service
   ```

2. **Add service configuration:**
   ```ini
   [Unit]
   Description=WireGuard Connection Monitor
   After=network.target

   [Service]
   Type=simple
   User=your_username
   WorkingDirectory=/path/to/wireguard-monitor
   ExecStart=/path/to/wireguard-monitor/venv/bin/python /path/to/wireguard-monitor/wireguard_monitor.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable wireguard-monitor
   sudo systemctl start wireguard-monitor
   ```

### Run with Screen (Alternative)
```bash
screen -S wireguard-monitor
python3 wireguard_monitor.py
# Press Ctrl+A then D to detach
```

## How It Works

1. **API Monitoring**: The script regularly polls the WireGuard Dashboard API to get configuration and peer status
2. **Connection Analysis**: Checks interface status and analyzes peer handshake timestamps
3. **Status Tracking**: Maintains state to detect changes and avoid duplicate notifications
4. **Email Alerts**: Sends notifications when:
   - WireGuard interface goes down
   - Peers disconnect or reconnect
   - API becomes unavailable (after multiple failures)

## Monitoring Logic

- **Interface Status**: Checks if WireGuard interface is up/down
- **Peer Connections**: Considers a peer connected if their last handshake was within the configured timeout (default: 5 minutes)
- **API Failures**: Sends alerts after 3 consecutive API failures to detect monitoring issues

## Email Notifications

The script sends notifications for:

### Connection Issues
- Interface down
- Peer disconnections
- API unavailable

### Recovery Events
- Peer reconnections
- Interface restored

### Sample Email
```
Subject: WireGuard Peer(s) Disconnected - wg0

WireGuard peer(s) have disconnected from wg0.

Time: 2025-01-15 14:30:00
Disconnected peers: client-laptop

Current peer status:
  - client-laptop: Disconnected
  - client-phone: Connected
  - office-server: Connected
```

## Logging

Logs are written to both:
- **Console**: Real-time status information
- **File**: `wireguard_monitor.log` with detailed timestamps

Log levels:
- `INFO`: Normal operations and status checks
- `WARNING`: Connection issues and retries
- `ERROR`: API failures and configuration problems

## Troubleshooting

### Common Issues

#### "Missing required environment variables"
- Ensure `.env` file exists and contains all required variables
- Check for typos in variable names

#### "API request failed"
- Verify WireGuard Dashboard is running
- Check API URL and key are correct
- Ensure network connectivity

#### "Failed to send email notification"
- Verify SMTP settings are correct
- Check email credentials and app passwords
- Test with a simple email client first

#### "Invalid API response format"
- Check WireGuard Dashboard API version compatibility
- Verify the API endpoint returns expected JSON structure

### Debug Mode

Enable debug logging by modifying the script:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## API Compatibility

This script is designed for WireGuard Dashboard API. The expected API endpoint:
```
GET /api/getWireguardConfigurationInfo?configurationName=wg0
Header: wg-dashboard-apikey: your_api_key
```

Expected response format:
```json
{
  "data": {
    "status": "up",
    "peers": [
      {
        "name": "client-name",
        "latest_handshake": "2025-01-15T14:25:00Z"
      }
    ]
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review the log file for error details
3. Open an issue with:
   - Error messages
   - Relevant log entries
   - Your configuration (excluding sensitive data)

## Security Notes

- Store sensitive credentials in `.env` file (never commit to git)
- Use app passwords instead of regular passwords when possible
- Ensure `.env` is in your `.gitignore`
- Consider running the script with a dedicated service account