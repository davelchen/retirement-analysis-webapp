# Retirement Analysis Suite

A comprehensive **Streamlit multipage application** for retirement planning featuring an interactive **Setup Wizard** and advanced **Monte Carlo simulation** with tax-aware withdrawals and Guyton-Klinger guardrails. Seamlessly navigate between guided parameter setup and sophisticated financial analysis.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-Educational-green.svg)
![Tests](https://img.shields.io/badge/tests-255%2B%20passed-brightgreen.svg)
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
- **Main App**: http://localhost:8501 (choose your starting point)
- **Setup Wizard**: http://localhost:8501/Wizard (guided parameter configuration)
- **Monte Carlo Analysis**: http://localhost:8501/Monte_Carlo_Analysis (advanced simulations)

## ✨ Key Features

### 🧙‍♂️ **Interactive Setup Wizard**
- **Step-by-step guidance** through all retirement planning parameters
- **Comprehensive parameter persistence** - all 47+ widgets maintain values through navigation
- **Beautiful visualizations** - pie charts, scatter plots, timelines
- **Educational content** with parameter descriptions and best practices
- **Real-time feedback** showing impact of your choices
- **JSON save/load functionality** with complete parameter preservation
- **Seamless handoff** to Monte Carlo analysis with one click

### 🎲 **Advanced Monte Carlo Engine**
- Up to **50,000 simulations** with configurable market scenarios
- **Tax-aware withdrawal calculations** using progressive brackets
- **Guyton-Klinger guardrails** for dynamic spending adjustments
- **Multiple asset classes** with customizable return assumptions

### 🎯 **Intelligent Tax Modeling**
- **State tax integration** - 10 common states with combined federal+state rates
- **Progressive tax brackets** with automatic updates when state changes
- **Gross-up solver** automatically calculates pre-tax withdrawals
- **Standard deduction** and filing status support
- **Real-time tax impact** analysis in projections

### 🏛️ **Social Security Integration**
- **Comprehensive modeling** with primary and spousal benefits
- **4 funding scenarios** based on 2024-2025 Trustees Report projections
- **Trust fund timeline** modeling 2034 depletion with benefit cuts
- **Age flexibility** - start benefits anywhere from 62-70
- **Tax-aware integration** - SS income reduces portfolio withdrawals

### 📊 **Rich Interactive UI**
- **Comprehensive tooltips** for every parameter with usage guidance
- **Dynamic expense management** - add/remove one-time expenses
- **Multiple income streams** with flexible timing
- **Real-time validation** and helpful error messages

### 📈 **Professional Visualizations**
- **Interactive Plotly charts** with hover details
- **Wealth distribution histograms** and percentile bands
- **Withdrawal rate tracking** with guardrail visualization
- **Year-by-year detailed tables** with real/nominal views
- **Percentile path analysis** - P10/P50/P90 scenario selection for pessimistic, median, and optimistic projections

### 💾 **Data Management**
- **JSON parameter save/load** for scenario comparison
- **CSV exports** for external analysis
- **Comprehensive reporting** with summary statistics
- **Reproducible results** with optional random seeds
- **"Pick up where you left off"** - upload JSON files in wizard welcome page

### 🤖 **AI-Powered Analysis**
- **Google Gemini Integration** with manual trigger controls
- **Multiple model options** - Gemini 2.5 Pro, Flash variants with performance descriptions
- **Usage tracking** - real-time token consumption and daily quota monitoring
- **Privacy protection** - comprehensive warnings about free tier data usage
- **Interactive chat** - Q&A interface with context-aware responses about your results
- **Smart error handling** - graceful fallbacks with detailed guidance

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
├── charts.py                   # 📈 Plotly visualization builders
├── io_utils.py                 # 💾 Data import/export & JSON conversion
├── ai_analysis.py              # 🤖 Google Gemini AI integration & usage tracking
├── tests/                      # 🧪 Comprehensive test suite (240+ tests)
│   ├── test_simulation.py      #     Core simulation tests
│   ├── test_tax.py             #     Tax calculation tests
│   ├── test_io.py              #     I/O and serialization tests
│   ├── test_deterministic.py   #     Deterministic projection tests
│   └── test_app_integration.py #     UI integration tests
├── run.sh                      # 🚀 Enhanced launcher script
├── requirements.txt            # 📦 Python dependencies
├── CLAUDE.md                   # 🤖 Technical documentation & context
├── WIZARD_README.md            # 🧙‍♂️ Setup wizard documentation
└── README.md                   # 📖 This file
```

## 🆕 What's New (September 2025)

### 🔄 **Comprehensive Parameter Management Overhaul**
- **Universal Widget Persistence**: All 47+ wizard widgets now maintain values through navigation
- **Eliminated Race Conditions**: Complete fix for widget persistence issues that caused value resets
- **Enhanced JSON Saving**: Both wizard and simulation save functions capture ALL parameters
- **Robust Parameter Loading**: Support for both wizard nested JSON and simulation flat JSON formats
- **Round-Trip Reliability**: Complete parameter lifecycle testing ensures data integrity
- **No More Partial Fixes**: Systematic architectural solution prevents future persistence issues

### 🎨 **User Experience Improvements**
- **Consistent Parameter Preservation**: Inheritance amounts, Social Security settings, and all other inputs persist correctly
- **Comprehensive Tooltips**: Enhanced CAPE ratio explanations and parameter guidance
- **JSON Format Consistency**: Unified JSON structure between wizard and simulation save functions
- **Immediate Sync Patterns**: Real-time parameter synchronization prevents data loss

### JSON Compatibility Layer
- **Auto-detection**: Wizard JSON (nested) vs Native JSON (flat) formats
- **Parameter mapping**: 30+ parameter name conversions handled automatically
- **Seamless handoff**: Parameters flow directly between wizard and analysis
- **Backward compatibility**: Existing configuration files continue to work

## 🎛️ Configuration Options

### 💼 **Portfolio Setup** 
- **Start Capital**: $2.5M - $4M presets (or custom)
- **Asset Allocation**: Equity/Bonds/Real Estate/Cash with validation
- **Return Models**: Configurable means & volatilities per asset class
- **Market Regimes**: Baseline, Recession/Recovery, Grind-Lower scenarios

### 💸 **Spending Framework**
- **Three Spending Methods**: CAPE-based (with guardrails), Fixed annual (no guardrails), or Manual initial (legacy)
- **CAPE-Based Initial Rate**: Dynamic withdrawal rate based on market valuation (1.75% + 0.5/CAPE)
- **Guyton-Klinger Guardrails**: Upper/lower thresholds with automatic adjustments (CAPE & manual modes only)
- **Spending Bounds**: Floor/ceiling limits with time constraints
- **College Expenses**: Growing costs (2032-2041) with inflation adjustment

### 🏠 **Income & Expenses**
- **Multi-Year Expense Streams**: Comprehensive support for overlapping expense periods with accurate timing
- **Multiple Income Streams**: Part-time work, consulting, board positions with proper start year/duration handling
- **Real Estate Cash Flow**: Ramp or delayed income patterns
- **Robust Stream Testing**: 240+ tests ensure accurate timing, edge case handling, and full simulation integration
- **Inheritance Planning**: Configurable lump sum timing

### 🧮 **Tax Configuration**
- **Filing Status**: MFJ or Single with appropriate brackets
- **Progressive Brackets**: 3-tier configurable system
- **Standard Deduction**: Adjustable based on tax year
- **Gross-Up Automation**: Solves for pre-tax withdrawal amounts

## 📋 Default Scenario

The application includes a **realistic California family scenario** with:

- **👨‍👩‍👧‍👦 Household**: Married couple, 2 children, $250K annual income
- **💰 Portfolio**: $2.5M at retirement (10x income, strong savers)  
- **🏠 Location**: California (higher costs, taxes, and inflation)
- **⚖️ Allocation**: Age-appropriate 65/25/8/2 (Equity/Bonds/RE/Cash)
- **📚 Expenses**: College costs, home renovation, healthcare upgrades
- **💼 Income**: Part-time consulting and board position income

## 🚦 Usage Examples

### **Basic Retirement Analysis**
1. **Configure Portfolio**: Set start capital and allocation weights
2. **Set Spending Goals**: Define floor, ceiling, and guardrails  
3. **Run Simulation**: Click "🚀 Run Simulation" for Monte Carlo analysis
4. **Analyze Results**: Review success rates and wealth projections

### **Tax-Aware Planning**
- **Optimize Withdrawals**: System automatically calculates gross withdrawals
- **Compare Filing Status**: Test MFJ vs Single impact
- **Bracket Planning**: Model different tax scenarios
- **View Effective Rates**: Year-by-year tax burden analysis

### **Scenario Comparison**
- **Save Base Case**: Export parameters as JSON via Download button
- **Test Variations**: Modify assumptions (market regime, spending, etc.)
- **Load & Compare**: Upload JSON file and click "Load Parameters" button
- **Export Results**: Download CSV data for external analysis

### **Advanced Modeling**
- **Market Regime Testing**: Model recession, recovery, and grind scenarios
- **Expense Planning**: Add multiple one-time expenses with custom timing
- **Income Optimization**: Model part-time work and consulting income
- **Inheritance Impact**: Test timing and amount sensitivity

### **AI-Enhanced Analysis**
- **Setup AI**: Enable AI analysis and enter free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Manual Trigger**: Click "🧠 Run AI Analysis" button after running simulation for personalized insights
- **Monitor Usage**: Track token consumption and daily quota with real-time warnings
- **Interactive Chat**: Ask follow-up questions about your retirement plan with context-aware responses
- **Privacy Control**: Review comprehensive warnings about free tier data usage before enabling

## 🧪 Testing & Validation

**255+ comprehensive unit tests** covering all major functionality:

```bash
# Run complete test suite
pytest tests/ -v

# Run with coverage report
pytest --cov=. --cov-report=html tests/

# Test specific module
pytest tests/test_simulation.py -v
```

**Test Coverage Areas:**
- ✅ **Monte Carlo Engine** (60+ tests): Simulation logic, guardrails, regimes, percentile paths, income/expense streams
- ✅ **Tax Calculations** (30+ tests): Progressive brackets, gross-up solver, state taxes
- ✅ **Data Management** (25+ tests): Parameter serialization, CSV exports, array length validation
- ✅ **Deterministic Models** (16+ tests): Expected return projections, Social Security integration
- ✅ **UI Integration** (40+ tests): Parameter conversion, wizard transitions, type safety
- ✅ **AI Analysis** (25+ tests): Gemini integration, error handling, usage tracking
- ✅ **App Functions** (15+ tests): State tax rates, Social Security calculations
- ✅ **Stream Robustness** (10+ tests): Income/expense stream timing, overlaps, edge cases, full simulation integration
- ✅ **Widget Persistence** (9+ tests): Streamlit widget behavior patterns, session state management, persistence validation
- ✅ **Parameter Validation** (20+ tests): Input validation, edge cases, error handling

## 🚀 Deployment & Configuration

### Local Development
```bash
# Recommended: Use enhanced launcher
./run.sh

# Or run directly
streamlit run main.py
```

### Production Deployment
```bash
# Custom port and host
streamlit run main.py --server.port 8080 --server.address 0.0.0.0

# With configuration options
streamlit run main.py --server.maxUploadSize=200 --server.maxMessageSize=200
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0"]
```

### Environment Configuration
```bash
# Optional environment variables
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Personal configuration (auto-loads on startup)
# Create default.json in project root (ignored by git)
```

## 🔧 Technical Architecture

### **🎯 Design Principles**
- **Pure Functions**: Simulation engine decoupled from UI for testability
- **Real Dollar Foundation**: All calculations in real terms, nominal for display  
- **Modular Components**: Easy to extend with new features
- **Robust Numerics**: Bisection solver for tax gross-up calculations
- **Performance Optimized**: Vectorized NumPy operations for large simulations

### **📊 Mathematical Models**
- **CAPE-Based Withdrawal**: `Initial Rate = 1.75% + 0.5 × (1/CAPE)`
- **Guyton-Klinger Guardrails**: Dynamic spending based on withdrawal rate bands
- **Progressive Taxation**: Multi-bracket system with gross-up automation
- **Monte Carlo**: Correlated asset returns with regime-based adjustments

### **⚡ Performance Benchmarks**
- **Small Sims** (≤1,000): < 1 second  
- **Medium Sims** (≤10,000): 2-5 seconds ⭐ *Recommended*
- **Large Sims** (≤50,000): 10-30 seconds (high precision)

## 🎨 Customization & Extensions

The modular architecture supports easy customization:

### **📈 New Asset Classes**
```python
# Add new asset class in simulation.py
new_asset_mean = 0.045
new_asset_vol = 0.12
# Update allocation logic and UI
```

### **🧮 Enhanced Tax Models**
```python
# Extend tax.py for capital gains, Roth conversions
def calculate_capital_gains_tax(gains, holding_period):
    # Long-term vs short-term capital gains
    pass

def calculate_roth_conversion_tax(conversion_amount):
    # Tax implications of Roth conversions
    pass
```

### **📊 Additional Charts**
```python
# Add new visualizations in charts.py
def create_risk_return_scatter(returns, risks):
    # Custom Plotly chart
    pass
```

### **💾 New Export Formats**
```python
# Extend io_utils.py for Excel, PDF exports
def export_excel_workbook(results):
    # Multi-sheet Excel export
    pass
```

## ⚠️ Important Notes

### **📚 Educational Purpose**
- This tool is for **educational and personal use**
- Tax calculations are **simplified models**
- **Not a substitute** for professional financial advice
- Results should be **validated with financial advisors**

### **🔒 Privacy & Security**  
- **No personal data** stored or transmitted
- All calculations performed **locally**
- Parameters can be saved/loaded as **local JSON files**
- **Git ignored** personal configuration files

### **🎯 Accuracy Considerations**
- **Simplified tax model** (combined federal+state rates, basic brackets)
- **State tax estimates** are rough approximations for retirement income
- **Social Security projections** based on current Trustees Reports (2024-2025)
- **Real estate** treated as REITs, not direct ownership
- **Inflation assumptions** may vary from actual experience

## 🤝 Contributing

Contributions welcome! Areas for enhancement:

- 📊 **Additional asset classes** (commodities, international bonds)
- 🎨 **Enhanced visualizations** (risk/return charts, Monte Carlo paths)
- 🧮 **Advanced tax modeling** (capital gains, Roth conversions)
- 🔬 **Healthcare cost modeling** with inflation projections
- 🌎 **International tax considerations** for expats
- 📱 **Mobile responsive** design improvements

## 📄 License

**Educational Use License** - This project is provided for educational and personal use. The tax calculations are simplified models and should not be used as a substitute for professional financial or tax advice.

---

**⭐ If you find this tool useful, please star the repository!**

**💬 Questions or suggestions? Open an issue or discussion.**