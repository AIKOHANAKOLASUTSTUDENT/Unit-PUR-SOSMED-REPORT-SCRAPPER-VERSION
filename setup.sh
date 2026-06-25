#!/bin/bash

set -e

echo "Creating Python virtual environment..."
python -m venv venv

echo "Activating virtual environment..."
source venv/Scripts/activate || . venv/Scripts/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Installing Playwright Chromium..."
playwright install chromium

echo "Creating necessary directories..."
mkdir -p logs input credentials

echo "Setup complete! Next steps:"
echo "1. Edit .env file with your Google Sheets ID and credentials"
echo "2. Edit .env with your Instagram username and password"
echo "3. Add Instagram URLs to input/urls.txt"
echo "4. Run: python main.py"
