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
89 comprehensive unit tests covering:
- Monte Carlo simulation logic and edge cases
- Tax calculations and gross-up solver accuracy
- Parameter serialization/deserialization
- UI integration and data structures
- Deterministic projection validation

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

### Visualization Suite
- Wealth distribution histograms with percentile bands
- Interactive timeline charts with hover details
- Year-by-year detailed tables (real/nominal views)
- Success rate and guardrail hit statistics

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

### Multi-Year Expense Streams (Latest)
- **Replaced**: Hardcoded `onetime_2033`/`onetime_2040` parameters
- **With**: Dynamic `expense_streams` architecture supporting any year/duration
- **Benefits**: True multi-year planning, overlapping expense support, college-ready
- **UI**: "Multi-Year Expenses" section matching "Other Income" structure
- **Testing**: All 90 tests passing, including new multi-year scenarios

### College Expense Modeling  
- **Built-in system**: `college_growth_real` handles 2032-2041 with inflation
- **Personal config**: Uses existing college system, no duplicate modeling
- **Flexible**: Expense streams available for other multi-year costs

### Parameter Loading Enhancement
- **Added**: Load Parameters confirmation button (no auto-loading)
- **Fixed**: Complete parameter mapping for all SimulationParams fields
- **UI**: Shows file info before user confirms loading

### Automatic Default Configuration (Latest)
- **Auto-load**: App automatically loads `default.json` on startup if it exists
- **Fallback**: Uses hardcoded defaults if `default.json` missing or invalid
- **Privacy**: `default.json` ignored by git for personal data protection
- **Seamless**: No UI changes required - parameters load transparently
- **Backward compatible**: Works with or without `default.json`