#!/usr/bin/env python3
"""
VPN Monitor - WireGuard and Tailscale connection monitoring with email alerts.

Monitors VPN connections via API and sends email notifications when status changes.
"""

import argparse
import json
import logging
import os
import re
import smtplib
import sys
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


# =============================================================================
# Configuration
# =============================================================================

def load_email_config() -> Dict[str, Any]:
    """Load email configuration from environment variables."""
    to_emails_str = os.getenv('TO_EMAILS', 'admin@example.com')
    to_emails = [email.strip() for email in to_emails_str.split(',')]

    return {
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_username': os.getenv('SMTP_USERNAME'),
        'smtp_password': os.getenv('SMTP_PASSWORD'),
        'from_email': os.getenv('FROM_EMAIL'),
        'to_emails': to_emails,
    }


def load_wireguard_config() -> Dict[str, Any]:
    """Load WireGuard configuration from environment variables."""
    monitored_peers_str = os.getenv('MONITORED_PEERS', '')
    monitored_peers = [p.strip() for p in monitored_peers_str.split(',') if p.strip()]

    return {
        'api_url': os.getenv('WG_API_URL', 'http://localhost:10086/api'),
        'api_key': os.getenv('WG_API_KEY'),
        'config_name': os.getenv('WG_CONFIG_NAME', 'wg0'),
        'check_interval': int(os.getenv('CHECK_INTERVAL', '300')),
        'connection_timeout': int(os.getenv('CONNECTION_TIMEOUT', '10')),
        'max_retries': int(os.getenv('MAX_RETRIES', '3')),
        'retry_delay': int(os.getenv('RETRY_DELAY', '30')),
        'handshake_timeout': int(os.getenv('HANDSHAKE_TIMEOUT', '300')),
        'monitored_peers': monitored_peers,
        'monitor_all_peers': os.getenv('MONITOR_ALL_PEERS', 'false').lower() == 'true',
        'email': load_email_config(),
    }


def load_tailscale_config() -> Dict[str, Any]:
    """Load Tailscale configuration from environment variables."""
    monitored_devices_str = os.getenv('MONITORED_TAILSCALE_DEVICES', '')
    monitored_devices = [d.strip() for d in monitored_devices_str.split(',') if d.strip()]

    monitored_tags_str = os.getenv('MONITORED_TAILSCALE_TAGS', '')
    monitored_tags = [t.strip() for t in monitored_tags_str.split(',') if t.strip()]

    return {
        'tailnet': os.getenv('TAILSCALE_TAILNET'),
        'api_key': os.getenv('TAILSCALE_API_KEY'),
        'check_interval': int(os.getenv('CHECK_INTERVAL', '300')),
        'connection_timeout': int(os.getenv('CONNECTION_TIMEOUT', '10')),
        'max_retries': int(os.getenv('MAX_RETRIES', '3')),
        'retry_delay': int(os.getenv('RETRY_DELAY', '30')),
        'monitored_devices': monitored_devices,
        'monitored_tags': monitored_tags,
        'monitor_all_devices': os.getenv('MONITOR_ALL_TAILSCALE_DEVICES', 'false').lower() == 'true',
        'email': load_email_config(),
    }


def validate_wireguard_config(logger: logging.Logger) -> bool:
    """Validate required WireGuard configuration."""
    required = {
        'WG_API_KEY': 'WireGuard API key',
        'SMTP_USERNAME': 'SMTP username',
        'SMTP_PASSWORD': 'SMTP password',
        'FROM_EMAIL': 'From email address',
    }

    missing = [f"{k} ({v})" for k, v in required.items() if not os.getenv(k)]

    if missing:
        logger.error("Missing required environment variables:")
        for item in missing:
            logger.error(f"  - {item}")
        return False
    return True


def validate_tailscale_config(logger: logging.Logger) -> bool:
    """Validate required Tailscale configuration."""
    required = {
        'TAILSCALE_TAILNET': 'Tailscale tailnet name',
        'TAILSCALE_API_KEY': 'Tailscale API key',
        'SMTP_USERNAME': 'SMTP username',
        'SMTP_PASSWORD': 'SMTP password',
        'FROM_EMAIL': 'From email address',
    }

    missing = [f"{k} ({v})" for k, v in required.items() if not os.getenv(k)]

    if missing:
        logger.error("Missing required environment variables:")
        for item in missing:
            logger.error(f"  - {item}")
        return False
    return True


# =============================================================================
# Logging
# =============================================================================

def setup_logging(verbose: bool = False, debug: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    """Setup logging configuration based on verbosity level."""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    if debug:
        fmt = '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    else:
        fmt = '%(asctime)s - %(levelname)s - %(message)s'

    handlers: List[logging.Handler] = [logging.StreamHandler()]

    if log_file and not debug:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=level, format=fmt, handlers=handlers)

    return logging.getLogger(__name__)


# =============================================================================
# Email Notifier
# =============================================================================

class EmailNotifier:
    """Handles email notifications for VPN monitoring."""

    def __init__(self, config: Dict[str, Any], logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger

    def send_notification(self, subject: str, body: str) -> None:
        """Send email notification."""
        try:
            self.logger.debug(f"Preparing email: {subject}")

            msg = MIMEMultipart()
            msg['From'] = self.config['from_email']
            msg['To'] = ', '.join(self.config['to_emails'])
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_username'], self.config['smtp_password'])
                for to_email in self.config['to_emails']:
                    server.sendmail(self.config['from_email'], to_email, msg.as_string())

            self.logger.info(f"Email notification sent: {subject}")

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")

    def send_test_email(self, service: str, details: str) -> None:
        """Send a test email to verify configuration."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"{service} Monitor Test Email"
        body = f"""
This is a test email from {service} Monitor.

Configuration Test Results:
- Timestamp: {timestamp}
{details}

If you receive this email, your email configuration is working correctly!
"""
        self.logger.info("Sending test email...")
        self.send_notification(subject, body)


# =============================================================================
# WireGuard Monitor
# =============================================================================

def parse_handshake_age(handshake: str) -> Optional[int]:
    """Return seconds since handshake, or None if unparseable."""
    if not handshake or handshake == 'No Handshake':
        return None

    # H:M:S format (e.g., "0:05:23")
    if match := re.match(r'^(\d+):(\d+):(\d+)$', handshake):
        h, m, s = map(int, match.groups())
        return h * 3600 + m * 60 + s

    # ISO format (e.g., "2025-01-15T14:25:00Z")
    try:
        dt = datetime.fromisoformat(handshake.replace('Z', '+00:00'))
        return int((datetime.now(timezone.utc) - dt).total_seconds())
    except ValueError:
        return None


class WireGuardMonitor:
    """Monitors WireGuard connections via API."""

    def __init__(self, config: Dict[str, Any], notifier: EmailNotifier, logger: logging.Logger) -> None:
        self.config = config
        self.notifier = notifier
        self.logger = logger
        self.last_status: Dict[str, Any] = {}
        self.consecutive_failures: int = 0

    def get_status(self) -> Optional[Dict[str, Any]]:
        """Fetch WireGuard configuration info from API."""
        headers = {'wg-dashboard-apikey': self.config['api_key']}
        url = f"{self.config['api_url']}/getWireguardConfigurationInfo"
        params = {'configurationName': self.config['config_name']}

        self.logger.debug(f"API request to: {url}")

        for attempt in range(self.config['max_retries']):
            try:
                response = requests.get(
                    url, headers=headers, params=params,
                    timeout=self.config['connection_timeout']
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    self.logger.warning(f"API returned {response.status_code}: {response.text}")

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"API request attempt {attempt + 1} failed: {e}")
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])

        self.logger.error("All API request attempts failed")
        return None

    def analyze_connections(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze connection data and return status for each peer."""
        if not data or 'data' not in data:
            self.logger.error("Invalid API response format")
            return {}

        config_data = data['data']
        interface_info = config_data.get('configurationInfo', {})
        interface_status = interface_info.get('Status', False)

        if not interface_status:
            self.logger.warning(f"WireGuard interface {self.config['config_name']} is down")
            return {'interface': False}

        peers = config_data.get('configurationPeers', [])

        if not peers:
            self.logger.warning("No peers found in configuration")
            return {'interface': True, 'peers': {}}

        # Determine which peers to monitor
        if self.config['monitored_peers']:
            peers_to_monitor = self.config['monitored_peers']
        elif self.config['monitor_all_peers']:
            peers_to_monitor = [p.get('name', f"peer-{i}") for i, p in enumerate(peers)]
        else:
            self.logger.warning("No peers configured for monitoring")
            return {'interface': True, 'peers': {}}

        peer_status = {}

        for i, peer in enumerate(peers):
            peer_name = peer.get('name', f'peer-{i}')

            if peer_name not in peers_to_monitor:
                continue

            latest_handshake = peer.get('latest_handshake')
            status_field = peer.get('status', 'unknown')

            self.logger.debug(f"Peer '{peer_name}': handshake='{latest_handshake}', status='{status_field}'")

            # Parse handshake age
            handshake_age = parse_handshake_age(latest_handshake)
            is_connected = False

            if handshake_age is not None:
                is_connected = handshake_age < self.config['handshake_timeout']

            # Status field logic
            if status_field in ['running', 'connected', 'active']:
                if handshake_age and handshake_age > self.config['handshake_timeout']:
                    self.logger.warning(f"Peer '{peer_name}': status 'running' but stale handshake")
                    is_connected = False
                else:
                    is_connected = True
            elif status_field in ['stopped', 'disconnected', 'inactive']:
                if handshake_age is not None and handshake_age < self.config['handshake_timeout']:
                    is_connected = True  # Recent handshake overrides status (mobile sleeping)
                else:
                    is_connected = False

            peer_status[peer_name] = is_connected

            if is_connected:
                self.logger.info(f"Peer '{peer_name}' is connected")
            else:
                self.logger.warning(f"Peer '{peer_name}' is disconnected")

        return {'interface': True, 'peers': peer_status}

    def check_status_changes(self, current_status: Dict[str, Any]) -> None:
        """Check for status changes and send notifications."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not current_status.get('interface', False):
            if self.last_status.get('interface', True):
                subject = f"WireGuard Interface Down - {self.config['config_name']}"
                body = f"""
WireGuard interface {self.config['config_name']} is DOWN.

Time: {timestamp}
Status: Interface not running

Please check the WireGuard service immediately.
"""
                self.notifier.send_notification(subject, body)
        else:
            peers = current_status.get('peers', {})
            last_peers = self.last_status.get('peers', {})

            disconnected = [p for p, c in peers.items() if not c and last_peers.get(p, True)]
            reconnected = [p for p, c in peers.items() if c and not last_peers.get(p, True)]

            if disconnected:
                subject = f"WireGuard Peer(s) Disconnected - {self.config['config_name']}"
                body = f"""
WireGuard peer(s) have disconnected from {self.config['config_name']}.

Time: {timestamp}
Disconnected peers: {', '.join(disconnected)}

Current peer status:
"""
                for name, connected in peers.items():
                    body += f"  - {name}: {'Connected' if connected else 'Disconnected'}\n"
                self.notifier.send_notification(subject, body)

            if reconnected:
                subject = f"WireGuard Peer(s) Reconnected - {self.config['config_name']}"
                body = f"""
WireGuard peer(s) have reconnected to {self.config['config_name']}.

Time: {timestamp}
Reconnected peers: {', '.join(reconnected)}

Current peer status:
"""
                for name, connected in peers.items():
                    body += f"  - {name}: {'Connected' if connected else 'Disconnected'}\n"
                self.notifier.send_notification(subject, body)

        self.last_status = current_status.copy()

    def test_api(self) -> bool:
        """Test API connectivity and display results."""
        self.logger.info("Testing WireGuard API connectivity...")

        data = self.get_status()
        if data is None:
            self.logger.error("API connectivity test failed")
            return False

        self.logger.info("API connectivity test successful")

        if 'data' in data and 'configurationInfo' in data['data']:
            info = data['data']['configurationInfo']
            self.logger.info(f"Interface '{info.get('Name')}': {'UP' if info.get('Status') else 'DOWN'}")
            self.logger.info(f"Peers: {info.get('ConnectedPeers', 0)}/{info.get('TotalPeers', 0)} connected")

        if 'data' in data and 'configurationPeers' in data['data']:
            for peer in data['data']['configurationPeers']:
                name = peer.get('name', 'unnamed')
                handshake = peer.get('latest_handshake', 'Unknown')
                status = peer.get('status', 'unknown')
                self.logger.info(f"  - {name}: handshake='{handshake}', status='{status}'")

        return True

    def run(self, check_once: bool = False) -> None:
        """Main monitoring loop."""
        self.logger.info(f"Starting WireGuard monitor for {self.config['config_name']}")
        self.logger.info(f"Check interval: {self.config['check_interval']}s")

        while True:
            try:
                api_data = self.get_status()

                if api_data is None:
                    self.consecutive_failures += 1
                    self.logger.error(f"Failed to get status (failures: {self.consecutive_failures})")

                    if self.consecutive_failures >= 3:
                        subject = "WireGuard Monitoring Alert - API Unavailable"
                        body = f"""
Unable to monitor WireGuard connections due to API failures.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Consecutive failures: {self.consecutive_failures}
Configuration: {self.config['config_name']}

Please check the WireGuard Dashboard API.
"""
                        self.notifier.send_notification(subject, body)
                        self.consecutive_failures = 0
                else:
                    self.consecutive_failures = 0
                    current_status = self.analyze_connections(api_data)
                    self.check_status_changes(current_status)

                    if current_status.get('interface'):
                        peers = current_status.get('peers', {})
                        connected = sum(1 for c in peers.values() if c)
                        self.logger.info(f"Status: Interface UP, Peers: {connected}/{len(peers)} connected")
                    else:
                        self.logger.warning("Status: Interface DOWN")

                if check_once:
                    break

            except KeyboardInterrupt:
                self.logger.info("Monitor stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")

            if not check_once:
                time.sleep(self.config['check_interval'])


# =============================================================================
# Tailscale Monitor
# =============================================================================

class TailscaleMonitor:
    """Monitors Tailscale devices via API."""

    def __init__(self, config: Dict[str, Any], notifier: EmailNotifier, logger: logging.Logger) -> None:
        self.config = config
        self.notifier = notifier
        self.logger = logger
        self.last_status: Dict[str, Any] = {}
        self.consecutive_failures: int = 0

    def get_devices(self) -> Optional[Dict[str, Any]]:
        """Fetch Tailscale device information from API."""
        headers = {'Authorization': f'Bearer {self.config["api_key"]}'}
        url = f"https://api.tailscale.com/api/v2/tailnet/{self.config['tailnet']}/devices"

        self.logger.debug(f"API request to: {url}")

        for attempt in range(self.config['max_retries']):
            try:
                response = requests.get(
                    url, headers=headers,
                    timeout=self.config['connection_timeout']
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    self.logger.warning(f"API returned {response.status_code}: {response.text}")

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"API request attempt {attempt + 1} failed: {e}")
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])

        self.logger.error("All API request attempts failed")
        return None

    def analyze_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze device data and return online status for each device."""
        if not data or 'devices' not in data:
            self.logger.error("Invalid API response format")
            return {}

        devices = data['devices']

        if not devices:
            self.logger.warning("No devices found in Tailscale network")
            return {}

        # Determine monitoring mode
        monitor_by_name = bool(self.config['monitored_devices'])
        monitor_by_tags = bool(self.config['monitored_tags'])
        monitor_all = self.config['monitor_all_devices']

        if not (monitor_by_name or monitor_by_tags or monitor_all):
            self.logger.warning("No devices configured for monitoring")
            return {}

        device_status = {}

        for i, device in enumerate(devices):
            device_name = device.get('name', device.get('hostname', f'device-{i}'))
            device_tags = device.get('tags', [])

            # Check if device should be monitored
            should_monitor = False

            if monitor_by_name:
                should_monitor = device_name in self.config['monitored_devices']
            elif monitor_by_tags:
                for tag in self.config['monitored_tags']:
                    tag_check = tag if tag.startswith('tag:') else f'tag:{tag}'
                    if tag_check in device_tags:
                        should_monitor = True
                        break
            elif monitor_all:
                should_monitor = True

            if not should_monitor:
                continue

            is_online = device.get('connectedToControl', False)
            device_status[device_name] = is_online

            if is_online:
                self.logger.info(f"Device '{device_name}' is online")
            else:
                self.logger.warning(f"Device '{device_name}' is offline")

        return {'devices': device_status}

    def check_status_changes(self, current_status: Dict[str, Any]) -> None:
        """Check for status changes and send notifications."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        devices = current_status.get('devices', {})
        last_devices = self.last_status.get('devices', {})

        offline = [d for d, online in devices.items() if not online and last_devices.get(d, True)]
        online = [d for d, is_online in devices.items() if is_online and not last_devices.get(d, True)]

        if offline:
            short_names = [name.split('.')[0] for name in offline]
            device_list = ', '.join(short_names)

            subject = f"Tailscale Device Offline: {device_list}"
            body = f"""
Tailscale device(s) have gone offline on tailnet {self.config['tailnet']}.

Time: {timestamp}
Offline devices: {', '.join(offline)}

Current device status:
"""
            for name, is_online in devices.items():
                body += f"  - {name}: {'Online' if is_online else 'Offline'}\n"
            self.notifier.send_notification(subject, body)

        if online:
            short_names = [name.split('.')[0] for name in online]
            device_list = ', '.join(short_names)

            subject = f"Tailscale Device Online: {device_list}"
            body = f"""
Tailscale device(s) have come online on tailnet {self.config['tailnet']}.

Time: {timestamp}
Online devices: {', '.join(online)}

Current device status:
"""
            for name, is_online in devices.items():
                body += f"  - {name}: {'Online' if is_online else 'Offline'}\n"
            self.notifier.send_notification(subject, body)

        self.last_status = current_status.copy()

    def test_api(self) -> bool:
        """Test API connectivity and display results."""
        self.logger.info("Testing Tailscale API connectivity...")

        data = self.get_devices()
        if data is None:
            self.logger.error("API connectivity test failed")
            return False

        self.logger.info("API connectivity test successful")

        if 'devices' in data:
            devices = data['devices']
            online_count = sum(1 for d in devices if d.get('connectedToControl', False))
            self.logger.info(f"Devices: {online_count}/{len(devices)} online")

            for device in devices:
                name = device.get('name', device.get('hostname', 'unnamed'))
                is_online = device.get('connectedToControl', False)
                tags = device.get('tags', [])
                tags_str = f", tags: {', '.join(tags)}" if tags else ""
                self.logger.info(f"  - {name}: {'Online' if is_online else 'Offline'}{tags_str}")

        return True

    def run(self, check_once: bool = False) -> None:
        """Main monitoring loop."""
        self.logger.info(f"Starting Tailscale monitor for {self.config['tailnet']}")
        self.logger.info(f"Check interval: {self.config['check_interval']}s")

        while True:
            try:
                api_data = self.get_devices()

                if api_data is None:
                    self.consecutive_failures += 1
                    self.logger.error(f"Failed to get status (failures: {self.consecutive_failures})")

                    if self.consecutive_failures >= 3:
                        subject = "Tailscale Monitoring Alert - API Unavailable"
                        body = f"""
Unable to monitor Tailscale devices due to API failures.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Consecutive failures: {self.consecutive_failures}
Tailnet: {self.config['tailnet']}

Please check the Tailscale API connectivity.
"""
                        self.notifier.send_notification(subject, body)
                        self.consecutive_failures = 0
                else:
                    self.consecutive_failures = 0
                    current_status = self.analyze_devices(api_data)
                    self.check_status_changes(current_status)

                    devices = current_status.get('devices', {})
                    online = sum(1 for c in devices.values() if c)
                    self.logger.info(f"Status: {online}/{len(devices)} devices online")

                if check_once:
                    break

            except KeyboardInterrupt:
                self.logger.info("Monitor stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")

            if not check_once:
                time.sleep(self.config['check_interval'])


# =============================================================================
# CLI
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description='Monitor VPN connections and send email notifications',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vpn_monitor.py wireguard                # Monitor WireGuard continuously
  python vpn_monitor.py wg --check-once          # Single WireGuard check
  python vpn_monitor.py tailscale --config-test  # Test Tailscale API
  python vpn_monitor.py -v ts --check-once       # Verbose Tailscale check
"""
    )

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging (INFO level)')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug logging (DEBUG level)')

    subparsers = parser.add_subparsers(dest='service', help='VPN service to monitor')

    # WireGuard subcommand
    wg_parser = subparsers.add_parser('wireguard', aliases=['wg'],
                                       help='Monitor WireGuard connections')
    wg_parser.add_argument('--test-email', action='store_true',
                           help='Send a test email and exit')
    wg_parser.add_argument('--check-once', action='store_true',
                           help='Perform a single status check and exit')
    wg_parser.add_argument('--config-test', action='store_true',
                           help='Test API connectivity and exit')

    # Tailscale subcommand
    ts_parser = subparsers.add_parser('tailscale', aliases=['ts'],
                                       help='Monitor Tailscale devices')
    ts_parser.add_argument('--test-email', action='store_true',
                           help='Send a test email and exit')
    ts_parser.add_argument('--check-once', action='store_true',
                           help='Perform a single status check and exit')
    ts_parser.add_argument('--config-test', action='store_true',
                           help='Test API connectivity and exit')

    return parser


def run_wireguard(args: argparse.Namespace, logger: logging.Logger) -> None:
    """Run WireGuard monitor."""
    if not validate_wireguard_config(logger):
        sys.exit(1)

    config = load_wireguard_config()
    notifier = EmailNotifier(config['email'], logger)
    monitor = WireGuardMonitor(config, notifier, logger)

    logger.info(f"Monitoring WireGuard config: {config['config_name']}")
    logger.info(f"API URL: {config['api_url']}")

    if args.test_email:
        details = f"- Monitoring config: {config['config_name']}\n- API URL: {config['api_url']}\n- Check interval: {config['check_interval']} seconds"
        notifier.send_test_email("WireGuard", details)
    elif args.config_test:
        monitor.test_api()
    else:
        monitor.run(check_once=args.check_once)


def run_tailscale(args: argparse.Namespace, logger: logging.Logger) -> None:
    """Run Tailscale monitor."""
    if not validate_tailscale_config(logger):
        sys.exit(1)

    config = load_tailscale_config()
    notifier = EmailNotifier(config['email'], logger)
    monitor = TailscaleMonitor(config, notifier, logger)

    logger.info(f"Monitoring tailnet: {config['tailnet']}")

    if args.test_email:
        details = f"- Tailnet: {config['tailnet']}\n- Check interval: {config['check_interval']} seconds"
        notifier.send_test_email("Tailscale", details)
    elif args.config_test:
        monitor.test_api()
    else:
        monitor.run(check_once=args.check_once)


def main() -> None:
    """Main entry point."""
    load_dotenv()

    parser = create_parser()
    args = parser.parse_args()

    if not args.service:
        parser.print_help()
        sys.exit(1)

    # Determine log file based on service
    log_file = None
    if args.service in ('wireguard', 'wg'):
        log_file = 'wireguard_monitor.log'
    elif args.service in ('tailscale', 'ts'):
        log_file = 'tailscale_monitor.log'

    logger = setup_logging(verbose=args.verbose, debug=args.debug, log_file=log_file)

    if not os.path.exists('.env'):
        logger.error(".env file not found! Please copy .env.example to .env and configure.")
        sys.exit(1)

    print(f"VPN Monitor - {args.service.title()}")
    print("=" * 40)

    if args.service in ('wireguard', 'wg'):
        run_wireguard(args, logger)
    elif args.service in ('tailscale', 'ts'):
        run_tailscale(args, logger)


if __name__ == "__main__":
    main()
