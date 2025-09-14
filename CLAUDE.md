# Claude Code Context - Monte Carlo Retirement Simulator

## Project Overview
This is a comprehensive Streamlit web application for retirement planning using Monte Carlo simulation. Built for educational and personal use, it features tax-aware withdrawals, Guyton-Klinger guardrails, and interactive visualizations.

## Key Architecture Decisions

### Multipage Design
- **Unified application**: Single Streamlit app with multiple pages for seamless navigation
- **Direct parameter sharing**: No JSON file handoff required between wizard and analysis
- **Pure functions**: Simulation engine decoupled from UI for testability
- **Separation of concerns**: Each module has single responsibility
- **Real dollar foundation**: All calculations in real terms, nominal for display only

### Core Components
- `main.py`: Streamlit multipage application entry point with page navigation
- `pages/wizard.py`: Interactive setup wizard with parameter configuration and JSON loading
- `pages/monte_carlo.py`: Monte Carlo analysis with advanced visualizations and manual AI triggers
- `simulation.py`: Monte Carlo engine with vectorized NumPy operations
- `tax.py`: Progressive tax model with bisection solver for gross-up calculations
- `deterministic.py`: Expected-return projections without randomness
- `charts.py`: Interactive Plotly visualizations with percentile path analysis
- `io_utils.py`: JSON/CSV data management utilities with wizard JSON conversion
- `ai_analysis.py`: Google Gemini AI integration with usage tracking and privacy controls

### Testing Strategy
Comprehensive test suite with 100+ unit tests covering:
- Monte Carlo simulation logic and edge cases
- Tax calculations and gross-up solver accuracy
- State tax integration and rate calculations
- Social Security benefit modeling with funding scenarios
- Parameter serialization/deserialization
- UI integration and data structures
- Deterministic projection validation
- Chart generation and visualization functions
- Market regime scenarios and custom configurations
- College and real estate flow toggle functionality
- Spousal Social Security integration

## Implementation Notes

### Tax Calculation System
Uses simplified 3-bracket progressive model with automatic gross-up solver and state tax integration:
```python
def solve_gross_withdrawal(net_need, other_taxable_income, standard_deduction, tax_brackets):
    # Bisection method to find pre-tax withdrawal amount
```

**State Tax Integration**:
- **10 states supported**: CA, NY, TX, FL, WA, NV, PA, OH, IL + Federal Only
- **Combined rates**: Rough estimates of federal + state effective tax rates
- **Auto-updating brackets**: Tax brackets automatically adjust when state changes
- **High-tax states**: CA/NY with rates up to 36% combined
- **No-tax states**: TX/FL/WA/NV using federal-only rates (10-24%)
- **Moderate states**: PA/OH/IL with intermediate combined rates

### Social Security Modeling
Comprehensive Social Security integration with projected trust fund scenarios based on 2024-2025 Trustees Reports:

**Funding Scenarios**:
- **Conservative (19% cut)**: Full benefit reduction starting 2034 per current law
- **Moderate (gradual reform)**: Partial cuts with Congressional intervention
- **Optimistic (full reform)**: Benefits maintained through tax increases
- **Custom**: User-defined reduction percentage and timing

**Key Features**:
- **Age flexibility**: Start benefits ages 62-70 with proper actuarial adjustments
- **Spousal benefits**: Separate tracking for spouse's Social Security income
- **Trust fund modeling**: Projects 2034 depletion timeline with scenario-based cuts
- **Tax integration**: SS income reduces portfolio withdrawal requirements
- **Real-dollar calculations**: Benefits subject to same funding scenarios

```python
def calculate_social_security_benefit(year, start_year, annual_benefit, scenario,
                                    custom_reduction, reduction_start_year, start_age):
    # Age-based eligibility with funding scenario adjustments
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

### Tax and Social Security UI
- **State tax dropdown**: 10 common states with automatic bracket updates
- **Social Security configuration**: Primary and spousal benefit modeling
- **Funding scenario selection**: 4 options based on Congressional Budget Office projections
- **Age customization**: Flexible start ages (62-70) for both spouses
- **Trust fund timeline**: Projects 2034 depletion with user-defined custom scenarios
- **Interactive help**: Detailed tooltips explaining each funding scenario and tax implication

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
- **Wizard JSON Loading**: "Pick up where you left off" functionality in wizard welcome page with file preview and parameter validation

### Wizard JSON Conversion
Automatic compatibility layer between wizard and Monte Carlo analysis:
- **Auto-detection**: `parse_parameters_upload_json()` detects wizard vs native JSON format
- **Parameter mapping**: `convert_wizard_json_to_simulation_params()` handles 30+ parameter name conversions
- **Structure flattening**: Converts nested wizard JSON to flat SimulationParams format
- **Backward compatibility**: Native Monte Carlo JSON files still work unchanged
- **Seamless handoff**: Parameters flow directly between pages without file transfers

### Privacy Protection
Personal configuration files ignored in git:
- `default.json` (personal configuration, auto-loaded on startup)
- `*_personal_*.json`, `*_confidential_*.json` patterns
- Simulation output files

### Default Scenario
Hypothetical California family:
- $250K annual income, $2.5M portfolio at retirement
- 65/25/8/2 allocation (Equity/Bonds/RE/Cash)
- **California state taxes**: Combined fed+state rates (13%/31%/36%)
- **Social Security**: $40K primary + optional spousal benefits
- **Moderate funding scenario**: Gradual SS cuts with partial reform
- College expenses, home renovation, healthcare costs
- Part-time consulting and board position income

## Common Commands

### Running the Application
```bash
# Recommended: Use the launcher script
./run.sh

# Or run directly:
streamlit run main.py
# Open browser to http://localhost:8501
```

### Page Navigation
- **Main App**: http://localhost:8501
- **Setup Wizard**: http://localhost:8501/Wizard
- **Monte Carlo Analysis**: http://localhost:8501/Monte_Carlo_Analysis

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

### AI Analysis & Chat Interface Improvements (Latest - September 2025)
**Major improvements to AI analysis experience and parameter loading reliability:**

**Fixed Duplicate AI Analysis UI:**
- **Problem**: Duplicate "Run AI Analysis" buttons appearing during analysis execution due to Streamlit rerun timing issues
- **Root Cause**: `st.rerun()` after analysis completion caused both "ready" and "analyzing" states to render simultaneously
- **Solution**: Removed forced rerun, implemented proper state-based conditional rendering using `analyze_button` state
- **Pattern**: Only show "Ready to analyze" message when NOT running analysis: `if not (analyze_button or st.session_state.get('force_ai_analysis', False))`
- **Result**: Clean UI with single AI analysis section that properly transitions between states

**Enhanced Chat Interface:**
- **Chat Input Positioning**: Restructured chat logic to process input first, then display history - moving toward proper chat app UX
- **Improved Error Handling**: All chat errors now properly added to conversation history instead of showing duplicate error messages
- **Session Management**: Added `st.rerun()` after chat processing to ensure new messages appear immediately
- **Message Flow**: Eliminated immediate message displays during processing, relying on centralized history display

**Income Stream Parameter Loading Fix:**
- **Problem**: Loading JSON with empty `income_streams` arrays didn't clear existing income streams in UI
- **Root Cause**: Parameter transfer was setting `st.session_state.income_streams = []` but UI uses `st.session_state.other_income_streams`
- **Solution**: Fixed session state variable mapping in `pages/monte_carlo.py` lines 1831 and 1839
- **Pattern**: Matches expense streams fix pattern using correct UI session state variables

**Technical Implementation:**
- **Streamlit State Management**: Better understanding and handling of Streamlit's execution model and rerun behavior
- **Conditional UI Rendering**: Proper use of button state to control what UI elements are displayed
- **Session State Synchronization**: Ensured UI widgets use correct session state variables for parameter loading
- **Error Message Handling**: Consistent error handling patterns across AI analysis and chat interfaces

### Unified Parameter Loading Architecture (September 2025)
**Major architectural improvements for parameter management:**

**Unified JSON Loading System:**
- **Problem**: Duplicate code paths for wizard transitions vs JSON loading led to sync issues and filing status bugs
- **Solution**: Both wizard and JSON loading now use identical approach - load params into `wizard_params`, set `wizard_completed=True`
- **Benefits**: Single code path, no duplicate functions, consistent behavior between all parameter loading methods
- **Pattern**: Load → Set session flags → Trigger unified parameter application on next page load

**P10/P90 Path Storage Implementation:**
- **Problem**: Year-by-year table showed identical values (~$24-25M) for P10/P50/P90 regardless of selection
- **Root Cause**: Previous implementation reconstructed percentile paths by scaling median path, not using actual simulation data
- **Solution**: Modified simulation engine to store actual P10/P50/P90 path details during Monte Carlo run
- **Architecture**: Added `p10_path_details` and `p90_path_details` to `SimulationResults`, identify specific simulations corresponding to percentiles
- **Testing**: Added 10 comprehensive unit tests validating percentile path accuracy and internal consistency

**Duplicate Button Fixes:**
- **Problem**: "Run AI Analysis" and "Run Simulation" buttons were appearing twice
- **Solution**: Moved AI analysis entirely to sidebar, removed duplicate section from main tabs
- **Result**: Clean UI with single button for each action

**Critical Regression Fixes:**
- **Filing Status Bug**: JSON loading caused crash with `'married_filing_jointly' not in list ['MFJ', 'Single']`
  - **Solution**: Added filing status format conversion mapping in parameter application
  - **Mapping**: `married_filing_jointly` → `MFJ`, `single` → `Single`

- **Social Security Parameter Mismatches**: Wizard transition failed with `'SimulationParams' object has no attribute 'ss_scenario'`
  - **Root Cause**: Parameter name inconsistencies between UI and simulation engine
  - **Solution**: Fixed parameter mapping to use correct SimulationParams attribute names:
    - `ss_scenario` → `ss_benefit_scenario`
    - `ss_custom_start_year` → `ss_reduction_start_year`
    - `ss_spouse_benefit` → `spouse_ss_annual_benefit` (with `spouse_ss_enabled` flag)

- **JSON Loading Function Usage**: Initial attempts to bypass `unified_json_loader_ui()` broke the UI
  - **Problem**: Function was returning `None` on page reruns, causing button duplication and failures
  - **Root Cause**: Misunderstanding of the function's design - it's meant to handle the complete UI flow
  - **Solution**: Used `unified_json_loader_ui()` as designed - it handles preview, confirmation, and returns parameters only after user confirmation
  - **Result**: Clean, single-button experience matching wizard behavior exactly

### Multipage Architecture Implementation (September 2025)
Complete transformation to unified Streamlit multipage application:

**Architecture Changes:**
- **Unified Entry Point**: `main.py` serves as multipage application controller
- **Page Structure**: `pages/wizard.py` (setup) and `pages/monte_carlo.py` (analysis)
- **Seamless Navigation**: Direct parameter sharing via `st.session_state` - no JSON files required
- **Enhanced Launcher**: Updated `run.sh` for single-app deployment

**JSON Compatibility Layer:**
- **Auto-Detection**: `parse_parameters_upload_json()` detects wizard vs native JSON formats
- **Parameter Mapping**: `convert_wizard_json_to_simulation_params()` handles 30+ parameter name conversions
- **Structure Flattening**: Converts nested wizard JSON to flat SimulationParams format
- **Backward Compatibility**: Existing Monte Carlo JSON files continue to work unchanged

**User Experience Improvements:**
- **Single Port**: Everything runs on http://localhost:8501 (no more port juggling)
- **Direct Access**: Bookmark wizard (*/Wizard) or analysis (*/Monte_Carlo_Analysis) pages
- **Smart Workflow**: Wizard completion button navigates directly to analysis
- **Shared State**: Parameters flow automatically between pages without file transfers

**Technical Implementation:**
- **Session State Management**: Centralized parameter storage in `st.session_state`
- **Page Navigation**: Streamlit's native `st.switch_page()` for seamless transitions
- **Parameter Validation**: Comprehensive validation and error handling
- **Legacy Support**: JSON download/upload still available for backup and sharing

### Enhanced Visualization Suite
- **High-resolution charts**: Terminal wealth distribution with 100-200 bins and kernel density overlay
- **New chart types**: 5 additional visualizations including Monte Carlo path samples, success probability over time, cash flow waterfall, sequence of returns analysis, and drawdown analysis
- **Improved rendering**: Fixed overlapping elements with clean subtitle formatting
- **Statistical depth**: Comprehensive percentile analysis and failure threshold visualization
- **Interactive elements**: Hover details and dynamic chart controls
- **Percentile path analysis**: P10/P50/P90 path selection for year-by-year tables with pessimistic, median, and optimistic scenarios

### AI Analysis Features
- **Google Gemini Integration**: Advanced AI-powered retirement analysis with multiple model options
- **Manual Trigger Controls**: Separated AI analysis from simulation with dedicated "Run AI Analysis" button
- **Usage Tracking**: Real-time monitoring of token consumption and API request counts
- **Privacy Protection**: Comprehensive warnings about free tier data usage for AI training
- **Query Monitoring**: Session-based tracking with daily usage limits and warnings
- **Model Selection**: Support for Gemini 2.5 Pro, Flash models, and other variants
- **Error Handling**: Graceful fallbacks with informative error messages
- **Chat Interface**: Interactive Q&A with context-aware responses about simulation results

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

## Recent Major Updates

### State Tax Integration & Social Security Modeling (Latest)
- **State Tax Dropdown**: 10 common states with automatic combined federal+state tax bracket updates
- **Comprehensive Social Security**: Primary and spousal benefits with 4 funding scenarios
- **2024-2025 Projections**: Based on latest Social Security Trustees Report projections
- **Trust Fund Modeling**: 2034 depletion timeline with 19% benefit cuts (conservative scenario)
- **Enhanced Test Coverage**: 24 new tests covering state taxes, Social Security calculations, integration testing
- **Improved Portfolio Sustainability**: Social Security income reduces withdrawal pressure, improving success rates
- **Age Flexibility**: Configurable start ages (62-70) for both primary and spousal benefits
- **Custom Scenarios**: User-defined benefit reduction percentages and timing
- **Tax Integration**: Social Security income properly reduces portfolio withdrawal needs in tax calculations

**Implementation Details**:
- Age calculation: Assumes retirement at 65, so `age = 65 + (year - start_year)`
- Spousal benefits use same funding scenario as primary beneficiary
- All parameters properly serialized/deserialized in JSON format
- State tax rates are rough estimates combining federal and state effective rates
- Social Security scenarios:
  - Conservative: 19% cut starting 2034 (current law)
  - Moderate: Gradual cuts (5% + 1% per year) capping at 10%
  - Optimistic: Full benefits maintained through reforms
  - Custom: User-defined reduction percentage and start year

**Test Suite Enhancements**:
- New `tests/test_app_functions.py`: 13 tests for state tax rates and Social Security calculations
- Enhanced `tests/test_simulation.py`: 7 new tests for parameter integration and simulation logic
- Updated `tests/test_io.py`: 2 new tests for Social Security parameter serialization
- Enhanced `tests/test_deterministic.py`: 2 new tests for deterministic projector integration
- Fixed regression: Updated depletion test to account for Social Security benefits improving sustainability
- **All 83+ tests passing**: Comprehensive validation with no regressions

### AI Analysis & User Experience Enhancements (September 2025)
Major improvements to AI integration, user experience, and data management:

**AI Analysis Improvements:**
- **Manual Trigger Control**: Separated AI analysis from automatic simulation run with dedicated "🧠 Run AI Analysis" button
- **Usage Tracking**: Real-time monitoring of token consumption, request counts, and daily usage with warnings at 50% and 80% of limits
- **Enhanced Privacy Warnings**: Comprehensive notices about Gemini free tier data usage for AI training in both wizard and Monte Carlo interfaces
- **Model Selection**: Support for Gemini 2.5 Pro, Flash models, and other variants with performance descriptions
- **Error Handling**: Improved error messages with specific guidance for rate limits, quota exceeded, and API key issues

**User Experience Enhancements:**
- **JSON Parameter Loading**: "Pick up where you left off" functionality in wizard welcome page with file upload, parameter preview, and automatic type conversion
- **Percentile Path Analysis**: P10/P50/P90 path selection dropdown for year-by-year tables showing pessimistic, median, and optimistic scenarios
- **Numeric Type Safety**: Fixed Streamlit mixed numeric types errors for all number inputs when loading JSON parameters
- **Enhanced Navigation**: Seamless parameter transfer between wizard and Monte Carlo analysis with improved session state management

**Technical Implementation:**
- **Usage Metadata Extraction**: Captures prompt tokens, completion tokens, and total tokens from Gemini API responses
- **Session-Based Tracking**: Maintains usage history with automatic cleanup (last 50 entries) and daily totals calculation
- **Privacy Controls**: Explicit warnings and user consent for AI data usage with clear privacy implications
- **Parameter Conversion**: Robust handling of both wizard JSON and flat Monte Carlo parameter formats with type safety
- **Percentile Calculations**: Wealth path scaling algorithm to approximate P10/P90 scenarios from existing Monte Carlo results

**Files Modified:**
- `pages/wizard.py`: Added JSON loading, numeric type fixes, privacy warnings
- `pages/monte_carlo.py`: Manual AI triggers, usage display, P10/P90 dropdowns
- `ai_analysis.py`: Usage tracking, metadata extraction, enhanced error handling
- `CLAUDE.md`: Comprehensive documentation updates

All features maintain backward compatibility while significantly improving user experience and privacy controls for AI-powered retirement analysis.