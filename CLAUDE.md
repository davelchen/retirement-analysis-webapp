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
Comprehensive test suite with 240+ unit tests covering:
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
- Income and expense stream timing, overlaps, and edge cases
- Multiple spending methods (CAPE-based, fixed annual)

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

### Enhanced Social Security Modeling
Comprehensive Social Security integration with proper retirement vs SS age handling and full year-by-year visibility:

**Major Architecture Improvements (September 2025)**:
- **Retirement Age Independence**: Fixed hardcoded age=65 assumption - now uses actual `retirement_age` parameter
- **Year-by-Year Tracking**: SS income appears in detailed tables, CSV exports, and summary statistics
- **Cash Flow Integration**: SS income included in waterfall charts and simulation results display
- **Enhanced UI Guidance**: Clear tooltips distinguishing retirement age from SS start age with strategy examples

**Funding Scenarios**:
- **Conservative (19% cut)**: Full benefit reduction starting 2034 per current law
- **Moderate (gradual reform)**: Partial cuts with Congressional intervention
- **Optimistic (full reform)**: Benefits maintained through tax increases
- **Custom**: User-defined reduction percentage and timing

**Technical Implementation**:
- **Age flexibility**: Start benefits ages 62-70 with proper actuarial adjustments
- **Spousal benefits**: Separate tracking for spouse's Social Security income
- **Trust fund modeling**: Projects 2034 depletion timeline with scenario-based cuts
- **Tax integration**: SS income reduces portfolio withdrawal requirements
- **Real-dollar calculations**: Benefits subject to same funding scenarios
- **Early retirement support**: Validated for retire-at-45, SS-at-62 scenarios with 17+ year delays

```python
def calculate_social_security_benefit(year, start_year, retirement_age, annual_benefit, scenario,
                                    custom_reduction, reduction_start_year, start_age):
    # Calculate age based on actual retirement age, not hardcoded 65
    age_at_year = retirement_age + (year - start_year)
    # Age-based eligibility with funding scenario adjustments
```

### Monte Carlo Engine
Vectorized operations for performance:
- Small sims (≤1K): <1 second
- Medium sims (≤10K): 2-5 seconds (recommended)
- Large sims (≤50K): 10-30 seconds

### Spending Methods
Three distinct spending approaches with appropriate guardrail integration:
- **CAPE-based**: Uses market valuation to set initial withdrawal rate (3.2% + 0.5/CAPE) with Guyton-Klinger guardrails
- **Fixed annual**: Constant spending amount every year, no guardrail adjustments
- **Manual initial**: User-defined starting withdrawal rate with Guyton-Klinger guardrails (legacy option)

### Guyton-Klinger Guardrails
Dynamic spending adjustments based on withdrawal rate bands (when enabled):
- Upper guardrail: Increase spending when WR drops below threshold
- Lower guardrail: Decrease spending when WR exceeds threshold
- Configurable adjustment percentages and spending bounds
- Only applies to CAPE-based and manual initial spending methods

## UI Features

### Intelligent Parameter Validation
**Age-Aware Planning Guidance:**
- Retirement age is used for smart horizon validation (not in simulation calculations)
- Young retirees (< 50 years) get warnings for short horizons (< 40 years) with specific recommendations
- All users get longevity risk alerts if planning horizon doesn't reach age 80
- Late retirees (65+) can plan any horizon length without restrictive warnings
- Positive confirmation for excellent planning (horizons reaching age 90+)
- Real-time feedback as users adjust retirement age and horizon parameters

### Rich Tooltips & Smart Validation
Every parameter includes detailed explanations with usage guidance and examples.

**Age-Aware Horizon Validation:**
- **Young Retirement Warning**: Users retiring before age 50 with horizons under 40 years receive recommendations to extend planning
- **Longevity Risk Alerts**: Plans ending before age 80 trigger longevity risk information regardless of retirement age
- **Positive Reinforcement**: Plans extending to age 90+ receive confirmation of excellent longevity planning
- **Flexible for Late Retirees**: Users retiring at 65+ can choose any horizon without complaints about "too long"
- **Smart Logic**: retirement_age + horizon_years = end_age analysis provides contextual, helpful guidance

### Dynamic Management
- **Multi-year expense streams**: Annual amount, start year, and duration with comprehensive testing for timing accuracy
- **Income streams**: Multiple sources with start year, duration, and amounts supporting overlapping periods
- **Robust stream handling**: Proper timing calculations with edge case protection and full simulation integration
- **Aggregation logic**: UI data structures converted to simulation parameters with comprehensive test coverage
- **Spending method selection**: CAPE-based (with guardrails) vs fixed annual (no guardrails) with conditional UI display

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
- **Main Landing Page**: http://localhost:8501 (choose your starting point)
- **Setup Wizard**: Navigate via sidebar or click "Wizard" page
- **Monte Carlo Analysis**: Navigate via sidebar or click "Monte_Carlo_Analysis" page

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

## Technical Lessons Learned

### Streamlit Execution Model & State Management
- **Rerun Timing Issues**: `st.rerun()` after operations can cause duplicate UI rendering where both "ready" and "processing" states show simultaneously
- **Solution**: Use conditional rendering based on button state instead of forced reruns: `if not (analyze_button or st.session_state.get('force_analysis', False))`
- **Session State Variables**: UI widgets must use exact session state variable names - `st.session_state.other_income_streams` vs `st.session_state.income_streams` mismatch causes parameter loading failures
- **Multipage Architecture**: Direct session state sharing between pages is more reliable than JSON file handoffs for parameter transfer

### Streamlit Widget Persistence Patterns (CRITICAL)
**Hard-learned lessons from debugging widget "jumping" and double-click issues:**

**The CORRECT Widget Persistence Pattern:**
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

**Why This Pattern Works:**
- **`wizard_params` survives navigation** - doesn't get cleared between wizard steps
- **Widget key may get cleared** - Streamlit clears unused widget keys between reruns
- **Value parameter restores widget** - when key is cleared, value parameter restores from persistent storage
- **Immediate sync keeps both aligned** - prevents circular references and conflicts
- **Change check prevents unnecessary writes** - performance optimization

**PROBLEMATIC Patterns That Cause Issues:**
```python
# ❌ WRONG: Widget key only (gets cleared between steps)
widget = st.slider("Label", key="widget_key")

# ❌ WRONG: Value parameter only (no persistence when user changes widget)
widget = st.slider("Label", value=some_default)

# ❌ WRONG: Conflicting value + key (Streamlit resets key to match value)
widget = st.slider("Label", value=43, key="widget_key")  # If widget_key=48, resets to 43!

# ❌ WRONG: Delayed sync only (widget shows stale values during navigation)
sync_widget_values_to_wizard_params()  # Called at end of script only
```

**Key Streamlit Behaviors Discovered:**
1. **Widget Keys vs Value Parameter Conflict**: When a widget has both `value` and `key` parameters and they have different values, Streamlit resets the widget key to match the value parameter
2. **Widget Key Lifecycle**: Widget keys are cleared when widgets don't render (e.g., during step navigation)
3. **One-Time Operations**: Use session state flags for operations that should only run once: `if not st.session_state.get('operation_done', False)`
4. **Rerun Behavior**: Streamlit reruns the entire script on every interaction - all code runs again

**Implementation Status:**
- **✅ COMPLETE**: 6 critical widgets use full correct pattern (horizon_years, equity_reduction, start_capital, retirement_age, start_year, num_simulations)
- **⚠️ PARTIAL**: 30+ widgets have value + key but missing change sync (functional but not optimized)
- **✅ TESTED**: 9 comprehensive unit tests in `tests/test_widget_persistence.py` validate patterns and document lessons

**Stream Safety Pattern (AI Analysis Fix):**
```python
# ✅ CORRECT: Always ensure streams are lists, never None
income_streams = st.session_state.other_income_streams if st.session_state.other_income_streams else []

# ✅ CORRECT: Defensive programming in data processing
streams = getattr(params, 'income_streams', []) or []  # Handle None gracefully
```

**This section documents the most critical Streamlit learnings to prevent future widget persistence bugs.**

### Pandas DataFrame Array Length Issues
- **Root Cause**: Monte Carlo `wealth_paths` includes t=0 (initial wealth) plus all horizon years, creating N+1 data points
- **Symptom**: `ValueError: All arrays must be of the same length` when years array (N elements) doesn't match data arrays (N+1 elements)
- **Solution**: Use dynamic sizing with `results.wealth_paths.shape[1]` instead of calculated `horizon_years`
- **Prevention**: Always validate array lengths before DataFrame construction
- **Debug Pattern**: Use `print(f"DEBUG: array_name shape: {array.shape}")` to diagnose length mismatches

### Security Best Practices
- **API Key Protection**: Always verify `.gitignore` contains sensitive config files (`ui_config.json`, `default.json`, `*_personal_*.json`)
- **Git Status Check**: Use `git status --ignored filename` to confirm files are properly ignored
- **Search Patterns**: Use `grep -r "actual_secret_value"` to verify no hardcoded secrets in tracked files
- **Never commit sensitive data**: Even in test files or examples

### Testing & Documentation Maintenance
- **Test Count Tracking**: With 255+ tests, documentation gets outdated quickly - regularly update README badges and counts
- **Regression Tests**: For critical bugs like CSV exports, add both failure reproduction tests and fix validation tests
- **Module Growth**: As test suites grow, update specific module test counts in documentation
- **Widget Persistence Tests**: Added comprehensive unit tests in `tests/test_widget_persistence.py` to validate and document Streamlit widget behavior patterns

## Recent Major Updates

### Streamlit Widget Persistence & AI Analysis Fixes (Latest - September 2025)
**Critical fixes for widget behavior and AI analysis robustness:**

**Widget Persistence Pattern Implementation:**
- **Problem**: Streamlit widgets exhibiting "jumping" behavior requiring double-clicks, values resetting after navigation between wizard steps
- **Root Cause**: Conflicting widget `value` and `key` parameters, plus widget keys being cleared during step navigation
- **Solution**: Implemented complete persistence pattern with persistent storage (`wizard_params`) as source of truth, widget keys for identity, and immediate sync with change detection
- **Pattern**: `value=wizard_params.get()` + `key="widget_key"` + `if widget_value != wizard_params.get(): wizard_params[key] = widget_value`
- **Fixed Widgets**: 6 critical widgets now use complete pattern (horizon_years, equity_reduction, start_capital, retirement_age, start_year, num_simulations)

**AI Analysis NoneType Error Fix:**
- **Problem**: `"object of type 'NoneType' has no len()"` error when running AI analysis
- **Root Cause**: `income_streams` parameter being passed as `None` instead of empty list `[]` when no streams exist
- **Solution**: Updated `pages/monte_carlo.py` line 464: `income_streams=st.session_state.other_income_streams if st.session_state.other_income_streams else []`
- **Safety**: Added defensive programming in `ai_analysis.py`: `getattr(params, 'income_streams', []) or []`

**Comprehensive Testing & Documentation:**
- **New Test Suite**: Added `tests/test_widget_persistence.py` with 9 comprehensive unit tests validating widget patterns
- **Test Categories**: Parameter persistence, AI analysis robustness, widget pattern validation, Streamlit behavior documentation
- **Documentation**: Added critical Streamlit Widget Persistence Patterns section to CLAUDE.md with examples and anti-patterns
- **Test Results**: All 255 tests passing (1 complex UI test skipped), no regressions from widget fixes

**Key Streamlit Discoveries Documented:**
1. **Value/Key Conflict**: Streamlit resets widget keys when value parameter conflicts with existing key value
2. **Widget Key Lifecycle**: Keys cleared when widgets don't render (navigation), restored by value parameter
3. **One-Time Operation Pattern**: Use session state flags to prevent repeated execution on reruns
4. **Stream Safety**: Always ensure list parameters are `[]` not `None` to prevent length operation errors

### Spending Method Enhancement & Stream Robustness (September 2025)
**Major UI improvements and comprehensive testing for income/expense streams:**

**Spending Method Alignment:**
- **Problem**: Wizard offered "fixed annual spending" but Monte Carlo only had "manual initial spending", creating user confusion
- **Solution**: Implemented three distinct spending methods with proper UI alignment between wizard and Monte Carlo pages
- **Methods**: CAPE-based (with guardrails), Fixed annual (no guardrails), Manual initial (legacy, with guardrails)
- **Conditional UI**: Guardrails and spending bounds automatically hidden when fixed spending is selected
- **CAPE Display**: Added real-time CAPE calculation display showing withdrawal rate and dollar amounts in both wizard and Monte Carlo

**Income Stream Bug Fix & Enhancement:**
- **Problem**: Multiple income streams incorrectly flattened into single stream (e.g., $35K/5yrs + $20K/8yrs showing as $55K from earliest to latest year)
- **Root Cause**: `_get_other_income()` method wasn't properly handling overlapping stream timing
- **Solution**: Implemented proper multiple stream support with accurate year-by-year calculations
- **Code Fix**: `simulation.py` - `for stream in self.params.income_streams:` loop with proper `year_offset` and duration checks
- **UI Integration**: Fixed `pages/monte_carlo.py` parameter mapping to use `st.session_state.other_income_streams`

**Comprehensive Stream Testing:**
- **Income Streams**: Added 4 comprehensive unit tests in `TestIncomeStreams` class covering timing, overlaps, edge cases, and full simulation
- **Expense Streams**: Added 6 comprehensive unit tests in `TestExpenseStreams` class covering multiple streams, portfolio impact, and legacy format compatibility
- **Test Coverage**: All 10 new tests pass, bringing total test count to 240+
- **Edge Cases**: Tests handle empty streams, missing keys, zero amounts, and tax implications

**Chat Interface Improvement:**
- **Problem**: Chat input appeared above conversation instead of below (ChatGPT-like behavior expected)
- **Solution**: Reordered rendering logic to display chat history first, then chat input last
- **Pattern**: Process input → Display history → Show input field for natural conversation flow
- **Result**: Proper chat app UX with input at bottom

**Technical Implementation:**
- **Stream Architecture**: Both income and expense streams use identical `start_year` + `years` duration model
- **Parameter Persistence**: All stream configurations properly serialized/deserialized in JSON format

### Social Security Age Independence & UI Improvements (September 2025)
**Major architectural fix for retirement age vs Social Security start age handling:**

**Core Issue Resolution:**
- **Problem**: Social Security calculations hardcoded `age = 65 + (year - start_year)` assumption, ignoring user's actual retirement age
- **Impact**: Early retirees saw SS starting 2 years after retirement instead of at proper age (e.g., retire at 45, SS at 67 = 22 years)
- **Root Cause**: `tax_utils.py:57` hardcoded retirement age, `SimulationParams` missing `retirement_age` field, parameter conversion gaps

**Architecture Changes:**
- **Added `retirement_age` parameter**: Updated `SimulationParams` dataclass with `retirement_age: int = 65`
- **Fixed age calculation**: `tax_utils.py` - `age_at_year = retirement_age + (year - start_year)` instead of hardcoded 65
- **Parameter flow**: Added `retirement_age` to Monte Carlo `get_current_params()` and wizard JSON conversion
- **Deterministic fix**: Updated `deterministic.py` to pass `retirement_age` parameter to SS calculations

**User Interface Improvements:**
- **Editable retirement age**: Added to Monte Carlo sidebar as number input (30-75, default 65)
- **Enhanced tooltips**: Clear distinction between retirement age and SS start age with strategy examples
- **Text input guardrails**: Fixed Streamlit decimal issues by using `st.text_input` with validation for precise 0.028 values
- **Smart date validation**: Dynamic `min_value` calculation prevents errors when changing start year

**Market Regime Synchronization:**
- **Problem**: Wizard used `recession_early`/`recession_late`, Monte Carlo used `recession_recover`/`late_recession`
- **Solution**: Updated wizard to use identical regime names as Monte Carlo for seamless parameter transfer
- **Names**: `baseline`, `recession_recover`, `grind_lower`, `late_recession`, `inflation_shock`, `long_bear`, `tech_bubble`

**Data Visibility Enhancements:**
- **Year-by-year tables**: Added `ss_income` column to simulation details and CSV exports
- **Cash flow charts**: SS income appears in waterfall visualizations
- **Summary statistics**: Total SS income metric displayed in simulation results

**Testing & Validation:**
- **Early retirement test**: Validated retire-at-45, SS-at-62 scenario with proper 17-year delay
- **Standard retirement test**: Confirmed retire-at-65, SS-at-67 with 2-year delay
- **All tests passing**: 63/63 simulation tests, 16/16 deterministic tests, no regressions
- **UI Consistency**: Wizard and Monte Carlo interfaces now perfectly aligned for spending method selection
- **Test Strategy**: Added both unit tests for logic validation and integration tests for full simulation behavior

### CSV Export Array Length Mismatch Fix (September 2025)
**Critical bug fix for CSV export functionality that was causing application crashes:**

**Fixed CSV Export Pandas DataFrame Error:**
- **Problem**: `ValueError: All arrays must be of the same length` when exporting percentile bands CSV
- **Root Cause**: Years array (40 elements) didn't match percentiles arrays (41 elements) because `wealth_paths` includes initial wealth plus horizon years
- **Solution**: Changed from hardcoded calculation to dynamic sizing using `results.wealth_paths.shape[1]` instead of assumptions about array lengths
- **Code Fix**: `pages/monte_carlo.py:1783` - `years = np.arange(st.session_state.start_year, st.session_state.start_year + results.wealth_paths.shape[1])`

**Added Comprehensive Unit Tests:**
- **Test Coverage**: Added 2 new regression tests in `tests/test_io.py`
- **Bug Reproduction**: `test_percentile_bands_csv_array_length_mismatch` reproduces the exact error scenario
- **Fix Validation**: `test_percentile_bands_csv_correct_array_sizing` validates the corrected approach
- **Result**: Total test count increased to 230+ tests, all passing

**Technical Implementation:**
- **Dynamic Array Sizing**: Uses actual data shape instead of calculated lengths for robust CSV generation
- **Regression Prevention**: Tests ensure future changes won't break CSV export functionality
- **Error Context**: The issue occurred because wealth simulation results include t=0 (initial wealth) plus all horizon years

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
- **Current usage**: CAPE sets initial withdrawal rate via `0.032 + 0.5 * (1.0 / cape_now)` - conservative base rate for safe retirement spending
- **Static during simulation**: CAPE value doesn't evolve during the 50-year projection
- **Not regime-dependent**: Market regimes affect returns but not CAPE trajectory
- **Enhancement opportunity**: Could implement dynamic CAPE evolution based on market performance

## Recent Major Updates

### Comprehensive Parameter Management Overhaul (Latest - September 2025)
**Major architectural improvement implementing systematic parameter persistence across all wizard widgets:**

**Complete Widget Immediate Sync Implementation:**
- **Universal Coverage**: Applied immediate sync patterns to all 47+ wizard widgets across all sections
- **Previously**: Only 7 widgets had proper immediate sync (start_capital, retirement_age, start_year, horizon_years, equity_reduction, num_simulations, inheritance_amount)
- **Now**: All widgets have immediate sync patterns preventing persistence race conditions
- **Sections Upgraded**: Financial Basics, Asset Allocation, Market Expectations, Tax Planning, Social Security, Guardrails, Cash Flows, AI Setup, Advanced Options
- **Pattern**: Each widget checks for changes and immediately syncs to `wizard_params` before global sync runs

**Enhanced Parameter Saving Architecture:**
- **Wizard JSON Saving**: Added missing Social Security custom reduction parameters (`ss_custom_reduction`, `ss_reduction_start_year`)
- **Simulation JSON Saving**: Enhanced `convert_simulation_params_to_wizard_params()` to include income/expense streams
- **Comprehensive Coverage**: Both save locations (wizard and simulation) now capture ALL user-modifiable parameters
- **AI Settings Exception**: AI configuration still comes from `ui_config.json` as intended
- **Complete JSON Structure**: All 10 required sections populated (basic_params, allocation, market_assumptions, taxes, social_security, guardrails, simulation, ai_config, cash_flows, advanced_options)

**Parameter Lifecycle Reliability:**
- **Round-Trip Testing**: Comprehensive testing of wizard → JSON → simulation → wizard parameter flow
- **13 Critical Parameters Verified**: start_capital, annual_spending, inheritance_amount, ss_custom_reduction, equity_pct, bonds_pct, glide_path, ss_primary_benefit, lower_guardrail, upper_guardrail, spending_floor_real, college_enabled, ss_reduction_start_year
- **Fixed Annual Spending Recovery**: Proper handling of both fixed and CAPE-based spending methods
- **JSON Format Compatibility**: Enhanced support for both wizard nested JSON and simulation flat JSON formats

**Widget Persistence Race Condition Elimination:**
- **Root Cause Fixed**: Global sync function no longer overwrites widgets with immediate sync patterns
- **Skip List Maintenance**: Comprehensive list of 47+ widgets excluded from global sync to prevent conflicts
- **Navigation Reliability**: Values now persist correctly through wizard page navigation
- **No More Regressions**: Architecture prevents future widget persistence issues

**JSON Loading Improvements:**
- **Wizard Format Loading**: Enhanced parameter mapping with proper nested structure handling
- **Flat Format Loading**: Fixed `_convert_flat_to_wizard_params()` with correct parameter name mappings
- **Parameter Name Conversion**: Proper translation between simulation parameter names (w_equity) and wizard names (equity_pct)
- **Missing Parameter Handling**: Added inheritance_amount, ss_custom_reduction, glide_path, and other missing parameters to flat-to-wizard conversion

**Technical Implementation:**
- **Immediate Sync Pattern**: `if widget_value != st.session_state.wizard_params.get('param_key'): st.session_state.wizard_params['param_key'] = widget_value`
- **Global Sync Exclusion**: `widgets_with_immediate_sync` list prevents race conditions
- **Cash Percentage Calculation**: Automatic calculation for cash allocation from other three asset classes
- **Change Detection**: Only sync when values actually change to prevent unnecessary operations
- **Debug Logging**: Comprehensive logging for troubleshooting parameter flow issues

**Testing and Validation:**
- **Integration Tests**: All existing wizard integration tests continue to pass
- **Lifecycle Tests**: Comprehensive parameter round-trip testing with real user data
- **JSON Format Tests**: Both wizard and flat JSON formats tested with actual user files
- **Regression Prevention**: Tests ensure future changes won't break parameter persistence

**Files Modified:**
- `pages/wizard.py`: Applied immediate sync patterns to 40 additional widgets, updated skip list
- `io_utils.py`: Enhanced JSON conversion functions, fixed flat-to-wizard parameter mapping, added missing parameters
- All existing tests continue to pass, ensuring no regressions

**Result**: Eliminated all parameter persistence issues - no more values resetting after navigation, no more missing parameters in JSON files, no more widget state race conditions. The system now provides reliable, comprehensive parameter management that "just works" for all user inputs.

**Age-Aware Horizon Validation (Latest Enhancement):**
- **Intelligent Retirement Planning Guidance**: Retirement age now provides smart validation for planning horizon
- **Young Retiree Warnings**: Users under 50 with short horizons (< 40 years) receive targeted recommendations
- **Longevity Risk Alerts**: All users warned if planning doesn't extend to age 80, regardless of retirement age
- **Flexible for Late Retirees**: Users retiring at 65+ can choose any horizon without restrictive warnings
- **Positive Reinforcement**: Excellent planning (reaching age 90+) receives confirmation messages
- **Real-Time Feedback**: Validation updates immediately as users adjust age and horizon parameters

### State Tax Integration & Social Security Modeling (September 2025)
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
- New `tests/test_app_functions.py`: 15 tests for state tax rates and Social Security calculations
- Enhanced `tests/test_simulation.py`: 50+ tests for parameter integration and simulation logic
- Updated `tests/test_io.py`: 25 tests for Social Security parameter serialization and CSV exports
- Enhanced `tests/test_deterministic.py`: 16 tests for deterministic projector integration
- Added comprehensive test modules for wizard integration, type safety, and parameter validation
- Fixed regression: Updated depletion test to account for Social Security benefits improving sustainability
- **All 230+ tests passing**: Comprehensive validation with no regressions

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