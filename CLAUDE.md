# Claude Code Context - Monte Carlo Retirement Simulator

## Project Overview
Comprehensive Streamlit web application for retirement planning using Monte Carlo simulation. Features tax-aware withdrawals, Guyton-Klinger guardrails, Social Security modeling, and interactive visualizations.

## Core Architecture

### Multipage Design
- **Unified application**: Single Streamlit app (`main.py`) with wizard and analysis pages
- **Direct parameter sharing**: Session state transfer between pages, no JSON handoff required
- **Pure functions**: Simulation engine decoupled from UI for testability
- **Real dollar foundation**: All calculations in real terms, nominal for display only

### Key Components
- `main.py`: Multipage application entry point
- `pages/wizard.py`: Interactive setup with parameter configuration and JSON loading
- `pages/monte_carlo.py`: Monte Carlo analysis with visualizations and AI triggers
- `simulation.py`: Monte Carlo engine with vectorized NumPy operations
- `tax.py`: Progressive tax model with bisection solver for gross-up calculations
- `deterministic.py`: Expected-return projections
- `charts.py`: Interactive Plotly visualizations
- `io_utils.py`: JSON/CSV utilities with wizard JSON conversion
- `ai_analysis.py`: Google Gemini AI integration with usage tracking

### Testing Strategy
Comprehensive test suite with 270+ unit tests covering simulation logic, tax calculations, Social Security modeling, parameter serialization, UI integration, market regimes, and stream timing.

## Critical Technical Patterns

### Streamlit Widget Persistence Pattern (CRITICAL)
**Hard-learned lesson preventing widget "jumping" and double-click issues:**

```python
# ✅ CORRECT: Complete persistence pattern
widget_value = st.slider(
    "Label",
    value=st.session_state.wizard_params.get('param_key', default),  # Persistent source of truth
    key="widget_key"  # Widget identity for Streamlit
)

# Immediate sync with change check (prevents unnecessary writes)
if widget_value != st.session_state.wizard_params.get('param_key'):
    st.session_state.wizard_params['param_key'] = widget_value
```

**Why This Works:**
- `wizard_params` survives navigation, widget keys may get cleared
- Value parameter restores widget when key is cleared
- Immediate sync prevents circular references
- Change check optimizes performance

**Key Streamlit Behaviors:**
1. Widget keys cleared when widgets don't render (navigation)
2. Value/key conflicts cause Streamlit to reset widget key
3. Use session state flags for one-time operations
4. Always ensure list parameters are `[]` not `None`

### Parameter Flow Architecture
**JSON Compatibility Layer:**
- Auto-detection of wizard vs native JSON formats
- Parameter mapping handles 30+ name conversions
- Structure flattening from nested to flat SimulationParams
- Seamless handoff between wizard and analysis pages

### Social Security Age Independence
**Fixed Critical Bug (September 2025):**
- Problem: SS calculations hardcoded `age = 65 + (year - start_year)`
- Solution: `age_at_year = retirement_age + (year - start_year)`
- Impact: Proper handling of early retirement scenarios (e.g., retire at 45, SS at 67 = 22 years)

## Implementation Details

### Tax System
3-bracket progressive model with state tax integration:
- **10 states supported**: CA, NY, TX, FL, WA, NV, PA, OH, IL + Federal Only
- **Combined rates**: Federal + state effective rates (CA/NY up to 36%, no-tax states 10-24%)
- **Gross-up solver**: Bisection method to find pre-tax withdrawal amounts

### Social Security Modeling
**Architecture Improvements:**
- Retirement age independence (fixed hardcoded age=65)
- Year-by-year tracking in tables and CSV exports
- 4 funding scenarios: Conservative (19% cut 2034), Moderate, Optimistic, Custom
- Age flexibility: Start ages 62-70 with actuarial adjustments
- Spousal benefits with separate tracking

### Spending Methods
- **CAPE-based**: Market valuation sets initial rate (3.2% + 0.5/CAPE) with guardrails
- **Fixed annual**: Constant spending, no guardrail adjustments
- **Manual initial**: User-defined rate with guardrails (legacy)

### Monte Carlo Engine
Vectorized operations: Small sims (≤1K) <1s, Medium (≤10K) 2-5s, Large (≤50K) 10-30s

## UI Features

### Intelligent Validation
**Age-Aware Horizon Validation:**
- Young retirees (<50) warned for short horizons (<40 years)
- Longevity risk alerts if planning doesn't reach age 80
- Positive reinforcement for excellent planning (age 90+)
- Flexible for late retirees (65+)

### Advanced Visualizations
- Terminal wealth distribution with KDE overlay
- Wealth percentile bands (P10/P50/P90 trajectories)
- Monte Carlo path samples with confidence bands
- Success probability over time
- Cash flow waterfall with income/expense breakdown
- Sequence of returns and drawdown analysis

### Dynamic Cash Flow Management
- Multi-year expense streams with start year and duration
- Multiple income sources with overlapping period support
- Robust timing calculations with edge case protection
- CAPE-based vs fixed spending with conditional UI

## Data Management

### Parameter Persistence
- JSON save/load for scenario comparison
- Auto-load from `default.json` if available
- Wizard JSON conversion with backward compatibility
- Privacy protection (personal files ignored in git)

### AI Analysis Features
- Google Gemini integration with usage tracking
- Manual trigger controls separated from simulation
- Privacy warnings for free tier data usage
- Model selection (Gemini 2.5 Pro, Flash variants)
- Chat interface with context-aware responses

## Common Commands

### Running Application
```bash
./run.sh  # Recommended launcher
# Or: streamlit run main.py
# Open: http://localhost:8501
```

### Testing
```bash
pytest tests/ -v  # Full suite
pytest tests/test_simulation.py -v  # Specific module
```

## Critical Fixes & Patterns

### Market Regime Parameter Flow
**Fixed**: Missing `.get()` defaults caused regimes not to apply
**Solution**: `regime=st.session_state.get('regime', 'baseline')` with proper fallbacks

### CSV Export Array Length
**Fixed**: Years array length mismatch in percentile bands export
**Solution**: Use `results.wealth_paths.shape[1]` instead of calculated lengths

### Widget Persistence Race Conditions
**Fixed**: Global sync overwrote immediate sync widgets
**Solution**: Skip list excludes widgets with immediate sync patterns

### Stream Safety Pattern
```python
# Always ensure streams are lists, never None
streams = st.session_state.other_income_streams if st.session_state.other_income_streams else []
```

## Security & Privacy
- No personal data stored or transmitted
- All calculations performed locally
- Git ignores personal configuration files
- API key protection with .gitignore validation
- Educational use disclaimer

## Extension Points
- New asset classes: Update `simulation.py` return models
- Enhanced tax models: Extend `tax.py` for capital gains, Roth conversions
- Additional visualizations: Create new chart types in `charts.py`
- Export formats: Extend `io_utils.py` for Excel, PDF outputs

This project demonstrates comprehensive financial modeling with professional software engineering practices including modular design, extensive testing, and user-friendly interfaces.