#!/usr/bin/env python3
"""
Combined Network Monitor
Monitors both WireGuard and Tailscale connections and sends email notifications.
"""

import argparse
import logging
import os
import sys
import time
import threading
from datetime import datetime
from dotenv import load_dotenv

# Import the monitor classes
from wireguard_monitor import WireGuardMonitor, EmailNotifier as WGEmailNotifier, load_config as wg_load_config, validate_config as wg_validate_config
from tailscale_monitor import TailscaleMonitor, EmailNotifier as TSEmailNotifier, load_config as ts_load_config, validate_config as ts_validate_config

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
        '%(asctime)s - %(levelname)s - [%(name)s] %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
    )

    # Choose formatter based on debug mode
    formatter = detailed_formatter if debug else simple_formatter

    # Setup handlers
    handlers = [logging.StreamHandler()]

    # Add file handler if not in debug mode
    if not debug:
        handlers.append(logging.FileHandler('combined_monitor.log'))

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
        description='Monitor both WireGuard and Tailscale networks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 combined_monitor.py                    # Monitor both services
  python3 combined_monitor.py --wireguard-only   # Monitor only WireGuard
  python3 combined_monitor.py --tailscale-only   # Monitor only Tailscale
  python3 combined_monitor.py -v                 # Verbose output
  python3 combined_monitor.py -d                 # Debug mode
  python3 combined_monitor.py --check-once       # Single check and exit
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
        '--wireguard-only',
        action='store_true',
        help='Monitor only WireGuard connections'
    )

    parser.add_argument(
        '--tailscale-only',
        action='store_true',
        help='Monitor only Tailscale devices'
    )

    parser.add_argument(
        '--check-once',
        action='store_true',
        help='Perform a single status check and exit'
    )

    parser.add_argument(
        '--config-test',
        action='store_true',
        help='Test configuration and API connectivity'
    )

    return parser.parse_args()

def run_wireguard_monitor(wg_config, email_notifier, check_once=False):
    """Run WireGuard monitor in a separate thread."""
    logger = logging.getLogger('wireguard_monitor')
    try:
        monitor = WireGuardMonitor(wg_config, email_notifier)
        logger.info("Starting WireGuard monitor thread...")
        monitor.run_monitor(check_once=check_once)
    except Exception as e:
        logger.error(f"WireGuard monitor error: {e}")
        logger.debug(f"Exception details: {type(e).__name__}: {str(e)}", exc_info=True)

def run_tailscale_monitor(ts_config, email_notifier, check_once=False):
    """Run Tailscale monitor in a separate thread."""
    logger = logging.getLogger('tailscale_monitor')
    try:
        monitor = TailscaleMonitor(ts_config, email_notifier)
        logger.info("Starting Tailscale monitor thread...")
        monitor.run_monitor(check_once=check_once)
    except Exception as e:
        logger.error(f"Tailscale monitor error: {e}")
        logger.debug(f"Exception details: {type(e).__name__}: {str(e)}", exc_info=True)

def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup logging
    logger = setup_logging(verbose=args.verbose, debug=args.debug)

    print("Combined Network Monitor")
    print("=" * 40)

    # Check if .env file exists
    if not os.path.exists('.env'):
        logger.error(".env file not found!")
        logger.error("Please copy .env.example to .env and configure your settings.")
        return

    # Determine which monitors to run
    run_wireguard = not args.tailscale_only
    run_tailscale = not args.wireguard_only

    # Validate configurations
    wg_config_valid = False
    ts_config_valid = False

    if run_wireguard:
        logger.info("Checking WireGuard configuration...")
        wg_config_valid = wg_validate_config()
        if not wg_config_valid:
            logger.warning("WireGuard configuration incomplete or invalid")
            if not run_tailscale:
                return

    if run_tailscale:
        logger.info("Checking Tailscale configuration...")
        ts_config_valid = ts_validate_config()
        if not ts_config_valid:
            logger.warning("Tailscale configuration incomplete or invalid")
            if not run_wireguard:
                return

    if not wg_config_valid and not ts_config_valid:
        logger.error("No valid configurations found. Please configure at least one service.")
        return

    # Load configurations for valid services
    threads = []

    if run_wireguard and wg_config_valid:
        wg_config = wg_load_config()
        wg_email_config = {
            'smtp_server': wg_config['smtp_server'],
            'smtp_port': wg_config['smtp_port'],
            'smtp_username': wg_config['smtp_username'],
            'smtp_password': wg_config['smtp_password'],
            'from_email': wg_config['from_email'],
            'to_emails': wg_config['to_emails']
        }
        wg_email_notifier = WGEmailNotifier(wg_email_config)

        if args.config_test:
            logger.info("Testing WireGuard configuration...")
            monitor = WireGuardMonitor(wg_config, wg_email_notifier)
            monitor.test_api_connectivity()
        else:
            # Create and start WireGuard monitor thread
            wg_thread = threading.Thread(
                target=run_wireguard_monitor,
                args=(wg_config, wg_email_notifier, args.check_once),
                name="WireGuard-Monitor",
                daemon=True
            )
            threads.append(wg_thread)
            logger.info("WireGuard monitor configured")

    if run_tailscale and ts_config_valid:
        ts_config = ts_load_config()
        ts_email_config = {
            'smtp_server': ts_config['smtp_server'],
            'smtp_port': ts_config['smtp_port'],
            'smtp_username': ts_config['smtp_username'],
            'smtp_password': ts_config['smtp_password'],
            'from_email': ts_config['from_email'],
            'to_emails': ts_config['to_emails']
        }
        ts_email_notifier = TSEmailNotifier(ts_email_config)

        if args.config_test:
            logger.info("Testing Tailscale configuration...")
            monitor = TailscaleMonitor(ts_config, ts_email_notifier)
            monitor.test_api_connectivity()
        else:
            # Create and start Tailscale monitor thread
            ts_thread = threading.Thread(
                target=run_tailscale_monitor,
                args=(ts_config, ts_email_notifier, args.check_once),
                name="Tailscale-Monitor",
                daemon=True
            )
            threads.append(ts_thread)
            logger.info("Tailscale monitor configured")

    if args.config_test:
        logger.info("Configuration test completed")
        return

    # Start all monitor threads
    logger.info(f"Starting {len(threads)} monitor thread(s)...")
    for thread in threads:
        thread.start()
        logger.info(f"Started {thread.name}")

    try:
        # Wait for all threads to complete
        if args.check_once:
            logger.info("Waiting for single check to complete...")
            for thread in threads:
                thread.join(timeout=60)  # Wait up to 60 seconds for each thread
            logger.info("All checks completed")
        else:
            logger.info("Monitors running. Press Ctrl+C to stop.")
            # Keep main thread alive
            while any(thread.is_alive() for thread in threads):
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        logger.info("Waiting for monitor threads to stop...")
        for thread in threads:
            thread.join(timeout=5)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.debug:
            logger.exception("Full traceback:")

if __name__ == "__main__":
    main()
