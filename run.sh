#!/bin/bash

echo "🚀 Starting Retirement Monte Carlo Simulator..."
echo "📁 Working directory: $(pwd)"
echo ""

# Try to find streamlit in user's Python path
if python3 -c "import streamlit" 2>/dev/null; then
    echo "✅ Streamlit found. Starting app..."
    echo "🌐 Open your browser to: http://localhost:8501"
    echo ""
    python3 -m streamlit run app.py --server.address localhost --server.port 8501
else
    echo "❌ Streamlit not found. Installing..."
    python3 -m pip install streamlit
    echo "✅ Installation complete. Starting app..."
    python3 -m streamlit run app.py --server.address localhost --server.port 8501
fi