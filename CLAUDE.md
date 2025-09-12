# Claude Code Context - Monte Carlo Retirement Simulator

## Project Overview
This is a comprehensive Streamlit web application for retirement planning using Monte Carlo simulation. Built for educational and personal use, it features tax-aware withdrawals, Guyton-Klinger guardrails, and interactive visualizations.

## Key Architecture Decisions

### Modular Design
- **Pure functions**: Simulation engine decoupled from UI for testability
- **Separation of concerns**: Each module has single responsibility
- **Real dollar foundation**: All calculations in real terms, nominal for display only

### Core Components
- `app.py`: Streamlit UI with rich tooltips and dynamic expense/income management
- `simulation.py`: Monte Carlo engine with vectorized NumPy operations
- `tax.py`: Progressive tax model with bisection solver for gross-up calculations
- `deterministic.py`: Expected-return projections without randomness
- `charts.py`: Interactive Plotly visualizations
- `io_utils.py`: JSON/CSV data management utilities

### Testing Strategy
Comprehensive test suite with 100+ unit tests covering:
- Monte Carlo simulation logic and edge cases
- Tax calculations and gross-up solver accuracy
- Parameter serialization/deserialization
- UI integration and data structures
- Deterministic projection validation
- Chart generation and visualization functions
- Market regime scenarios and custom configurations
- College and real estate flow toggle functionality

## Implementation Notes

### Tax Calculation System
Uses simplified 3-bracket progressive model with automatic gross-up solver:
```python
def solve_gross_withdrawal(net_need, other_taxable_income, standard_deduction, tax_brackets):
    # Bisection method to find pre-tax withdrawal amount
```

### Monte Carlo Engine
Vectorized operations for performance:
- Small sims (≤1K): <1 second
- Medium sims (≤10K): 2-5 seconds (recommended)
- Large sims (≤50K): 10-30 seconds

### Guyton-Klinger Guardrails
Dynamic spending adjustments based on withdrawal rate bands:
- Upper guardrail: Increase spending when WR drops below threshold
- Lower guardrail: Decrease spending when WR exceeds threshold
- Configurable adjustment percentages and spending bounds

## UI Features

### Rich Tooltips
Every parameter includes detailed explanations with usage guidance and examples.

### Dynamic Management
- **Multi-year expense streams**: Annual amount, start year, and duration (like income streams)
- **Income streams**: Multiple sources with start year, duration, and amounts
- **Overlapping support**: Multiple expense periods with accurate yearly totals
- **Aggregation logic**: UI data structures converted to simulation parameters

### Advanced Visualization Suite
- **Terminal Wealth Distribution**: High-resolution histograms (100-200 bins) with kernel density estimation (KDE) overlay, comprehensive percentile analysis, and failure threshold visualization
- **Wealth Percentile Bands**: Interactive timeline showing P10/P50/P90 wealth trajectories over time
- **Monte Carlo Path Samples**: Representative simulation paths with confidence bands for intuitive understanding
- **Success Probability Over Time**: Probability of maintaining different wealth thresholds throughout retirement
- **Cash Flow Waterfall**: Year-by-year breakdown showing income sources, expenses, taxes, and portfolio changes
- **Sequence of Returns Analysis**: Impact of return timing on final outcomes with early/late return grouping
- **Drawdown Analysis**: Maximum portfolio decline analysis with percentile bands
- **Year-by-year detailed tables**: Real/nominal views with comprehensive financial breakdown
- **Success rate and guardrail statistics**: Portfolio sustainability metrics

## Data Management

### Parameter Persistence
JSON save/load for scenario comparison and reproducible results.
- Save: Download parameters JSON via button
- Load: Upload JSON file, then click "Load Parameters" button for confirmation
- Auto-load: Place personal config in `default.json` for automatic startup loading

### Privacy Protection
Personal configuration files ignored in git:
- `default.json` (personal configuration, auto-loaded on startup)
- `*_personal_*.json`, `*_confidential_*.json` patterns
- Simulation output files

### Default Scenario
Hypothetical California family:
- $250K annual income, $2.5M portfolio at retirement
- 65/25/8/2 allocation (Equity/Bonds/RE/Cash)
- College expenses, home renovation, healthcare costs
- Part-time consulting and board position income

## Common Commands

### Running the Application
```bash
streamlit run app.py
# Open browser to http://localhost:8501
```

### Testing
```bash
# Full test suite
pytest tests/ -v

# With coverage
pytest --cov=. --cov-report=html tests/

# Specific module
pytest tests/test_simulation.py -v
```

### Development Notes
- Uses session state for UI persistence
- All monetary values in real dollars unless specified
- Inflation adjustments applied for display only
- Random seed support for reproducible results

## Troubleshooting

### Common Issues
1. **Charts not displaying**: Check for proper data types in visualization functions
2. **Tax calculation errors**: Verify bracket thresholds and rates are positive
3. **Performance issues**: Reduce simulation count for faster iterations
4. **Parameter validation**: Check year ranges and positive amounts
5. **Parameter loading**: Upload JSON file, then click "Load Parameters" button to confirm

### Test Failures
- Most common cause: NumPy percentile calculation precision differences
- Fix: Adjust test tolerances for floating-point comparisons
- UI tests: Ensure proper session state initialization

## Extension Points

### New Asset Classes
Add to `simulation.py` return model parameters and update allocation logic.

### Enhanced Tax Models
Extend `tax.py` for state taxes, capital gains, or Roth conversions.

### Additional Visualizations
Create new chart types in `charts.py` using Plotly.

### Export Formats
Extend `io_utils.py` for Excel, PDF, or other output formats.

## Security Considerations
- No personal data stored or transmitted
- All calculations performed locally
- Git ignores personal configuration files
- Educational use disclaimer included

This project demonstrates comprehensive financial modeling with professional software engineering practices including modular design, extensive testing, and user-friendly interfaces.

## Recent Major Updates

### Enhanced Visualization Suite (Latest)
- **High-resolution charts**: Terminal wealth distribution with 100-200 bins and kernel density overlay
- **New chart types**: 5 additional visualizations including Monte Carlo path samples, success probability over time, cash flow waterfall, sequence of returns analysis, and drawdown analysis
- **Improved rendering**: Fixed overlapping elements with clean subtitle formatting
- **Statistical depth**: Comprehensive percentile analysis and failure threshold visualization
- **Interactive elements**: Hover details and dynamic chart controls

### Advanced Market Regime Modeling
- **8 predefined scenarios**: baseline, recession_recover, grind_lower, late_recession, inflation_shock, long_bear, tech_bubble, plus custom
- **Finer-grained control**: Custom regime builder with shock timing, duration, recovery patterns
- **Realistic patterns**: Each regime models different economic environments (early recession, late recession, prolonged inflation, tech bubbles)
- **Parameter flexibility**: Custom shock years, return adjustments, recovery periods
- **Testing coverage**: Comprehensive tests for all regime scenarios

### Enhanced College Expense Controls
- **Toggle capability**: Complete on/off control for college expenses
- **Custom parameters**: Configurable base amount, start/end years, growth rates
- **Flexible timing**: Not limited to 2032-2041 default period
- **Integration**: Works seamlessly with existing expense stream architecture
- **UI enhancements**: Expandable section with detailed controls

### Real Estate Cash Flow Enhancement
- **Toggle on/off**: Complete control over RE income inclusion
- **Custom ramp patterns**: Year 1, Year 2, and steady-state amounts
- **Flexible timing**: Configurable start years and delay periods
- **Preset options**: Ramp, delayed, and custom configuration modes
- **Enhanced UI**: Better organization and control over RE parameters

### Multi-Year Expense Streams (Previous)
- **Replaced**: Hardcoded `onetime_2033`/`onetime_2040` parameters
- **With**: Dynamic `expense_streams` architecture supporting any year/duration
- **Benefits**: True multi-year planning, overlapping expense support, college-ready
- **UI**: "Multi-Year Expenses" section matching "Other Income" structure
- **Testing**: Comprehensive test coverage for multi-year scenarios

### Parameter Management Improvements
- **Auto-load defaults**: App automatically loads `default.json` on startup if available
- **Enhanced loading**: Load Parameters confirmation button prevents accidental overwrites
- **Complete mapping**: All SimulationParams fields properly supported in JSON I/O
- **Privacy protection**: `default.json` ignored by git for personal data security
- **Backward compatibility**: Works with or without personal configuration files

### CAPE Ratio Implementation Notes
- **Current usage**: CAPE sets initial withdrawal rate via `0.0175 + 0.5 * (1.0 / cape_now)`
- **Static during simulation**: CAPE value doesn't evolve during the 50-year projection
- **Not regime-dependent**: Market regimes affect returns but not CAPE trajectory
- **Enhancement opportunity**: Could implement dynamic CAPE evolution based on market performance