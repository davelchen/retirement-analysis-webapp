# Monte Carlo Retirement Simulator

A comprehensive **Streamlit web application** for retirement planning using Monte Carlo simulation with **tax-aware withdrawals** and **Guyton-Klinger guardrails**. Features an intuitive UI with rich parameter tooltips, multiple expense/income management, and interactive visualizations.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-Educational-green.svg)
![Tests](https://img.shields.io/badge/tests-89%20passed-brightgreen.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.49+-red.svg)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/username/retirement-simulator.git
cd retirement-simulator

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

**Open your browser to `http://localhost:8501`**

## ✨ Key Features

### 🎲 **Advanced Monte Carlo Engine**
- Up to **50,000 simulations** with configurable market scenarios
- **Tax-aware withdrawal calculations** using progressive brackets
- **Guyton-Klinger guardrails** for dynamic spending adjustments
- **Multiple asset classes** with customizable return assumptions

### 🎯 **Intelligent Tax Modeling**
- **Progressive tax brackets** (federal, configurable)
- **Gross-up solver** automatically calculates pre-tax withdrawals
- **Standard deduction** and filing status support
- **Real-time tax impact** analysis in projections

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

### 💾 **Data Management**
- **JSON parameter save/load** for scenario comparison
- **CSV exports** for external analysis
- **Comprehensive reporting** with summary statistics
- **Reproducible results** with optional random seeds

## 🏗️ Project Structure

```
├── app.py                      # 🖥️  Main Streamlit application
├── simulation.py               # 🎲 Monte Carlo simulation engine
├── deterministic.py            # 📊 Expected-return projections
├── tax.py                      # 💰 Tax calculations & gross-up solver
├── charts.py                   # 📈 Plotly visualization builders
├── io_utils.py                 # 💾 Data import/export utilities
├── tests/                      # 🧪 Comprehensive test suite
│   ├── test_simulation.py      #     Core simulation tests
│   ├── test_tax.py             #     Tax calculation tests  
│   ├── test_io.py              #     I/O and serialization tests
│   ├── test_deterministic.py   #     Deterministic projection tests
│   └── test_app_integration.py #     UI integration tests
├── requirements.txt            # 📦 Python dependencies
├── .gitignore                  # 🚫 Git ignore patterns
└── README.md                   # 📖 This file
```

## 🎛️ Configuration Options

### 💼 **Portfolio Setup** 
- **Start Capital**: $2.5M - $4M presets (or custom)
- **Asset Allocation**: Equity/Bonds/Real Estate/Cash with validation
- **Return Models**: Configurable means & volatilities per asset class
- **Market Regimes**: Baseline, Recession/Recovery, Grind-Lower scenarios

### 💸 **Spending Framework**
- **CAPE-Based Initial Rate**: Dynamic withdrawal rate based on market valuation
- **Guardrails**: Upper/lower thresholds with automatic adjustments
- **Spending Bounds**: Floor/ceiling limits with time constraints
- **College Expenses**: Growing costs (2032-2041) with inflation adjustment

### 🏠 **Income & Expenses**
- **Multiple One-Time Expenses**: Add/remove with custom years and amounts
- **Flexible Income Streams**: Part-time work, consulting, board positions
- **Real Estate Cash Flow**: Ramp or delayed income patterns
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

## 🧪 Testing & Validation

**89 comprehensive unit tests** covering all major functionality:

```bash
# Run complete test suite
pytest tests/ -v

# Run with coverage report
pytest --cov=. --cov-report=html tests/

# Test specific module
pytest tests/test_simulation.py -v
```

**Test Coverage Areas:**
- ✅ **Monte Carlo Engine** (26 tests): Simulation logic, guardrails, regimes
- ✅ **Tax Calculations** (24 tests): Progressive brackets, gross-up solver
- ✅ **Data Management** (14 tests): Parameter serialization, CSV exports
- ✅ **Deterministic Models** (14 tests): Expected return projections  
- ✅ **UI Integration** (11 tests): Parameter conversion, validation

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
# Extend tax.py for state taxes, capital gains
def calculate_state_tax(income, state):
    # Custom state tax logic
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
- **Simplified tax model** (federal only, basic brackets)
- **No state tax calculations** (user should adjust brackets)
- **Real estate** treated as REITs, not direct ownership
- **Inflation assumptions** may vary from actual experience

## 🤝 Contributing

Contributions welcome! Areas for enhancement:

- 🏛️ **State tax modules** for different jurisdictions
- 📊 **Additional asset classes** (commodities, international bonds)
- 🎨 **Enhanced visualizations** (risk/return charts, Monte Carlo paths)
- 🧮 **Advanced tax modeling** (capital gains, Roth conversions)
- 📱 **Mobile responsive** design improvements

## 📄 License

**Educational Use License** - This project is provided for educational and personal use. The tax calculations are simplified models and should not be used as a substitute for professional financial or tax advice.

---

**⭐ If you find this tool useful, please star the repository!**

**💬 Questions or suggestions? Open an issue or discussion.**