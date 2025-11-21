#!/usr/bin/env python3
"""
Tailscale Connection Monitor
Monitors Tailscale devices via API and sends email notifications when device status changes.
"""

import requests
import smtplib
import json
import time
import logging
import os
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logging(verbose=False, debug=False):
    """Setup logging configuration based on verbosity level."""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # Choose formatter based on debug mode
    formatter = detailed_formatter if debug else simple_formatter

    # Setup handlers
    handlers = [logging.StreamHandler()]

    # Add file handler if not in debug mode (avoid cluttering during testing)
    if not debug:
        handlers.append(logging.FileHandler('tailscale_monitor.log'))

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    # Apply detailed formatter to all handlers in debug mode
    if debug:
        for handler in logging.getLogger().handlers:
            handler.setFormatter(detailed_formatter)

    return logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Monitor Tailscale devices and send email notifications',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 tailscale_monitor.py                    # Normal operation
  python3 tailscale_monitor.py -v                 # Verbose output
  python3 tailscale_monitor.py -d                 # Debug mode with detailed logging
  python3 tailscale_monitor.py --test-email       # Test email configuration
  python3 tailscale_monitor.py --check-once       # Single status check (no loop)
        """
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging (INFO level)'
    )

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug logging (DEBUG level) with detailed output'
    )

    parser.add_argument(
        '--test-email',
        action='store_true',
        help='Send a test email and exit'
    )

    parser.add_argument(
        '--check-once',
        action='store_true',
        help='Perform a single status check and exit (useful for testing)'
    )

    parser.add_argument(
        '--config-test',
        action='store_true',
        help='Test configuration and API connectivity without sending emails'
    )

    return parser.parse_args()

def load_config() -> Dict:
    """Load configuration from environment variables."""

    # Parse email recipients (comma-separated)
    to_emails_str = os.getenv('TO_EMAILS', 'admin@example.com')
    to_emails = [email.strip() for email in to_emails_str.split(',')]

    # Parse monitored devices (comma-separated)
    monitored_devices_str = os.getenv('MONITORED_TAILSCALE_DEVICES', '')
    monitored_devices = [device.strip() for device in monitored_devices_str.split(',') if device.strip()]

    return {
        # Tailscale API settings
        'tailnet': os.getenv('TAILSCALE_TAILNET'),
        'api_key': os.getenv('TAILSCALE_API_KEY'),

        # Email settings
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_username': os.getenv('SMTP_USERNAME'),
        'smtp_password': os.getenv('SMTP_PASSWORD'),
        'from_email': os.getenv('FROM_EMAIL'),
        'to_emails': to_emails,

        # Monitoring settings
        'check_interval': int(os.getenv('CHECK_INTERVAL', '300')),
        'connection_timeout': int(os.getenv('CONNECTION_TIMEOUT', '10')),
        'max_retries': int(os.getenv('MAX_RETRIES', '3')),
        'retry_delay': int(os.getenv('RETRY_DELAY', '30')),
        'monitored_devices': monitored_devices,
        'monitor_all_devices': os.getenv('MONITOR_ALL_TAILSCALE_DEVICES', 'false').lower() == 'true',
    }

# Load configuration
CONFIG = load_config()

# Initialize logger (will be reconfigured in main())
logger = logging.getLogger(__name__)

class EmailNotifier:
    """Handles email notifications for Tailscale monitoring."""

    def __init__(self, email_config: Dict):
        """Initialize email notifier with configuration."""
        self.config = email_config
        self.logger = logging.getLogger(__name__)

    def send_notification(self, subject: str, body: str):
        """Send email notification."""
        try:
            self.logger.debug(f"Preparing email: {subject}")
            self.logger.debug(f"SMTP server: {self.config['smtp_server']}:{self.config['smtp_port']}")
            self.logger.debug(f"From: {self.config['from_email']}")
            self.logger.debug(f"To: {self.config['to_emails']}")

            msg = MIMEMultipart()
            msg['From'] = self.config['from_email']
            msg['To'] = ', '.join(self.config['to_emails'])
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            self.logger.debug("Connecting to SMTP server...")
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])

            self.logger.debug("Starting TLS...")
            server.starttls()

            self.logger.debug("Authenticating...")
            server.login(self.config['smtp_username'], self.config['smtp_password'])

            self.logger.debug("Sending email...")
            for to_email in self.config['to_emails']:
                server.sendmail(self.config['from_email'], to_email, msg.as_string())

            server.quit()
            self.logger.info(f"Email notification sent: {subject}")

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            self.logger.debug(f"Email error details: {type(e).__name__}: {str(e)}")

    def send_test_email(self, tailnet: str, check_interval: int):
        """Send a test email to verify configuration."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = "Tailscale Monitor Test Email"
        body = f"""
This is a test email from Tailscale Monitor.

Configuration Test Results:
- Timestamp: {timestamp}
- Monitoring tailnet: {tailnet}
- Check interval: {check_interval} seconds

If you receive this email, your email configuration is working correctly!
"""

        self.logger.info("Sending test email...")
        self.send_notification(subject, body)

class TailscaleMonitor:
    def __init__(self, config: Dict, email_notifier: EmailNotifier):
        self.config = config
        self.email_notifier = email_notifier
        self.last_status = {}  # Track last known status to avoid spam
        self.consecutive_failures = 0

    def get_tailscale_devices(self) -> Optional[Dict]:
        """Fetch Tailscale device information from API."""
        headers = {
            'Authorization': f'Bearer {self.config["api_key"]}'
        }

        url = f"https://api.tailscale.com/api/v2/tailnet/{self.config['tailnet']}/devices"

        logger.debug(f"Making API request to: {url}")
        logger.debug(f"Request headers: Authorization: Bearer ***")

        for attempt in range(self.config['max_retries']):
            try:
                logger.debug(f"API request attempt {attempt + 1}/{self.config['max_retries']}")

                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.config['connection_timeout']
                )

                logger.debug(f"API response status: {response.status_code}")
                logger.debug(f"API response headers: {dict(response.headers)}")

                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"API response data: {json.dumps(data, indent=2)}")
                    return data
                else:
                    logger.warning(f"API returned status {response.status_code}: {response.text}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"API request attempt {attempt + 1} failed: {e}")
                logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")

                if attempt < self.config['max_retries'] - 1:
                    logger.debug(f"Waiting {self.config['retry_delay']} seconds before retry...")
                    time.sleep(self.config['retry_delay'])

        logger.error("All API request attempts failed")
        return None

    def analyze_devices(self, data: Dict) -> Dict[str, bool]:
        """Analyze device data and return online status for each device."""
        logger.debug("Starting device analysis")

        if not data or 'devices' not in data:
            logger.error("Invalid API response format")
            logger.debug(f"Received data: {data}")
            return {}

        devices = data['devices']
        logger.debug(f"Found {len(devices)} total devices")

        if not devices:
            logger.warning("No devices found in Tailscale network")
            return {}

        # Determine which devices to monitor
        if self.config['monitored_devices']:
            devices_to_monitor = self.config['monitored_devices']
            logger.debug(f"Monitoring specific devices: {devices_to_monitor}")
        elif self.config['monitor_all_devices']:
            devices_to_monitor = [device.get('name', device.get('hostname', f"device-{i}"))
                                  for i, device in enumerate(devices)]
            logger.debug(f"Monitoring all devices: {devices_to_monitor}")
        else:
            logger.warning("No devices configured for monitoring. Set MONITORED_TAILSCALE_DEVICES or MONITOR_ALL_TAILSCALE_DEVICES=true")
            return {}

        device_status = {}

        for i, device in enumerate(devices):
            device_name = device.get('name', device.get('hostname', f'device-{i}'))

            # Only monitor devices in our watch list
            if device_name not in devices_to_monitor:
                logger.debug(f"Skipping device '{device_name}' (not in monitor list)")
                continue

            # Check if device is online
            # Tailscale API returns 'online' field in the device object
            is_online = device.get('online', False)

            # Get additional useful information
            last_seen = device.get('lastSeen', 'Unknown')
            os_type = device.get('os', 'Unknown')

            logger.debug(f"Analyzing device '{device_name}': online={is_online}, last_seen='{last_seen}', os='{os_type}'")

            device_status[device_name] = is_online

            if not is_online:
                logger.warning(f"Monitored device '{device_name}' is offline (last seen: {last_seen})")
            else:
                logger.info(f"Monitored device '{device_name}' is online (OS: {os_type})")

        result = {'devices': device_status}
        logger.debug(f"Device analysis result: {result}")
        return result

    def check_status_changes(self, current_status: Dict):
        """Check for status changes and send notifications."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        devices = current_status.get('devices', {})
        last_devices = self.last_status.get('devices', {})

        offline_devices = []
        online_devices = []

        for device_name, is_online in devices.items():
            was_online = last_devices.get(device_name, True)

            if not is_online and was_online:
                offline_devices.append(device_name)
            elif is_online and not was_online:
                online_devices.append(device_name)

        # Send notifications for devices going offline
        if offline_devices:
            subject = f"Tailscale Device(s) Offline - {self.config['tailnet']}"
            body = f"""
Tailscale device(s) have gone offline on tailnet {self.config['tailnet']}.

Time: {timestamp}
Offline devices: {', '.join(offline_devices)}

Current device status:
"""
            for device_name, is_online in devices.items():
                status = "Online" if is_online else "Offline"
                body += f"  - {device_name}: {status}\n"

            self.email_notifier.send_notification(subject, body)

        # Send notifications for devices coming online
        if online_devices:
            subject = f"Tailscale Device(s) Online - {self.config['tailnet']}"
            body = f"""
Tailscale device(s) have come online on tailnet {self.config['tailnet']}.

Time: {timestamp}
Online devices: {', '.join(online_devices)}

Current device status:
"""
            for device_name, is_online in devices.items():
                status = "Online" if is_online else "Offline"
                body += f"  - {device_name}: {status}\n"

            self.email_notifier.send_notification(subject, body)

        self.last_status = current_status.copy()

    def test_api_connectivity(self):
        """Test API connectivity and display results."""
        logger.info("Testing API connectivity...")

        data = self.get_tailscale_devices()
        if data is None:
            logger.error("API connectivity test failed")
            return False

        logger.info("API connectivity test successful")

        # Show devices info
        if 'devices' in data:
            devices = data['devices']
            logger.info(f"Total devices found: {len(devices)}")

            online_count = sum(1 for device in devices if device.get('online', False))
            logger.info(f"Online devices: {online_count}/{len(devices)}")

            for i, device in enumerate(devices):
                device_name = device.get('name', device.get('hostname', f'device-{i}'))
                is_online = device.get('online', False)
                os_type = device.get('os', 'Unknown')
                last_seen = device.get('lastSeen', 'Unknown')
                status_str = "Online" if is_online else "Offline"
                logger.info(f"  - {device_name}: {status_str} (OS: {os_type}, Last seen: {last_seen})")

        # Test monitoring logic
        status = self.analyze_devices(data)

        devices = status.get('devices', {})
        if devices:
            monitored_count = len(devices)
            online_count = sum(1 for is_online in devices.values() if is_online)
            logger.info(f"Monitoring {monitored_count} devices: {online_count} online, {monitored_count - online_count} offline")

            for device_name, is_online in devices.items():
                status_str = "Online" if is_online else "Offline"
                logger.info(f"  - {device_name}: {status_str}")
        else:
            logger.warning("No devices configured for monitoring")
            logger.info("Available device names:")
            if 'devices' in data:
                for device in data['devices']:
                    logger.info(f"  - '{device.get('name', device.get('hostname', 'unnamed'))}'")
            logger.info("Configure MONITORED_TAILSCALE_DEVICES in .env or set MONITOR_ALL_TAILSCALE_DEVICES=true")

        return True

    def run_monitor(self, check_once=False):
        """Main monitoring loop."""
        logger.info("Starting Tailscale device monitor...")
        logger.info(f"Monitoring tailnet: {self.config['tailnet']}")
        logger.info(f"Check interval: {self.config['check_interval']} seconds")

        if check_once:
            logger.info("Single check mode enabled")

        iteration = 0
        while True:
            iteration += 1
            logger.debug(f"Starting monitoring iteration {iteration}")

            try:
                # Get current status
                api_data = self.get_tailscale_devices()

                if api_data is None:
                    self.consecutive_failures += 1
                    logger.error(f"Failed to get Tailscale device status (consecutive failures: {self.consecutive_failures})")

                    # Send alert after multiple consecutive failures
                    if self.consecutive_failures >= 3:
                        subject = f"Tailscale Monitoring Alert - API Unavailable"
                        body = f"""
Unable to monitor Tailscale devices due to API failures.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Consecutive failures: {self.consecutive_failures}
Tailnet: {self.config['tailnet']}

Please check:
1. Tailscale API is accessible
2. API key is valid
3. Network connectivity

Monitoring will continue automatically.
"""
                        self.email_notifier.send_notification(subject, body)
                        self.consecutive_failures = 0  # Reset to avoid spam
                else:
                    self.consecutive_failures = 0
                    current_status = self.analyze_devices(api_data)
                    self.check_status_changes(current_status)

                    # Log current status
                    devices = current_status.get('devices', {})
                    if isinstance(devices, dict):
                        online_count = sum(1 for is_online in devices.values() if is_online)
                        total_devices = len(devices)
                        logger.info(f"Status check: {online_count}/{total_devices} devices online")
                    else:
                        logger.info("Status check: no device data")

                if check_once:
                    logger.info("Single check completed, exiting")
                    break

            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in monitoring loop: {e}")
                logger.debug(f"Exception details: {type(e).__name__}: {str(e)}", exc_info=True)

            if not check_once:
                # Wait for next check
                logger.debug(f"Waiting {self.config['check_interval']} seconds for next check...")
                time.sleep(self.config['check_interval'])

def validate_config():
    """Validate required configuration settings."""
    required_settings = {
        'TAILSCALE_TAILNET': 'Tailscale tailnet name',
        'TAILSCALE_API_KEY': 'Tailscale API key',
        'SMTP_USERNAME': 'SMTP username',
        'SMTP_PASSWORD': 'SMTP password',
        'FROM_EMAIL': 'From email address',
    }

    missing = []
    for env_var, description in required_settings.items():
        if not os.getenv(env_var):
            missing.append(f"{env_var} ({description})")

    if missing:
        logger.error("Missing required environment variables:")
        for item in missing:
            logger.error(f"  - {item}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        return False

    return True

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_arguments()

    # Setup logging based on arguments
    global logger
    logger = setup_logging(verbose=args.verbose, debug=args.debug)

    print("Tailscale Device Monitor")
    print("=" * 40)

    # Check if .env file exists
    if not os.path.exists('.env'):
        logger.error(".env file not found!")
        logger.error("Please copy .env.example to .env and configure your settings.")
        return

    # Validate configuration
    if not validate_config():
        return

    logger.info(f"Configuration loaded successfully")
    logger.info(f"Monitoring tailnet: {CONFIG['tailnet']}")
    logger.info(f"Email notifications will be sent to: {', '.join(CONFIG['to_emails'])}")

    if args.debug:
        logger.info("Debug mode enabled - detailed logging active")
    elif args.verbose:
        logger.info("Verbose mode enabled")

    # Create email notifier instance
    email_config = {
        'smtp_server': CONFIG['smtp_server'],
        'smtp_port': CONFIG['smtp_port'],
        'smtp_username': CONFIG['smtp_username'],
        'smtp_password': CONFIG['smtp_password'],
        'from_email': CONFIG['from_email'],
        'to_emails': CONFIG['to_emails']
    }
    email_notifier = EmailNotifier(email_config)

    # Create monitor with email notifier
    monitor = TailscaleMonitor(CONFIG, email_notifier)

    try:
        if args.test_email:
            logger.info("Testing email configuration...")
            email_notifier.send_test_email(
                CONFIG['tailnet'],
                CONFIG['check_interval']
            )

        elif args.config_test:
            logger.info("Testing configuration and API connectivity...")
            if monitor.test_api_connectivity():
                logger.info("Configuration test completed successfully")
            else:
                logger.error("Configuration test failed")

        elif args.check_once:
            logger.info("Performing single status check...")
            monitor.run_monitor(check_once=True)

        else:
            # Normal monitoring mode
            monitor.run_monitor()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.debug:
            logger.exception("Full traceback:")

if __name__ == "__main__":
    main()
