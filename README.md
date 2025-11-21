## Quick Start

1. **Clone and setup:**
   ```bash
   git clone https://github.com/isriam/vpn-monitor.git
   cd vpn-monitor
   sudo bash setup.sh
   ```

2. **Configure:**
   ```bash
   cp .env.example .env
   nano .env  # Add your API keys and email settings
   ```

   Configure the services you want to monitor:
   - **WireGuard**: Set `WG_API_KEY` and `MONITORED_PEERS`
   - **Tailscale**: Set `TAILSCALE_API_KEY`, `TAILSCALE_TAILNET`, and device/tag monitoring options
   - **Both**: Configure both sets of variables

3. **Discover your device names (Tailscale users):**
   ```bash
   python3 tailscale_monitor.py --config-test -v
   ```

   This will show you:
   - All device names in your Tailscale network (use exact names in `MONITORED_TAILSCALE_DEVICES`)
   - Online/offline status of each device
   - Any tags assigned to devices (use in `MONITORED_TAILSCALE_TAGS`)

   Update your `.env` file with the exact device names shown.

4. **Create and start the service(s):**

   For WireGuard monitoring:
   ```bash
   # Create service file (see "Run as a Service" section for template)
   sudo systemctl start vpn-monitor-wireguard
   ```

   For Tailscale monitoring:
   ```bash
   # Create service file (see "Run as a Service" section for template)
   sudo systemctl start vpn-monitor-tailscale
   ```

That's it! The monitor will start checking your configured VPN connections and send email alerts when issues are detected. See the [Service Management](#service-management) section for detailed service setup instructions.

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

## Which Monitor Should I Use?

Choose the appropriate monitor based on your needs:

- **`combined_monitor.py`** (Recommended): Run both WireGuard and Tailscale monitoring simultaneously. This is ideal if you use both VPN services or want unified monitoring.

- **`wireguard_monitor.py`**: Monitor only WireGuard connections. Use this if you only have WireGuard infrastructure.

- **`tailscale_monitor.py`**: Monitor only Tailscale devices. Use this if you only use Tailscale networking.

The combined monitor can run both services independently, or just one if the other isn't configured. See the [Usage](#usage) section for command-line options.

## Requirements

- Python 3.6+
- For WireGuard: WireGuard Dashboard with API access
- For Tailscale: Tailscale account with API access
- SMTP email account (Gmail, Outlook, etc.)

## Installation

### Automated Setup (Optional)

The `setup.sh` script can help set up the Python environment, but you'll need to manually create the service files (see below).

1. **Clone the repository:**
   ```bash
   git clone https://github.com/isriam/vpn-monitor.git
   cd vpn-monitor
   ```

2. **Run the setup script (optional):**
   ```bash
   sudo bash setup.sh
   ```

   The setup script will:
   - Create a Python virtual environment
   - Install all dependencies
   - Set proper file permissions
   - Create a basic systemd service (combined monitor)

3. **Configure your settings:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

4. **Create service file(s) manually:**

   See the [Run as a Service](#run-as-a-service-systemd---manual-setup) section for service file templates for WireGuard and/or Tailscale monitoring.

### Manual Installation (Recommended)

This is the recommended approach for full control over your setup:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/isriam/vpn-monitor.git
   cd vpn-monitor
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
| `MONITORED_TAILSCALE_TAGS` | Comma-separated list of tags to monitor (see Tag-Based Monitoring below) | `kids-devices,family` or `tag:kids-devices,tag:family` |

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

To find device names and tags for monitoring:
```bash
# Run config test to see all available devices and their tags
python3 tailscale_monitor.py --config-test -v
```

#### Tag-Based Monitoring

Tailscale allows you to organize devices using tags. You can monitor groups of devices by specifying tags instead of individual device names:

**Setting Up Tags in Tailscale:**
1. Go to your [Tailscale Admin Console](https://login.tailscale.com/admin/machines)
2. Select a device
3. Click on the tags section and add tags (e.g., `tag:kids-devices`, `tag:family`)

**Configuring Tag Monitoring:**

In your `.env` file, you can specify tags in two formats:
```bash
# With "tag:" prefix (exact format from Tailscale)
MONITORED_TAILSCALE_TAGS=tag:kids-devices,tag:family

# Or without prefix (automatically added)
MONITORED_TAILSCALE_TAGS=kids-devices,family
```

**Monitoring Priority:**
1. **Specific devices** (highest priority) - If `MONITORED_TAILSCALE_DEVICES` is set, only those devices are monitored
2. **Tags** - If `MONITORED_TAILSCALE_TAGS` is set and no specific devices configured, all devices with matching tags are monitored
3. **All devices** - If `MONITOR_ALL_TAILSCALE_DEVICES=true` and no specific devices or tags configured, all devices are monitored

**Example Scenarios:**
```bash
# Monitor only children's devices by tag
MONITORED_TAILSCALE_TAGS=kids-devices

# Monitor multiple groups
MONITORED_TAILSCALE_TAGS=kids-devices,family,iot-devices

# Monitor specific devices (ignores tags)
MONITORED_TAILSCALE_DEVICES=laptop,phone
MONITORED_TAILSCALE_TAGS=kids-devices  # This is ignored
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

The VPN monitor can be run as two separate systemd services:
- `vpn-monitor-wireguard` - Monitors WireGuard connections
- `vpn-monitor-tailscale` - Monitors Tailscale devices

You can run one or both services depending on your needs. Both services share the same `.env` configuration file.

#### WireGuard Service Commands

```bash
# Start the service
sudo systemctl start vpn-monitor-wireguard

# Stop the service
sudo systemctl stop vpn-monitor-wireguard

# Restart the service
sudo systemctl restart vpn-monitor-wireguard

# Check service status
sudo systemctl status vpn-monitor-wireguard

# View live logs
sudo journalctl -u vpn-monitor-wireguard -f

# Enable auto-start on boot
sudo systemctl enable vpn-monitor-wireguard

# Disable auto-start on boot
sudo systemctl disable vpn-monitor-wireguard
```

#### Tailscale Service Commands

```bash
# Start the service
sudo systemctl start vpn-monitor-tailscale

# Stop the service
sudo systemctl stop vpn-monitor-tailscale

# Restart the service
sudo systemctl restart vpn-monitor-tailscale

# Check service status
sudo systemctl status vpn-monitor-tailscale

# View live logs
sudo journalctl -u vpn-monitor-tailscale -f

# Enable auto-start on boot
sudo systemctl enable vpn-monitor-tailscale

# Disable auto-start on boot
sudo systemctl disable vpn-monitor-tailscale
```

### Run as a Service (systemd) - Manual Setup

You can create separate services for WireGuard and Tailscale monitoring. This allows you to independently enable/disable each based on what you use.

#### WireGuard Monitoring Service

1. **Create service file:**
   ```bash
   sudo nano /etc/systemd/system/vpn-monitor-wireguard.service
   ```

2. **Add service configuration:**
   ```ini
   [Unit]
   Description=VPN Monitor - WireGuard
   After=network.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=your_username
   WorkingDirectory=/path/to/vpn-monitor
   ExecStart=/path/to/vpn-monitor/venv/bin/python /path/to/vpn-monitor/wireguard_monitor.py
   Restart=always
   RestartSec=10
   StandardOutput=journal
   StandardError=journal

   # Security settings
   NoNewPrivileges=true
   PrivateTmp=true
   ProtectSystem=strict
   ProtectHome=true
   ReadWritePaths=/path/to/vpn-monitor

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vpn-monitor-wireguard
   sudo systemctl start vpn-monitor-wireguard
   ```

#### Tailscale Monitoring Service

1. **Create service file:**
   ```bash
   sudo nano /etc/systemd/system/vpn-monitor-tailscale.service
   ```

2. **Add service configuration:**
   ```ini
   [Unit]
   Description=VPN Monitor - Tailscale
   After=network.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=your_username
   WorkingDirectory=/path/to/vpn-monitor
   ExecStart=/path/to/vpn-monitor/venv/bin/python /path/to/vpn-monitor/tailscale_monitor.py
   Restart=always
   RestartSec=10
   StandardOutput=journal
   StandardError=journal

   # Security settings
   NoNewPrivileges=true
   PrivateTmp=true
   ProtectSystem=strict
   ProtectHome=true
   ReadWritePaths=/path/to/vpn-monitor

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vpn-monitor-tailscale
   sudo systemctl start vpn-monitor-tailscale
   ```

**Note:** You can enable both services, just one, or neither depending on your needs. Each service monitors independently and shares the same `.env` configuration file.

### Run with Screen (Alternative)

If you don't want to use systemd services, you can run the monitors in screen sessions:

```bash
# For WireGuard monitoring
screen -S vpn-monitor-wireguard
python3 wireguard_monitor.py
# Press Ctrl+A then D to detach

# For Tailscale monitoring
screen -S vpn-monitor-tailscale
python3 tailscale_monitor.py
# Press Ctrl+A then D to detach

# Or run both together
screen -S vpn-monitor-combined
python3 combined_monitor.py
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