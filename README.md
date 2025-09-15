# Retirement Analysis Suite

A comprehensive **Streamlit multipage application** for retirement planning featuring an interactive **Setup Wizard** and advanced **Monte Carlo simulation** with tax-aware withdrawals and Guyton-Klinger guardrails. Seamlessly navigate between guided parameter setup and sophisticated financial analysis.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-Educational-green.svg)
![Tests](https://img.shields.io/badge/tests-320%20tests-brightgreen.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.49+-red.svg)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/username/retirement-analysis-suite.git
cd retirement-analysis-suite

# Install dependencies
pip install -r requirements.txt

# Run the unified application (recommended)
./run.sh

# Or run directly:
streamlit run main.py
```

**Open your browser to `http://localhost:8501`**

### 🧭 Navigation Options
- **Main Landing Page**: http://localhost:8501 (choose your starting point)
- **Setup Wizard**: Navigate via sidebar or click "Wizard" page
- **Monte Carlo Analysis**: Navigate via sidebar or click "Monte_Carlo_Analysis" page

## ✨ Key Features

### 🧙‍♂️ **Interactive Setup Wizard**
- Step-by-step guidance with parameter persistence and age-aware validation
- Beautiful visualizations and educational content with real-time feedback
- JSON save/load with seamless handoff to Monte Carlo analysis

### 🎲 **Advanced Monte Carlo Engine**
- Up to 50,000 simulations with tax-aware withdrawals and Guyton-Klinger guardrails
- Multiple asset classes with configurable market scenarios

### 🏛️ **Enhanced Social Security & Tax Integration**
- Retirement vs SS age distinction (retire any age, start SS 62-70)
- 4 funding scenarios with 2034 trust fund modeling
- 10-state tax integration with progressive brackets and gross-up solver

### 📊 **Professional UI & Visualizations**
- Interactive Plotly charts with wealth distributions and percentile bands
- Dynamic expense/income management with comprehensive tooltips
- Year-by-year detailed tables and CSV exports

### 🤖 **AI-Powered Analysis**
- Google Gemini integration with usage tracking and privacy controls
- Interactive chat for context-aware retirement plan insights

## 🏗️ Architecture & Structure

### Multipage Application Design
```
├── main.py                     # 🏠 Multipage entry point & navigation
├── pages/                      # 📄 Streamlit pages
│   ├── wizard.py               # 🧙‍♂️ Interactive setup wizard with JSON loading
│   └── monte_carlo.py          # 📊 Monte Carlo analysis & AI integration
├── simulation.py               # 🎲 Monte Carlo simulation engine
├── deterministic.py            # 📊 Expected-return projections
├── tax.py                      # 💰 Tax calculations & gross-up solver
├── tax_utils.py                # 🏛️ Social Security benefit calculations
├── charts.py                   # 📈 Plotly visualization builders
├── io_utils.py                 # 💾 Data import/export & JSON conversion
├── ai_analysis.py              # 🤖 Google Gemini AI integration & usage tracking
├── config_utils.py             # ⚙️ Configuration utilities & defaults
├── wizard_charts.py            # 📊 Wizard-specific chart functions
├── wizard_utils.py             # 🔧 Wizard parameter conversion utilities
├── tests/                      # 🧪 Comprehensive test suite (320+ tests)
│   ├── test_simulation.py      #     Core simulation tests
│   ├── test_tax.py             #     Tax calculation tests
│   ├── test_io.py              #     I/O and serialization tests
│   ├── test_deterministic.py   #     Deterministic projection tests
│   ├── test_app_integration.py #     UI integration tests
│   ├── test_market_regimes.py  #     Market regime validation tests
│   └── test_user_scenario_debug.py # Comprehensive scenario testing
├── run.sh                      # 🚀 Enhanced launcher script
├── requirements.txt            # 📦 Python dependencies
├── CLAUDE.md                   # 🤖 Technical documentation & context
└── README.md                   # 📖 This file
```

## 🆕 Recent Updates

- **Major Code Refactoring**: Extracted utility functions from giant files, improved maintainability
- **Bug Fixes**: Fixed market regime parameter flow, income streams chart display, Social Security timeline
- **Codebase Cleanup**: Removed 4,191 lines of obsolete code, cleaner project structure
- **Enhanced Testing**: 320+ tests with 72% line coverage, comprehensive market regime validation
- **Social Security Integration**: Full spousal benefits, funding scenarios, state tax modeling

## 🎛️ Configuration

### Portfolio & Spending
- **Start Capital**: $2.5M-$4M presets with custom asset allocation
- **Spending Methods**: CAPE-based (dynamic) or Fixed annual
- **Guyton-Klinger Guardrails**: Upper/lower thresholds with automatic adjustments
- **Market Regimes**: Baseline, Recession/Recovery, Grind-Lower scenarios

### Income & Expenses
- **Multi-year streams**: Overlapping expense/income periods with accurate timing
- **College costs**: Growing expenses with inflation adjustment
- **Inheritance**: Configurable lump sum timing

### Tax Configuration
- **10 State Support**: Combined federal+state rates with progressive brackets
- **Filing Status**: MFJ or Single with standard deduction
- **Gross-up automation**: Solves for pre-tax withdrawal amounts

## 📋 Default Scenario

The application includes a **realistic California family scenario** with:

- **👨‍👩‍👧‍👦 Household**: Married couple, 2 children, $250K annual income
- **💰 Portfolio**: $2.5M at retirement (10x income, strong savers)  
- **🏠 Location**: California (higher costs, taxes, and inflation)
- **⚖️ Allocation**: Age-appropriate 65/25/8/2 (Equity/Bonds/RE/Cash)
- **📚 Expenses**: College costs, home renovation, healthcare upgrades
- **💼 Income**: Part-time consulting and board position income

## 🚦 Usage

### Quick Start
1. Configure portfolio and spending goals
2. Run Monte Carlo simulation
3. Analyze results and success rates
4. Export data or save parameters as JSON

### Advanced Features
- **Scenario Comparison**: Save/load JSON parameters to test variations
- **AI Analysis**: Get Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) for personalized insights
- **Tax Planning**: Compare filing status and model different tax scenarios

## 🧪 Testing

Run the comprehensive test suite with `pytest tests/ -v` (320+ tests covering simulation logic, tax calculations, UI integration, and data management).

## 🚀 Deployment

```bash
# Local development (recommended)
./run.sh

# Production
streamlit run main.py --server.port 8080 --server.address 0.0.0.0

# Docker
FROM python:3.11-slim
COPY requirements.txt . && RUN pip install -r requirements.txt
COPY . . && EXPOSE 8501
CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0"]
```

## 🔧 Technical Details

- **Pure Functions**: Simulation engine decoupled from UI for testability
- **Real Dollar Foundation**: All calculations in real terms, nominal for display
- **CAPE-Based Withdrawal**: `Initial Rate = 1.75% + 0.5 × (1/CAPE)`
- **Performance**: Small sims (<1K) <1s, Medium (≤10K) 2-5s, Large (≤50K) 10-30s

## 🎨 Extensions

The modular architecture supports easy customization of asset classes (`simulation.py`), tax models (`tax.py`), visualizations (`charts.py`), and export formats (`io_utils.py`).

## ⚠️ Important Notes

**Educational Use**: Simplified tax models, not a substitute for professional financial advice. Results should be validated with advisors.

**Privacy**: All calculations performed locally. No personal data stored or transmitted.

**Accuracy**: Combined federal+state tax estimates, Social Security based on 2024-2025 Trustees Reports, real estate treated as REITs.

## 📄 License

**Educational Use License** - This project is provided for educational and personal use. The tax calculations are simplified models and should not be used as a substitute for professional financial or tax advice.

---

**⭐ If you find this tool useful, please star the repository!**

**💬 Questions or suggestions? Open an issue or discussion.**