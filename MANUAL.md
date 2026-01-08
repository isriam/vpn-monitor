# VPN Monitor Manual

Complete documentation for VPN Monitor configuration, deployment, and troubleshooting.

## Configuration

### Required Environment Variables

Copy `.env.example` to `.env` and configure:

#### Email (Required for all notifications)

| Variable | Description | Example |
|----------|-------------|---------|
| `SMTP_USERNAME` | Email account username | `your_email@gmail.com` |
| `SMTP_PASSWORD` | Email account password/app password | `your_app_password` |
| `FROM_EMAIL` | Sender email address | `your_email@gmail.com` |

#### WireGuard Monitor

| Variable | Description | Example |
|----------|-------------|---------|
| `WG_API_KEY` | WireGuard Dashboard API key | `WuphoOM7MXGcTYjU0RCCXYvvt3uM-8AffhxaOnEI1LU` |
| `MONITORED_PEERS` | Comma-separated list of peer names | `Work Phone,Home PC` |

#### Tailscale Monitor

| Variable | Description | Example |
|----------|-------------|---------|
| `TAILSCALE_TAILNET` | Your Tailscale tailnet name | `example.com` |
| `TAILSCALE_API_KEY` | Tailscale API key | `tskey-api-xxx...` |
| `MONITORED_TAILSCALE_DEVICES` | Comma-separated device names | `laptop,phone,server` |
| `MONITORED_TAILSCALE_TAGS` | Comma-separated tags to monitor | `kids-devices,family` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WG_API_URL` | `http://localhost:10086/api` | WireGuard Dashboard API URL |
| `WG_CONFIG_NAME` | `wg0` | WireGuard configuration name |
| `SMTP_SERVER` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `TO_EMAILS` | `admin@example.com` | Comma-separated recipients |
| `MONITOR_ALL_PEERS` | `false` | Monitor all WireGuard peers |
| `MONITOR_ALL_TAILSCALE_DEVICES` | `false` | Monitor all Tailscale devices |
| `CHECK_INTERVAL` | `300` | Seconds between checks |
| `CONNECTION_TIMEOUT` | `10` | API request timeout |
| `MAX_RETRIES` | `3` | Maximum API retry attempts |
| `RETRY_DELAY` | `30` | Delay between retries |
| `HANDSHAKE_TIMEOUT` | `300` | Peer disconnect threshold |

## Email Provider Setup

### Gmail

1. Enable 2-factor authentication
2. Generate an [App Password](https://support.google.com/accounts/answer/185833)
3. Use the app password in `SMTP_PASSWORD`

### Other Providers

| Provider | SMTP Server | Port |
|----------|-------------|------|
| Gmail | smtp.gmail.com | 587 |
| Outlook | smtp-mail.outlook.com | 587 |
| Yahoo | smtp.mail.yahoo.com | 587 |

## Tailscale API Setup

1. Go to [Tailscale Admin Console](https://login.tailscale.com/admin/settings/keys)
2. Navigate to **Settings** > **Keys**
3. Click **Generate API key**
4. Add to `.env` as `TAILSCALE_API_KEY`

### Tag-Based Monitoring

Monitor groups of devices by tag instead of individual names:

```bash
# With or without "tag:" prefix
MONITORED_TAILSCALE_TAGS=kids-devices,family
MONITORED_TAILSCALE_TAGS=tag:kids-devices,tag:family
```

**Priority order:**
1. Specific devices (`MONITORED_TAILSCALE_DEVICES`)
2. Tags (`MONITORED_TAILSCALE_TAGS`)
3. All devices (`MONITOR_ALL_TAILSCALE_DEVICES=true`)

## Systemd Service Setup

### WireGuard Service

Create `/etc/systemd/system/vpn-monitor-wireguard.service`:

```ini
[Unit]
Description=VPN Monitor - WireGuard
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/vpn-monitor
ExecStart=/path/to/vpn-monitor/venv/bin/python /path/to/vpn-monitor/vpn_monitor.py wireguard
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/path/to/vpn-monitor

[Install]
WantedBy=multi-user.target
```

### Tailscale Service

Create `/etc/systemd/system/vpn-monitor-tailscale.service`:

```ini
[Unit]
Description=VPN Monitor - Tailscale
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/vpn-monitor
ExecStart=/path/to/vpn-monitor/venv/bin/python /path/to/vpn-monitor/vpn_monitor.py tailscale
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/path/to/vpn-monitor

[Install]
WantedBy=multi-user.target
```

### Service Commands

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable vpn-monitor-wireguard
sudo systemctl start vpn-monitor-wireguard

# Management
sudo systemctl status vpn-monitor-wireguard
sudo systemctl restart vpn-monitor-wireguard
sudo journalctl -u vpn-monitor-wireguard -f
```

## How It Works

1. **API Polling**: Regularly queries WireGuard Dashboard or Tailscale API
2. **Status Analysis**: Checks handshake timestamps or device online status
3. **Change Detection**: Tracks state to detect status changes
4. **Notifications**: Sends email only when status changes (no spam)

### WireGuard Logic

- Peer connected if last handshake < `HANDSHAKE_TIMEOUT` (default 5 min)
- Interface status checked separately
- Alerts after 3 consecutive API failures

### Tailscale Logic

- Device online if `connectedToControl` is true
- Supports filtering by device name or tag
- Alerts after 3 consecutive API failures

## Troubleshooting

### Common Issues

**"Missing required environment variables"**
- Ensure `.env` file exists with all required variables

**"API request failed"**
- Verify API URL and key are correct
- Check network connectivity

**"Failed to send email notification"**
- Verify SMTP settings and app passwords
- Test with `--test-email` flag

### Debug Mode

```bash
python vpn_monitor.py -d wg   # Debug WireGuard
python vpn_monitor.py -d ts   # Debug Tailscale
```

### Discover Devices

```bash
python vpn_monitor.py ts --config-test -v
```

Shows all device names and tags for configuration.

## API Compatibility

### WireGuard Dashboard API

```
GET /api/getWireguardConfigurationInfo?configurationName=wg0
Header: wg-dashboard-apikey: your_api_key
```

### Tailscale API

```
GET https://api.tailscale.com/api/v2/tailnet/{tailnet}/devices
Header: Authorization: Bearer {api_key}
```
