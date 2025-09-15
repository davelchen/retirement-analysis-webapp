#!/bin/bash

echo "🚀 Starting Retirement Analysis Suite..."
echo "📁 Working directory: $(pwd)"
echo ""

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Try to find streamlit in user's Python path
if python3 -c "import streamlit" 2>/dev/null; then
    echo "✅ Streamlit found."
else
    echo "❌ Streamlit not found. Installing..."
    python3 -m pip install streamlit plotly
    echo "✅ Installation complete."
fi

echo ""
echo "🎯 Retirement Analysis Suite - Unified Application"
echo ""
echo "Features:"
echo "  🧙‍♂️  Setup Wizard - Interactive parameter setup with guidance"
echo "  📊 Monte Carlo Analysis - Advanced simulations and visualizations"
echo "  🔄 Seamless Navigation - Switch between wizard and analysis"
echo "  💾 No File Transfers - Direct parameter sharing between pages"
echo ""
echo "Access Options:"
echo "  📍 Main App: http://localhost:8501"
echo ""
echo "Recommended Workflow:"
echo "  1. 🧙‍♂️ Start with Run Wizard for parameter configuration"
echo "  2. 📊 Navigate to Simulation to run Monte Carlo analysis"
echo "  3. 🔄 Use sidebar navigation to switch between pages anytime"
echo ""

# Check if port is already in use
if check_port 8501; then
    echo "⚠️  Port 8501 is already in use"
    echo "   The app may already be running at: http://localhost:8501"
    echo ""
    read -p "Continue anyway? (y/n): " continue_choice
    if [[ $continue_choice != "y" && $continue_choice != "Y" ]]; then
        echo "❌ Exiting..."
        exit 1
    fi
fi

echo "🚀 Starting Retirement Analysis Suite..."
echo "🌐 Open your browser to: http://localhost:8501"
echo ""
echo "💡 Navigation Tips:"
echo "   • Use the sidebar to switch between Run Wizard and Simulation"
echo "   • Start from main page to see feature overview"
echo "   • Parameters are shared automatically between pages"
echo ""
echo "   (Press Ctrl+C to stop the application)"
echo ""

# Start the unified multipage application
python3 -m streamlit run main.py --server.address localhost --server.port 8501