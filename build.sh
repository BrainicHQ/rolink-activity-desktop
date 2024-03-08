#!/bin/bash

# Define the script and icons for different platforms
SCRIPT="rolink-activity.py"
MAC_ICON="icon.icns"
LINUX_ICON="icon.png"
WINDOWS_ICON="icon.ico"
APP_NAME="RoLink Activity"

# Build for macOS
echo "Building for macOS..."
pyinstaller --onefile --windowed $SCRIPT --icon=$MAC_ICON --name "$APP_NAME"
echo "macOS build completed."

# Build for Linux
# Assuming the same Python script works on Linux without modifications.
echo "Building for Linux..."
pyinstaller --onefile --windowed $SCRIPT --icon=$LINUX_ICON --name "$APP_NAME"
echo "Linux build completed."

# Optional: Build for Windows using Wine (if installed and configured)
# This part is commented out because it requires Wine to be properly set up on your macOS.
# Uncomment and adjust paths as necessary if you wish to attempt Windows builds from macOS.
# echo "Building for Windows..."
wine pyinstaller --onefile --windowed $SCRIPT --icon=$WINDOWS_ICON --name "$APP_NAME"
# echo "Windows build completed."

echo "Build process completed for all specified platforms."