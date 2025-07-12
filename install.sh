#!/bin/bash

echo "🎵 YouTube Playlist Manager - Installation Script"
echo "================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7+ first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Set up your YouTube API credentials:"
echo "   - Go to https://console.cloud.google.com/"
echo "   - Create a project and enable YouTube Data API v3"
echo "   - Create OAuth 2.0 credentials"
echo "   - Download as 'credentials.json' and place in this directory"
echo ""
echo "3. Run the application:"
echo "   python main.py"
echo ""
echo "📖 For detailed instructions, see README.md" 