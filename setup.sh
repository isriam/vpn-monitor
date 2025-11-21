#!/bin/bash

# VPN Monitor Setup Script
# This script sets up the Python virtual environment, installs dependencies,
# and creates a systemd service for the VPN monitor (WireGuard and Tailscale).

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="vpn-monitor"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_SCRIPT="$SCRIPT_DIR/combined_monitor.py"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${BLUE}VPN Monitor Setup Script${NC}"
echo "================================="
echo ""

# Function to print status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root for systemd service creation
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script needs to be run with sudo for systemd service creation."
        echo "Usage: sudo bash setup.sh"
        exit 1
    fi
    
    # Get the actual user who ran sudo
    REAL_USER=${SUDO_USER:-$USER}
    REAL_HOME=$(eval echo "~$REAL_USER")
    
    if [ -z "$REAL_USER" ] || [ "$REAL_USER" = "root" ]; then
        print_error "Please run this script with sudo as a regular user, not as root directly."
        echo "Usage: sudo bash setup.sh"
        exit 1
    fi
    
    print_status "Running as user: $REAL_USER"
}

# Check if Python 3 is installed
check_python() {
    print_status "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        echo "On Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-venv python3-pip"
        echo "On CentOS/RHEL: sudo yum install python3 python3-venv python3-pip"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_status "Found Python $PYTHON_VERSION"
}

# Create virtual environment
create_venv() {
    print_status "Creating Python virtual environment..."
    
    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists. Removing old one..."
        rm -rf "$VENV_DIR"
    fi
    
    # Create venv as the real user, not root
    sudo -u "$REAL_USER" python3 -m venv "$VENV_DIR"
    
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
    
    print_status "Virtual environment created successfully"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ ! -f "$SCRIPT_DIR/requirements.txt" ]; then
        print_error "requirements.txt not found in $SCRIPT_DIR"
        exit 1
    fi
    
    # Install as the real user
    sudo -u "$REAL_USER" "$VENV_DIR/bin/pip" install --upgrade pip
    sudo -u "$REAL_USER" "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    
    print_status "Dependencies installed successfully"
}

# Check if .env file exists
check_env_file() {
    print_status "Checking environment configuration..."
    
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        print_warning ".env file not found!"
        echo ""
        echo "Please create your .env file before starting the service:"
        echo "1. Copy the example: cp .env.example .env"
        echo "2. Edit with your settings: nano .env"
        echo ""
        return 1
    else
        print_status ".env file found"
        return 0
    fi
}

# Create systemd service file
create_service() {
    print_status "Creating systemd service file..."
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=VPN Connection Monitor (WireGuard and Tailscale)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$VENV_DIR/bin/python $PYTHON_SCRIPT
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$SCRIPT_DIR

[Install]
WantedBy=multi-user.target
EOF

    if [ ! -f "$SERVICE_FILE" ]; then
        print_error "Failed to create systemd service file"
        exit 1
    fi
    
    print_status "Systemd service file created: $SERVICE_FILE"
}

# Set correct permissions
set_permissions() {
    print_status "Setting file permissions..."
    
    # Make sure the real user owns the project directory
    chown -R "$REAL_USER:$REAL_USER" "$SCRIPT_DIR"
    
    # Make the Python script executable
    chmod +x "$PYTHON_SCRIPT"
    
    # Set secure permissions for .env if it exists
    if [ -f "$SCRIPT_DIR/.env" ]; then
        chmod 600 "$SCRIPT_DIR/.env"
        chown "$REAL_USER:$REAL_USER" "$SCRIPT_DIR/.env"
    fi
    
    print_status "Permissions set correctly"
}

# Enable and start service
setup_service() {
    print_status "Setting up systemd service..."
    
    # Reload systemd daemon
    systemctl daemon-reload
    
    # Enable service to start on boot
    systemctl enable "$SERVICE_NAME"
    
    print_status "Service enabled successfully"
    
    if check_env_file; then
        echo ""
        read -p "Do you want to start the service now? (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            systemctl start "$SERVICE_NAME"
            sleep 2
            
            if systemctl is-active --quiet "$SERVICE_NAME"; then
                print_status "Service started successfully!"
                echo ""
                echo "Service status:"
                systemctl status "$SERVICE_NAME" --no-pager -l
            else
                print_error "Service failed to start. Check the logs:"
                echo "sudo journalctl -u $SERVICE_NAME -f"
            fi
        else
            print_warning "Service not started. You can start it later with:"
            echo "sudo systemctl start $SERVICE_NAME"
        fi
    else
        print_warning "Service created but not started due to missing .env file"
    fi
}

# Print final instructions
print_instructions() {
    echo ""
    echo -e "${GREEN}Setup completed successfully!${NC}"
    echo "================================="
    echo ""
    echo "Next steps:"
    echo ""
    
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        echo "1. Create your configuration file:"
        echo "   cp .env.example .env"
        echo "   nano .env"
        echo ""
        echo "2. Start the service:"
        echo "   sudo systemctl start $SERVICE_NAME"
        echo ""
    fi
    
    echo "Useful commands:"
    echo "  Start service:    sudo systemctl start $SERVICE_NAME"
    echo "  Stop service:     sudo systemctl stop $SERVICE_NAME"
    echo "  Restart service:  sudo systemctl restart $SERVICE_NAME"
    echo "  View status:      sudo systemctl status $SERVICE_NAME"
    echo "  View logs:        sudo journalctl -u $SERVICE_NAME -f"
    echo "  Disable service:  sudo systemctl disable $SERVICE_NAME"
    echo ""
    echo "Configuration file: $SCRIPT_DIR/.env"
    echo "Log file:          $SCRIPT_DIR/combined_monitor.log"
    echo "Service file:      $SERVICE_FILE"
}

# Main execution
main() {
    check_sudo
    check_python
    create_venv
    install_dependencies
    create_service
    set_permissions
    setup_service
    print_instructions
}

# Run main function
main "$@"