#!/bin/bash

echo "Installing EC2 Inventory Script Requirements..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Install requirements
echo "Installing Python packages..."
pip3 install --break-system-packages -r requirements.txt

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Copy example configuration files:"
    echo "   cp aws_accounts.json.example aws_accounts.json"
    echo "   cp gcp-service-account.json.example gcp-service-account.json"
    echo "   cp sheet_config.json.example sheet_config.json"
    echo ""
    echo "2. Edit aws_accounts.json with your AWS credentials"
    echo "   nano aws_accounts.json"
    echo ""
    echo "3. Replace gcp-service-account.json with your Google service account key"
    echo "   (Download from Google Cloud Console)"
    echo ""
    echo "4. Edit sheet_config.json with your Google Sheet ID"
    echo "   nano sheet_config.json"
    echo ""
    echo "5. Run the script:"
    echo "   python3 ec2_inventory.py"
    echo ""
else
    echo ""
    echo "✗ Installation failed. Please check the error messages above."
    exit 1
fi
