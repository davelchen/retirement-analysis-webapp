"""
Streamlit web application for Monte Carlo retirement simulation.
Features state tax integration, Social Security modeling, and comprehensive
retirement planning with tax-aware withdrawals and Guyton-Klinger guardrails.

"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, Optional, Tuple
import json
import io

# Import our modules
from simulation import SimulationParams, RetirementSimulator, calculate_percentiles, calculate_summary_stats
from deterministic import DeterministicProjector, convert_to_nominal, create_nominal_table
from tax import calculate_tax, effective_tax_rate, marginal_tax_rate
from io_utils import convert_wizard_to_json, convert_wizard_json_to_simulation_params, create_parameters_download_json
from charts import (
    create_terminal_wealth_distribution, create_wealth_percentile_bands,
    create_comparison_chart, create_spending_chart, create_withdrawal_rate_chart,
    create_tax_analysis_chart, create_monte_carlo_paths_sample,
    create_success_probability_over_time, create_cash_flow_waterfall,
    create_sequence_of_returns_analysis, create_drawdown_analysis,
    create_income_sources_stacked_area, create_asset_allocation_evolution
)
from ai_analysis import RetirementAnalyzer, create_mock_analysis, APIError
from io_utils import (
    create_parameters_download_json, parse_parameters_upload_json,
    export_terminal_wealth_csv, export_percentile_bands_csv, export_year_by_year_csv,
    validate_parameters_json, format_currency, create_summary_report
)


def get_state_tax_rates(state, filing_status):
    """Get combined federal + state tax rates for common states"""
    # These are rough estimates combining federal and state effective rates
    state_rates = {
        'Federal Only': {
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'CA': {  # High state tax
            'MFJ': [(0, 0.13), (94_300, 0.31), (201_000, 0.36)],
            'Single': [(0, 0.13), (47_150, 0.31), (100_500, 0.36)]
        },
        'NY': {  # High state tax
            'MFJ': [(0, 0.14), (94_300, 0.30), (201_000, 0.35)],
            'Single': [(0, 0.14), (47_150, 0.30), (100_500, 0.35)]
        },
        'TX': {  # No state income tax
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'FL': {  # No state income tax
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'WA': {  # No state income tax
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'NV': {  # No state income tax
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'PA': {  # Flat state tax
            'MFJ': [(0, 0.13), (94_300, 0.25), (201_000, 0.27)],
            'Single': [(0, 0.13), (47_150, 0.25), (100_500, 0.27)]
        },
        'OH': {  # Moderate state tax
            'MFJ': [(0, 0.11), (94_300, 0.24), (201_000, 0.27)],
            'Single': [(0, 0.11), (47_150, 0.24), (100_500, 0.27)]
        },
        'IL': {  # Flat state tax
            'MFJ': [(0, 0.15), (94_300, 0.27), (201_000, 0.29)],
            'Single': [(0, 0.15), (47_150, 0.27), (100_500, 0.29)]
        }
    }
    return state_rates.get(state, state_rates['Federal Only'])[filing_status]


def calculate_social_security_benefit(year, start_year, annual_benefit, scenario, custom_reduction, reduction_start_year, start_age):
    """Calculate Social Security benefit for a given year with projected funding scenarios"""
    # Assume they start retirement at 65, so age = 65 + (year - start_year)
    age_at_year = 65 + (year - start_year)

    # Not eligible yet
    if age_at_year < start_age:
        return 0

    base_benefit = annual_benefit

    # Apply scenario-based reductions
    if year >= reduction_start_year:
        if scenario == 'conservative':
            # Full 19% cut starting 2034, no reform
            reduction = 0.19
        elif scenario == 'moderate':
            # Gradual reduction to 10% cut, partial reforms
            years_since_cut = year - reduction_start_year
            reduction = min(0.10, 0.05 + (years_since_cut * 0.01))  # Gradual to 10%
        elif scenario == 'optimistic':
            # Full benefits maintained through reforms
            reduction = 0.0
        else:  # custom
            reduction = custom_reduction

        base_benefit *= (1 - reduction)

    return base_benefit


def load_ui_config():
    """Load UI configuration like API keys from ui_config.json"""
    try:
        import os
        if os.path.exists('ui_config.json'):
            with open('ui_config.json', 'r') as f:
                config = json.load(f)
            return config
    except Exception as e:
        print(f"Warning: Could not load ui_config.json: {e}")

    return {}


def save_ui_config(config):
    """Save UI configuration to ui_config.json"""
    try:
        with open('ui_config.json', 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save ui_config.json: {e}")


def initialize_session_state():
    """Initialize session state variables with defaults for hypothetical CA family ($250K income)"""

    # Load UI config first
    ui_config = load_ui_config()

    # Try to load default.json if it exists
    try:
        import os
        if os.path.exists('default.json'):
            with open('default.json', 'r') as f:
                json_str = f.read()
            
            from io_utils import validate_parameters_json, parse_parameters_upload_json
            is_valid, error = validate_parameters_json(json_str)
            
            if is_valid:
                params = parse_parameters_upload_json(json_str)
                
                # Load parameters from default.json
                loaded_defaults = {
                    # Core setup
                    'start_year': params.start_year,
                    'horizon_years': params.horizon_years,
                    'num_sims': params.num_sims,
                    'random_seed': params.random_seed,
                    
                    # Start capital
                    'capital_preset': 'Custom',
                    'custom_capital': params.start_capital,
                    'use_custom_capital': True,
                    
                    # Allocation weights
                    'w_equity': params.w_equity,
                    'w_bonds': params.w_bonds,
                    'w_real_estate': params.w_real_estate,
                    'w_cash': params.w_cash,
                    
                    # Return model
                    'equity_mean': params.equity_mean,
                    'equity_vol': params.equity_vol,
                    'bonds_mean': params.bonds_mean,
                    'bonds_vol': params.bonds_vol,
                    'real_estate_mean': params.real_estate_mean,
                    'real_estate_vol': params.real_estate_vol,
                    'cash_mean': params.cash_mean,
                    'cash_vol': params.cash_vol,
                    
                    # CAPE and spending
                    'cape_now': params.cape_now,
                    'lower_wr': params.lower_wr,
                    'upper_wr': params.upper_wr,
                    'adjustment_pct': params.adjustment_pct,
                    'spending_floor_real': params.spending_floor_real,
                    'spending_ceiling_real': params.spending_ceiling_real,
                    'floor_end_year': params.floor_end_year,
                    
                    # College expenses
                    'college_enabled': params.college_enabled,
                    'college_base_amount': params.college_base_amount,
                    'college_start_year': params.college_start_year,
                    'college_end_year': params.college_end_year,
                    'college_growth_real': params.college_growth_real,
                    
                    # Multi-year expenses
                    'onetime_expenses': params.expense_streams or [],
                    
                    # Real estate cash flow
                    're_flow_enabled': params.re_flow_enabled,
                    're_flow_preset': params.re_flow_preset,
                    're_flow_start_year': params.re_flow_start_year,
                    're_flow_year1_amount': params.re_flow_year1_amount,
                    're_flow_year2_amount': params.re_flow_year2_amount,
                    're_flow_steady_amount': params.re_flow_steady_amount,
                    're_flow_delay_years': params.re_flow_delay_years,
                    
                    # Inheritance
                    'inherit_amount': params.inherit_amount,
                    'inherit_year': params.inherit_year,
                    
                    # Other income streams
                    'other_income_streams': [
                        {
                            'amount': params.other_income_amount,
                            'start_year': params.other_income_start_year,
                            'years': params.other_income_years,
                            'description': 'Loaded from default.json'
                        }
                    ] if params.other_income_amount > 0 and params.other_income_years > 0 else [],
                    
                    # Currency view
                    'currency_view': 'Real',
                    'inflation_rate': 0.028,
                    
                    # Tax parameters
                    'filing_status': params.filing_status,
                    'standard_deduction': params.standard_deduction,
                    'bracket_1_threshold': params.tax_brackets[0][0] if params.tax_brackets and len(params.tax_brackets) >= 1 else 0,
                    'bracket_1_rate': params.tax_brackets[0][1] if params.tax_brackets and len(params.tax_brackets) >= 1 else 0.10,
                    'bracket_2_threshold': params.tax_brackets[1][0] if params.tax_brackets and len(params.tax_brackets) >= 2 else 94_300,
                    'bracket_2_rate': params.tax_brackets[1][1] if params.tax_brackets and len(params.tax_brackets) >= 2 else 0.22,
                    'bracket_3_threshold': params.tax_brackets[2][0] if params.tax_brackets and len(params.tax_brackets) >= 3 else 201_000,
                    'bracket_3_rate': params.tax_brackets[2][1] if params.tax_brackets and len(params.tax_brackets) >= 3 else 0.24,
                    
                    # Regime
                    'regime': params.regime,
                    'custom_equity_shock_year': params.custom_equity_shock_year,
                    'custom_equity_shock_return': params.custom_equity_shock_return,
                    'custom_shock_duration': params.custom_shock_duration,
                    'custom_recovery_years': params.custom_recovery_years,
                    'custom_recovery_equity_return': params.custom_recovery_equity_return,
                    
                    # Results caching
                    'simulation_results': None,
                    'deterministic_results': None,
                    'last_params_hash': None,
                }
            else:
                # If validation fails, use hardcoded defaults
                raise ValueError(f"Invalid default.json: {error}")
    except Exception as e:
        # If any error occurs (file doesn't exist, invalid JSON, etc.), use hardcoded defaults
        loaded_defaults = {}
    
    # Fallback defaults (used if default.json doesn't exist or fails to load)
    defaults = {
        # Core setup
        'start_year': 2026,
        'horizon_years': 40,  # Retire at 65, plan to 95
        'num_sims': 10_000,
        'random_seed': None,
        
        # Start capital (accumulated over ~20-25 year career)
        'capital_preset': '2,500,000',  # ~10x annual income saved
        'custom_capital': 2_500_000,
        'use_custom_capital': False,
        
        # Allocation weights (age-appropriate for 55-year-old)
        'w_equity': 0.65,
        'w_bonds': 0.25,
        'w_real_estate': 0.08,
        'w_cash': 0.02,

        # Glide path (age-based allocation adjustment)
        'glide_path_enabled': False,
        'equity_reduction_per_year': 0.005,
        
        # Return model (conservative assumptions)
        'equity_mean': 0.048,
        'equity_vol': 0.18,
        'bonds_mean': 0.015,
        'bonds_vol': 0.07,
        'real_estate_mean': 0.01,
        'real_estate_vol': 0.10,
        'cash_mean': 0.0,
        'cash_vol': 0.0001,
        
        # CAPE and spending (California high cost of living)
        'cape_now': 32.0,  # Market-dependent
        'lower_wr': 0.032,
        'upper_wr': 0.050,
        'adjustment_pct': 0.10,
        'spending_floor_real': 120_000,  # CA minimum lifestyle
        'spending_ceiling_real': 200_000,  # Comfortable CA lifestyle
        'floor_end_year': 2046,  # First 20 years of retirement
        
        # College expenses (2 children)
        'college_enabled': True,
        'college_base_amount': 100_000,
        'college_start_year': 2032,
        'college_end_year': 2041,
        'college_growth_real': 0.015,  # Slightly above inflation
        
        # One-time expenses (realistic family expenses)
        'onetime_expenses': [
            {'year': 2030, 'amount': 75_000, 'description': 'Home renovation'},
            {'year': 2035, 'amount': 50_000, 'description': 'Vehicle replacement'},
            {'year': 2045, 'amount': 60_000, 'description': 'Healthcare/mobility upgrades'}
        ],
        
        # Real estate cash flow (no rental income initially)
        're_flow_enabled': True,
        're_flow_preset': 'delayed',
        're_flow_start_year': 2026,
        're_flow_year1_amount': 50_000,
        're_flow_year2_amount': 60_000,
        're_flow_steady_amount': 75_000,
        're_flow_delay_years': 0,
        
        # Inheritance (modest parental inheritance)
        'inherit_amount': 400_000,
        'inherit_year': 2038,
        
        # Other income streams (part-time work, consulting)
        'other_income_streams': [
            {'amount': 35_000, 'start_year': 2026, 'years': 5, 'description': 'Part-time consulting'},
            {'amount': 20_000, 'start_year': 2028, 'years': 8, 'description': 'Board positions'}
        ],
        
        # Currency view
        'currency_view': 'Real',
        'inflation_rate': 0.028,  # Slightly higher for California
        
        # Tax parameters (California MFJ)
        'filing_status': 'MFJ',
        'standard_deduction': 29_200,  # Federal standard deduction
        'state_tax': 'CA',  # Default to California
        'bracket_1_threshold': 0,
        'bracket_1_rate': 0.13,  # Combined Fed+CA effective rate
        'bracket_2_threshold': 94_300,
        'bracket_2_rate': 0.31,  # Combined Fed+CA effective rate
        'bracket_3_threshold': 201_000,
        'bracket_3_rate': 0.36,  # Combined Fed+CA effective rate

        # Social Security parameters
        'social_security_enabled': True,
        'ss_benefit_scenario': 'moderate',  # conservative, moderate, optimistic, custom
        'ss_annual_benefit': 40_000,  # Estimated annual benefit
        'ss_start_age': 67,  # Full retirement age
        'ss_custom_reduction': 0.10,  # For custom scenario
        'ss_reduction_start_year': 2034,  # When benefit cuts begin

        # Spousal Social Security
        'spouse_ss_enabled': False,
        'spouse_ss_annual_benefit': 30_000,
        'spouse_ss_start_age': 67,
        
        # Regime (baseline for demo)
        'regime': 'baseline',
        'custom_equity_shock_year': 0,
        'custom_equity_shock_return': -0.20,
        'custom_shock_duration': 1,
        'custom_recovery_years': 2,
        'custom_recovery_equity_return': 0.02,
        
        # Results caching
        'simulation_results': None,
        'deterministic_results': None,
        'last_params_hash': None,
    }
    
    # Use loaded_defaults if available, otherwise use fallback defaults
    final_defaults = loaded_defaults if 'loaded_defaults' in locals() and loaded_defaults else defaults

    for key, value in final_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize UI config items
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = ui_config.get('gemini_api_key', '')
    if 'enable_ai_analysis' not in st.session_state:
        st.session_state.enable_ai_analysis = ui_config.get('enable_ai_analysis', False)
    if 'gemini_model' not in st.session_state:
        st.session_state.gemini_model = ui_config.get('gemini_model', 'gemini-2.0-flash')


def get_current_params() -> SimulationParams:
    """Get current simulation parameters from session state"""
    # Determine start capital
    if st.session_state.use_custom_capital:
        start_capital = st.session_state.custom_capital
    else:
        start_capital = float(st.session_state.capital_preset.replace(',', ''))
    
    # Build tax brackets
    tax_brackets = [
        (st.session_state.bracket_1_threshold, st.session_state.bracket_1_rate),
        (st.session_state.bracket_2_threshold, st.session_state.bracket_2_rate),
        (st.session_state.bracket_3_threshold, st.session_state.bracket_3_rate)
    ]
    
    # Determine spending method parameters
    initial_base_spending = None
    fixed_annual_spending = None

    spending_method = getattr(st.session_state, 'spending_method', 'cape')
    if spending_method == 'fixed':
        fixed_annual_spending = getattr(st.session_state, 'fixed_annual_spending', None)
    # For 'cape' method, both remain None (use CAPE calculation)

    return SimulationParams(
        start_year=st.session_state.start_year,
        horizon_years=st.session_state.horizon_years,
        num_sims=st.session_state.num_sims,
        random_seed=st.session_state.random_seed,
        start_capital=start_capital,
        w_equity=st.session_state.w_equity,
        w_bonds=st.session_state.w_bonds,
        w_real_estate=st.session_state.w_real_estate,
        w_cash=st.session_state.w_cash,
        glide_path_enabled=st.session_state.get('glide_path_enabled', False),
        equity_reduction_per_year=st.session_state.get('equity_reduction_per_year', 0.005),
        equity_mean=st.session_state.equity_mean,
        equity_vol=st.session_state.equity_vol,
        bonds_mean=st.session_state.bonds_mean,
        bonds_vol=st.session_state.bonds_vol,
        real_estate_mean=st.session_state.real_estate_mean,
        real_estate_vol=st.session_state.real_estate_vol,
        cash_mean=st.session_state.cash_mean,
        cash_vol=st.session_state.cash_vol,
        cape_now=st.session_state.cape_now,
        initial_base_spending=initial_base_spending,
        fixed_annual_spending=fixed_annual_spending,
        lower_wr=st.session_state.lower_wr,
        upper_wr=st.session_state.upper_wr,
        adjustment_pct=st.session_state.adjustment_pct,
        spending_floor_real=st.session_state.spending_floor_real,
        spending_ceiling_real=st.session_state.spending_ceiling_real,
        floor_end_year=st.session_state.floor_end_year,
        college_enabled=st.session_state.college_enabled,
        college_base_amount=st.session_state.college_base_amount,
        college_start_year=st.session_state.college_start_year,
        college_end_year=st.session_state.college_end_year,
        college_growth_real=st.session_state.college_growth_real,
        expense_streams=st.session_state.onetime_expenses,
        re_flow_enabled=st.session_state.re_flow_enabled,
        re_flow_preset=st.session_state.re_flow_preset,
        re_flow_start_year=st.session_state.re_flow_start_year,
        re_flow_year1_amount=st.session_state.re_flow_year1_amount,
        re_flow_year2_amount=st.session_state.re_flow_year2_amount,
        re_flow_steady_amount=st.session_state.re_flow_steady_amount,
        re_flow_delay_years=st.session_state.re_flow_delay_years,
        inherit_amount=st.session_state.inherit_amount,
        inherit_year=st.session_state.inherit_year,
        # Pass income streams directly instead of flattening
        income_streams=st.session_state.other_income_streams if st.session_state.other_income_streams else [],
        # Legacy single stream parameters (for backward compatibility)
        other_income_amount=0.0,
        other_income_start_year=2026,
        other_income_years=0,
        filing_status=st.session_state.filing_status,
        standard_deduction=st.session_state.standard_deduction,
        tax_brackets=tax_brackets,
        social_security_enabled=st.session_state.get('social_security_enabled', True),
        ss_annual_benefit=st.session_state.get('ss_annual_benefit', 40000),
        ss_start_age=st.session_state.get('ss_start_age', 67),
        ss_benefit_scenario=st.session_state.get('ss_benefit_scenario', 'moderate'),
        ss_custom_reduction=st.session_state.get('ss_custom_reduction', 0.10),
        ss_reduction_start_year=st.session_state.get('ss_reduction_start_year', 2034),
        spouse_ss_enabled=st.session_state.get('spouse_ss_enabled', False),
        spouse_ss_annual_benefit=st.session_state.get('spouse_ss_annual_benefit', 30000),
        spouse_ss_start_age=st.session_state.get('spouse_ss_start_age', 67),
        regime=st.session_state.regime,
        custom_equity_shock_year=st.session_state.custom_equity_shock_year,
        custom_equity_shock_return=st.session_state.custom_equity_shock_return,
        custom_shock_duration=st.session_state.custom_shock_duration,
        custom_recovery_years=st.session_state.custom_recovery_years,
        custom_recovery_equity_return=st.session_state.custom_recovery_equity_return
    )


def params_hash(params: SimulationParams) -> str:
    """Create hash of parameters for caching"""
    import hashlib
    params_str = str(params)
    return hashlib.md5(params_str.encode()).hexdigest()


def create_sidebar():
    """Create sidebar with all input controls"""
    st.sidebar.title("Retirement Simulation")
    
    # Core Setup
    st.sidebar.header("Core Setup")
    st.session_state.start_year = st.sidebar.number_input(
        "Start Year", 
        value=st.session_state.start_year, 
        min_value=2020, 
        max_value=2050,
        help="🗓️ **Base year for simulation start**\n\nThis is the first year of retirement. All cash flows, expenses, and projections begin from this year."
    )
    st.session_state.horizon_years = st.sidebar.number_input(
        "Horizon Years", 
        value=st.session_state.horizon_years, 
        min_value=1, 
        max_value=100,
        help="📊 **Length of retirement projection**\n\nNumber of years to simulate. Common values:\n• 30 years: Standard planning horizon\n• 50 years: Conservative for early retirement\n• 25 years: Traditional retirement at 65"
    )
    st.session_state.num_sims = st.sidebar.number_input(
        "Number of Simulations", 
        value=st.session_state.num_sims, 
        min_value=100, 
        max_value=50_000, 
        step=1000,
        help="🎲 **Monte Carlo simulation count**\n\nMore simulations = more accurate results but slower computation:\n• 1,000: Quick estimates\n• 10,000: Good accuracy (recommended)\n• 50,000: Maximum precision"
    )
    seed_input = st.sidebar.text_input(
        "Random Seed (optional)", 
        value="",
        help="🎯 **Reproducibility control**\n\nEnter any number to get identical results across runs. Leave blank for different random outcomes each time."
    )
    st.session_state.random_seed = int(seed_input) if seed_input else None
    
    # Start Capital
    st.sidebar.header("Start Capital")
    capital_options = ['2,500,000', '3,000,000', '4,000,000', 'Custom']
    selected_capital = st.sidebar.selectbox(
        "Capital Preset", 
        options=capital_options,
        index=capital_options.index(st.session_state.capital_preset) if st.session_state.capital_preset in capital_options else 3,
        help="💰 **Initial portfolio value**\n\nTotal investable assets at retirement start. Presets represent different savings levels:\n• $2.5M: 10x annual income (strong saver)\n• $3.0M: 12x annual income (excellent saver)\n• $4.0M: 16x annual income (exceptional saver)\n• Custom: Enter your specific amount"
    )
    
    if selected_capital == 'Custom':
        st.session_state.use_custom_capital = True
        st.session_state.custom_capital = st.sidebar.number_input(
            "Custom Start Capital ($)", 
            value=float(st.session_state.custom_capital), 
            min_value=0.0,
            help="💼 **Your total investable assets**\n\nInclude all retirement accounts, taxable investments, and cash designated for retirement. Exclude primary residence unless planning to downsize."
        )
    else:
        st.session_state.use_custom_capital = False
        st.session_state.capital_preset = selected_capital
    
    # Allocation Weights
    st.sidebar.header("Allocation Weights")
    st.session_state.w_equity = st.sidebar.slider(
        "Equity", 0.0, 1.0, st.session_state.w_equity, 0.01,
        help="📈 **Stock market exposure**\n\nDomestic and international stocks. Higher expected returns but more volatile. Typical range: 40-80% for retirees."
    )
    st.session_state.w_bonds = st.sidebar.slider(
        "Bonds", 0.0, 1.0, st.session_state.w_bonds, 0.01,
        help="🏛️ **Fixed income allocation**\n\nGovernment and corporate bonds. Lower returns but provides stability and income. Typical range: 20-40% for retirees."
    )
    st.session_state.w_real_estate = st.sidebar.slider(
        "Real Estate", 0.0, 1.0, st.session_state.w_real_estate, 0.01,
        help="🏘️ **Real estate investment trusts (REITs)**\n\nProperty exposure for diversification and inflation protection. Typical range: 5-20%."
    )
    st.session_state.w_cash = st.sidebar.slider(
        "Cash", 0.0, 1.0, st.session_state.w_cash, 0.01,
        help="💵 **Cash and equivalents**\n\nMoney market, CDs, short-term bonds. Emergency funds and spending buffer. Typical range: 5-15%."
    )
    
    # Validate allocation weights
    total_weight = st.session_state.w_equity + st.session_state.w_bonds + st.session_state.w_real_estate + st.session_state.w_cash
    if abs(total_weight - 1.0) > 1e-6:
        st.sidebar.error(f"⚠️ Allocation weights must sum to 1.0. Current sum: {total_weight:.3f}")
    else:
        st.sidebar.success(f"✅ Allocation sums to {total_weight:.1%}")
    
    # Return Model
    st.sidebar.header("Return Model (Real, Annual)")
    
    with st.sidebar.expander("Expected Returns", expanded=False):
        st.session_state.equity_mean = st.number_input(
            "Equity Mean", value=st.session_state.equity_mean, format="%.3f",
            help="📊 **Expected annual real return for stocks**\n\nHistorical average ~7% nominal, ~5% real after inflation. Accounts for long-term economic growth and corporate earnings.",
            key="mc_equity_mean"
        )
        st.session_state.bonds_mean = st.number_input(
            "Bonds Mean", value=st.session_state.bonds_mean, format="%.3f",
            help="🏛️ **Expected annual real return for bonds**\n\nDepends on interest rates and credit quality. Currently low due to low yields. Historical real returns ~1-3%.",
            key="mc_bonds_mean"
        )
        st.session_state.real_estate_mean = st.number_input(
            "Real Estate Mean", value=st.session_state.real_estate_mean, format="%.3f",
            help="🏘️ **Expected annual real return for REITs**\n\nCombines rental income and property appreciation. Historically ~2-4% real returns with inflation protection.",
            key="mc_real_estate_mean"
        )
        st.session_state.cash_mean = st.number_input(
            "Cash Mean", value=st.session_state.cash_mean, format="%.3f",
            help="💵 **Expected annual real return for cash**\n\nTypically near zero real return (matches inflation). Provides stability and liquidity, not growth.",
            key="mc_cash_mean"
        )
    
    with st.sidebar.expander("Volatilities", expanded=False):
        st.session_state.equity_vol = st.number_input(
            "Equity Volatility", value=st.session_state.equity_vol, format="%.3f",
            help="📈 **Annual return volatility (standard deviation)**\n\nMeasures year-to-year variability. Equity: ~15-20%. Higher volatility = wider range of possible outcomes.",
            key="mc_equity_vol"
        )
        st.session_state.bonds_vol = st.number_input(
            "Bonds Volatility", value=st.session_state.bonds_vol, format="%.3f",
            help="🏛️ **Bond return volatility**\n\nTypically 5-10%. Lower than stocks but still varies with interest rate changes and credit events.",
            key="mc_bonds_vol"
        )
        st.session_state.real_estate_vol = st.number_input(
            "Real Estate Volatility", value=st.session_state.real_estate_vol, format="%.3f",
            help="🏘️ **REIT return volatility**\n\nTypically 8-15%. Less volatile than stocks, more than bonds. Affected by interest rates and property cycles.",
            key="mc_real_estate_vol"
        )
        st.session_state.cash_vol = st.number_input(
            "Cash Volatility", value=st.session_state.cash_vol, format="%.4f",
            help="💵 **Cash return volatility**\n\nNear zero (~0.01%). Cash provides stability with minimal fluctuation in returns.",
            key="mc_cash_vol"
        )
    
    # Spending & Guardrails
    st.sidebar.header("Spending & Guardrails")
    st.session_state.cape_now = st.sidebar.number_input(
        "CAPE Ratio",
        value=st.session_state.cape_now,
        help="📊 **Current market valuation metric**\n\nCyclically Adjusted PE Ratio. Used to set initial withdrawal rate:\nBase Rate = 1.75% + 0.5 × (1/CAPE)\n\n• Low CAPE (~15): Higher safe withdrawal\n• High CAPE (~35+): Lower safe withdrawal"
    )

    # Calculate and display CAPE-based withdrawal rate and initial spending
    cape_withdrawal_rate = 0.0175 + 0.5 * (1.0 / st.session_state.cape_now)

    # Get start capital correctly (matches get_current_params logic)
    if st.session_state.use_custom_capital:
        start_capital = st.session_state.custom_capital
    else:
        start_capital = float(st.session_state.capital_preset.replace(',', ''))

    initial_spending_cape = cape_withdrawal_rate * start_capital

    st.sidebar.info(
        f"**CAPE-Based Calculation:**\n"
        f"• Withdrawal Rate: {cape_withdrawal_rate:.2%}\n"
        f"• Initial Year 1 Spending: ${initial_spending_cape:,.0f}"
    )

    # Spending method choice
    if 'spending_method' not in st.session_state:
        st.session_state.spending_method = 'cape'
    if 'initial_base_spending' not in st.session_state:
        st.session_state.initial_base_spending = initial_spending_cape
    if 'fixed_annual_spending' not in st.session_state:
        st.session_state.fixed_annual_spending = initial_spending_cape

    spending_method = st.sidebar.radio(
        "Spending Method",
        options=['cape', 'fixed'],
        format_func=lambda x: {
            'cape': "📊 CAPE-based (with guardrails)",
            'fixed': "🔒 Fixed annual amount"
        }[x],
        index=['cape', 'fixed'].index(st.session_state.spending_method if st.session_state.spending_method in ['cape', 'fixed'] else 'cape'),
        help="Choose spending approach:\n• CAPE: Market-based calculation with guardrails\n• Fixed: Same amount every year (no guardrails)"
    )
    st.session_state.spending_method = spending_method

    if spending_method == 'fixed':
        st.session_state.fixed_annual_spending = st.sidebar.number_input(
            "Fixed Annual Spending",
            value=int(st.session_state.fixed_annual_spending),
            min_value=50_000,
            max_value=1_000_000,
            step=5_000,
            format="%d",
            help="🔒 **Fixed spending every year**\n\nSame amount every year regardless of portfolio performance. No guardrails or adjustments."
        )
    # For 'cape' method, no additional input needed - use CAPE calculation

    # Only show guardrails and spending bounds for CAPE-based spending
    if spending_method == 'cape':
        with st.sidebar.expander("Guardrails (Guyton-Klinger)", expanded=False):
            st.session_state.lower_wr = st.number_input(
                "Lower Guardrail", value=st.session_state.lower_wr, format="%.3f",
                help="📉 **Minimum withdrawal rate trigger**\n\nWhen withdrawal rate falls below this, increase spending by adjustment %. Typically 2.8-3.5%.",
                key="mc_lower_wr"
            )
            st.session_state.upper_wr = st.number_input(
                "Upper Guardrail", value=st.session_state.upper_wr, format="%.3f",
                help="📈 **Maximum withdrawal rate trigger**\n\nWhen withdrawal rate exceeds this, decrease spending by adjustment %. Typically 4.5-6.0%.",
                key="mc_upper_wr"
            )
            st.session_state.adjustment_pct = st.number_input(
                "Adjustment %", value=st.session_state.adjustment_pct, format="%.2f",
                help="⚖️ **Spending adjustment magnitude**\n\nPercentage to increase/decrease spending when guardrails trigger. Typically 10-15%.",
                key="mc_adjustment_pct"
            )

        with st.sidebar.expander("Spending Bounds", expanded=False):
            st.session_state.spending_floor_real = st.number_input(
                "Spending Floor ($)", value=st.session_state.spending_floor_real,
                help="🛡️ **Minimum annual spending**\n\nAbsolute minimum spending level, regardless of portfolio performance. Covers essential expenses.",
                key="mc_spending_floor_real"
            )
            st.session_state.spending_ceiling_real = st.number_input(
                "Spending Ceiling ($)", value=st.session_state.spending_ceiling_real,
                help="🏠 **Maximum annual spending**\n\nCaps spending even when portfolio performs well. Prevents lifestyle inflation and preserves capital.",
                key="mc_spending_ceiling_real"
            )
            st.session_state.floor_end_year = st.number_input(
                "Floor End Year", value=st.session_state.floor_end_year,
                help="📅 **When floor protection ends**\n\nAfter this year, spending can go below the floor if necessary. Allows flexibility in later years.",
                key="mc_floor_end_year"
            )
    else:
        # Fixed spending mode - show info about what's disabled
        st.sidebar.info(
            "🔒 **Fixed Spending Mode**\n\n"
            "Guardrails and spending bounds are disabled. "
            "Your spending will be exactly the same amount every year."
        )
    
    # College Expenses
    st.sidebar.header("College Expenses")
    st.session_state.college_enabled = st.sidebar.checkbox(
        "Enable College Expenses",
        value=st.session_state.college_enabled,
        help="🎓 **Toggle college expense system**\n\nEnable or disable all college-related expenses. When disabled, no college costs are included in the simulation.",
        key="mc_college_enabled"
    )
    
    if st.session_state.college_enabled:
        with st.sidebar.expander("College Configuration", expanded=True):
            st.session_state.college_base_amount = st.number_input(
                "Base Annual Amount ($)",
                value=st.session_state.college_base_amount,
                min_value=0,
                help="💰 **Annual college cost in first year**\n\nBase amount for college expenses in the starting year. This grows each year by the growth rate. Typical range: $50K-$150K per year.",
                key="mc_college_base_amount"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.college_start_year = st.number_input(
                    "Start Year",
                    value=st.session_state.college_start_year,
                    min_value=st.session_state.start_year,
                    max_value=st.session_state.start_year + st.session_state.horizon_years,
                    help="📅 **When college expenses begin**\n\nFirst year college costs are incurred. Typically when your first child starts college.",
                    key="mc_college_start_year"
                )
            
            with col2:
                st.session_state.college_end_year = st.number_input(
                    "End Year",
                    value=st.session_state.college_end_year,
                    min_value=st.session_state.college_start_year,
                    max_value=st.session_state.start_year + st.session_state.horizon_years,
                    help="📅 **When college expenses end**\n\nLast year of college costs. Typically when your last child graduates college.",
                    key="mc_college_end_year"
                )
            
            st.session_state.college_growth_real = st.number_input(
                "Annual Growth Rate",
                value=st.session_state.college_growth_real,
                format="%.3f",
                help="📈 **Real growth in college costs**\n\nAnnual growth rate above inflation. College costs historically grow 1-3% above inflation due to education cost increases.",
                key="mc_college_growth_real"
            )
            
            # Show calculated summary
            if st.session_state.college_enabled:
                duration = st.session_state.college_end_year - st.session_state.college_start_year + 1
                total_base = st.session_state.college_base_amount * duration
                final_year_amount = st.session_state.college_base_amount * (1 + st.session_state.college_growth_real) ** (duration - 1)
                
                st.info(f"📊 **College Summary**\n\n"
                       f"Duration: {duration} years ({st.session_state.college_start_year}-{st.session_state.college_end_year})\n\n"
                       f"First year: ${st.session_state.college_base_amount:,.0f}\n\n"
                       f"Final year: ${final_year_amount:,.0f}\n\n"
                       f"Total (without growth): ${total_base:,.0f}")
    else:
        st.sidebar.info("🚫 College expenses disabled")
    
    # Multi-Year Expenses
    st.sidebar.header("Multi-Year Expenses")
    
    with st.sidebar.expander("Manage Expense Streams", expanded=True):
        # Display existing expense streams
        for i, expense in enumerate(st.session_state.onetime_expenses):
            st.write(f"**Expense Stream {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                new_amount = st.number_input(f"Annual Amount {i+1}", value=expense.get('amount', 50000), min_value=0, key=f"expense_amount_{i}")
                new_start = st.number_input(f"Start Year {i+1}", value=expense.get('start_year', expense.get('year', st.session_state.start_year + 5)), min_value=st.session_state.start_year, key=f"expense_start_{i}")
            with col2:
                new_years = st.number_input(f"Duration {i+1}", value=expense.get('years', 1), min_value=1, key=f"expense_years_{i}")
                if st.button("🗑️ Delete", key=f"delete_expense_{i}", help="Delete this expense stream"):
                    st.session_state.onetime_expenses.pop(i)
                    st.rerun()
            
            # Update the expense stream
            st.session_state.onetime_expenses[i] = {
                'amount': new_amount,
                'start_year': new_start,
                'years': new_years,
                'description': expense.get('description', f'Expense stream {i+1}')
            }
        
        # Add new expense stream button
        if st.button("➕ Add Expense Stream"):
            st.session_state.onetime_expenses.append({
                'amount': 50_000,
                'start_year': st.session_state.start_year + 5,
                'years': 1,
                'description': f'Expense stream {len(st.session_state.onetime_expenses) + 1}'
            })
            st.rerun()
        
        # Show summary if expense streams exist
        if st.session_state.onetime_expenses:
            total_current = sum([expense['amount'] for expense in st.session_state.onetime_expenses])
            st.info(f"💸 Total current annual expenses: ${total_current:,}")
    
    # Real Estate Cash Flow
    st.sidebar.header("Real Estate Cash Flow")
    st.session_state.re_flow_enabled = st.sidebar.checkbox(
        "Enable Real Estate Income",
        value=st.session_state.re_flow_enabled,
        help="🏘️ **Toggle real estate income stream**\n\nEnable or disable all real estate income. When disabled, no RE cash flow is included in the simulation.",
        key="mc_re_flow_enabled"
    )
    
    if st.session_state.re_flow_enabled:
        st.session_state.re_flow_preset = st.sidebar.selectbox(
            "Cash Flow Pattern",
            options=['ramp', 'delayed', 'custom'],
            index=['ramp', 'delayed', 'custom'].index(st.session_state.re_flow_preset),
            help="🏘️ **Real estate income pattern**\n\n**Ramp**: $50K (Yr1) → $60K (Yr2) → $75K (Yr3+)\n**Delayed**: 5-year delay, then ramp up\n**Custom**: Configure your own amounts and timing",
            key="mc_re_flow_preset"
        )
        
        if st.session_state.re_flow_preset == 'custom':
            with st.sidebar.expander("Custom RE Configuration", expanded=True):
                st.session_state.re_flow_start_year = st.number_input(
                    "Start Year",
                    value=st.session_state.re_flow_start_year,
                    min_value=st.session_state.start_year,
                    max_value=st.session_state.start_year + st.session_state.horizon_years,
                    help="📅 **When real estate income begins**\n\nFirst year you expect to receive real estate cash flow.",
                    key="mc_re_flow_start_year"
                )
                
                st.session_state.re_flow_delay_years = st.number_input(
                    "Additional Delay (Years)",
                    value=st.session_state.re_flow_delay_years,
                    key="mc_re_flow_delay_years",
                    min_value=0,
                    max_value=20,
                    help="⏳ **Extra years to delay beyond start year**\n\nAdditional delay before income begins. Total start = Start Year + Delay Years."
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    st.session_state.re_flow_year1_amount = st.number_input(
                        "Year 1 Amount ($)",
                        value=st.session_state.re_flow_year1_amount,
                        min_value=0,
                        help="💰 **First year income amount**\n\nReal estate cash flow in the first year of operation.",
                        key="mc_re_flow_year1_amount"
                    )
                    
                    st.session_state.re_flow_year2_amount = st.number_input(
                        "Year 2 Amount ($)",
                        value=st.session_state.re_flow_year2_amount,
                        min_value=0,
                        help="💰 **Second year income amount**\n\nReal estate cash flow in the second year. Often higher than year 1 due to rent increases or stabilization.",
                        key="mc_re_flow_year2_amount"
                    )
                
                with col2:
                    st.session_state.re_flow_steady_amount = st.number_input(
                        "Ongoing Amount ($)",
                        value=st.session_state.re_flow_steady_amount,
                        min_value=0,
                        help="💰 **Steady-state annual income**\n\nOngoing real estate cash flow from year 3 onwards. The stabilized annual amount.",
                        key="mc_re_flow_steady_amount"
                    )
                
                # Show calculated summary
                effective_start = st.session_state.re_flow_start_year + st.session_state.re_flow_delay_years
                st.info(f"🏠 **RE Income Summary**\n\n"
                       f"Effective start: {effective_start}\n\n"
                       f"Year {effective_start}: ${st.session_state.re_flow_year1_amount:,.0f}\n\n"
                       f"Year {effective_start+1}: ${st.session_state.re_flow_year2_amount:,.0f}\n\n"
                       f"Year {effective_start+2}+: ${st.session_state.re_flow_steady_amount:,.0f}")
        else:
            # Show preset pattern info
            if st.session_state.re_flow_preset == 'ramp':
                st.sidebar.info("📈 **Ramp Pattern**\n\n$50K (Yr1) → $60K (Yr2) → $75K (Yr3+)")
            elif st.session_state.re_flow_preset == 'delayed':
                st.sidebar.info("⏳ **Delayed Pattern**\n\n$0 (Yrs 1-5) → $50K (Yr6) → $60K (Yr7) → $75K (Yr8+)")
    else:
        st.sidebar.info("🚫 Real estate income disabled")
    
    # Inheritance
    st.sidebar.header("Inheritance")
    st.session_state.inherit_amount = st.sidebar.number_input(
        "Inheritance Amount ($)", 
        value=st.session_state.inherit_amount,
        help="🎁 **Expected inheritance**\n\nLump sum added to portfolio in specified year. Real dollars, net of estate taxes and fees."
    )
    st.session_state.inherit_year = st.sidebar.number_input(
        "Inheritance Year", 
        value=st.session_state.inherit_year,
        help="📅 **Year inheritance received**\n\nSpecific year when inheritance is added to portfolio. Plan conservatively."
    )
    
    # Other Income
    st.sidebar.header("Other Income (Net of Tax)")
    
    with st.sidebar.expander("Manage Income Streams", expanded=True):
        # Display existing income streams
        for i, stream in enumerate(st.session_state.other_income_streams):
            st.write(f"**Income Stream {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                new_amount = st.number_input(f"Annual Amount {i+1}", value=stream['amount'], min_value=0, key=f"income_amount_{i}")
                new_start = st.number_input(f"Start Year {i+1}", value=stream['start_year'], min_value=st.session_state.start_year, key=f"income_start_{i}")
            with col2:
                new_years = st.number_input(f"Duration {i+1}", value=stream['years'], min_value=1, key=f"income_years_{i}")
                if st.button("🗑️ Delete", key=f"delete_income_{i}", help="Delete this income stream"):
                    st.session_state.other_income_streams.pop(i)
                    st.rerun()
            
            # Update the income stream
            st.session_state.other_income_streams[i] = {
                'amount': new_amount,
                'start_year': new_start,
                'years': new_years,
                'description': stream.get('description', f'Income stream {i+1}')
            }
        
        # Add new income stream button
        if st.button("➕ Add Income Stream"):
            st.session_state.other_income_streams.append({
                'amount': 25_000,
                'start_year': st.session_state.start_year + 2,
                'years': 5,
                'description': f'Income stream {len(st.session_state.other_income_streams) + 1}'
            })
            st.rerun()
        
        # Show summary if streams exist
        if st.session_state.other_income_streams:
            total_current = sum([stream['amount'] for stream in st.session_state.other_income_streams])
            st.info(f"💰 Total current annual income: ${total_current:,}")
    
    # Tax Parameters
    st.sidebar.header("Tax Model")
    st.session_state.filing_status = st.sidebar.selectbox(
        "Filing Status",
        options=['MFJ', 'Single'],
        index=['MFJ', 'Single'].index(st.session_state.filing_status),
        help="👥 **Tax filing status**\n\nMFJ: Married Filing Jointly\nSingle: Single filer\n\nAffects standard deduction and tax brackets."
    )

    # State tax selection
    state_options = ['Federal Only', 'CA', 'NY', 'TX', 'FL', 'WA', 'NV', 'PA', 'OH', 'IL']
    current_state = st.session_state.get('state_tax', 'CA')
    if current_state not in state_options:
        current_state = 'Federal Only'

    selected_state = st.sidebar.selectbox(
        "State Tax",
        options=state_options,
        index=state_options.index(current_state),
        help="🏛️ **State for combined federal + state tax rates**\n\n"
             "**Federal Only**: Federal taxes only\n"
             "**CA/NY**: High state income tax\n"
             "**TX/FL/WA/NV**: No state income tax\n"
             "**PA/OH/IL**: Moderate state tax\n\n"
             "Rates are rough estimates for retirement income."
    )

    # Update tax brackets if state changed
    if selected_state != st.session_state.get('state_tax', 'CA'):
        st.session_state.state_tax = selected_state
        state_brackets = get_state_tax_rates(selected_state, st.session_state.filing_status)
        st.session_state.bracket_1_threshold = state_brackets[0][0]
        st.session_state.bracket_1_rate = state_brackets[0][1]
        st.session_state.bracket_2_threshold = state_brackets[1][0]
        st.session_state.bracket_2_rate = state_brackets[1][1]
        st.session_state.bracket_3_threshold = state_brackets[2][0]
        st.session_state.bracket_3_rate = state_brackets[2][1]
        st.rerun()

    st.session_state.standard_deduction = st.sidebar.number_input(
        "Standard Deduction ($)",
        value=st.session_state.standard_deduction,
        help="📋 **Standard tax deduction**\n\nAmount deducted from gross income before calculating taxes. 2024: MFJ ~$29K, Single ~$15K.",
        key="mc_standard_deduction"
    )
    
    with st.sidebar.expander("Tax Brackets", expanded=False):
        st.session_state.bracket_1_threshold = st.number_input(
            "Bracket 1 Start ($)", value=st.session_state.bracket_1_threshold,
            help="💰 **First tax bracket threshold**\n\nTaxable income level where this rate starts. Usually $0.",
            key="mc_bracket_1_threshold"
        )
        st.session_state.bracket_1_rate = st.number_input(
            "Bracket 1 Rate", value=st.session_state.bracket_1_rate, format="%.2f",
            help="📊 **Tax rate for first bracket**\n\nDecimal format (0.10 = 10%). Typically 10-12%.",
            key="mc_bracket_1_rate"
        )
        st.session_state.bracket_2_threshold = st.number_input(
            "Bracket 2 Start ($)", value=st.session_state.bracket_2_threshold,
            help="💰 **Second tax bracket threshold**\n\nIncome level where higher rate begins. MFJ ~$94K, Single ~$47K.",
            key="mc_bracket_2_threshold"
        )
        st.session_state.bracket_2_rate = st.number_input(
            "Bracket 2 Rate", value=st.session_state.bracket_2_rate, format="%.2f",
            help="📊 **Tax rate for second bracket**\n\nTypically 22-24%. Applied to income above threshold.",
            key="mc_bracket_2_rate"
        )
        st.session_state.bracket_3_threshold = st.number_input(
            "Bracket 3 Start ($)", value=st.session_state.bracket_3_threshold,
            help="💰 **Third tax bracket threshold**\n\nHigh-income bracket start. MFJ ~$201K, Single ~$100K.",
            key="mc_bracket_3_threshold"
        )
        st.session_state.bracket_3_rate = st.number_input(
            "Bracket 3 Rate", value=st.session_state.bracket_3_rate, format="%.2f",
            help="📊 **Tax rate for third bracket**\n\nHighest rate modeled. Typically 24-32%.",
            key="mc_bracket_3_rate"
        )

    # Social Security Parameters
    st.sidebar.header("Social Security")

    st.session_state.social_security_enabled = st.sidebar.checkbox(
        "Include Social Security",
        value=st.session_state.get('social_security_enabled', True),
        help="✅ **Include Social Security benefits**\n\nAdd estimated Social Security income to retirement projections."
    )

    if st.session_state.social_security_enabled:
        st.session_state.ss_annual_benefit = st.sidebar.number_input(
            "Annual SS Benefit ($)",
            value=int(st.session_state.get('ss_annual_benefit', 40000)),
            min_value=0,
            max_value=200000,
            step=1000,
            help="💰 **Estimated annual Social Security benefit**\n\nFull benefit at your full retirement age. Check your SSA statement for estimates."
        )

        st.session_state.ss_start_age = st.sidebar.number_input(
            "SS Start Age",
            value=st.session_state.get('ss_start_age', 67),
            min_value=62,
            max_value=70,
            help="🎂 **Age to start Social Security**\n\n62: Early (reduced benefits)\n67: Full retirement age\n70: Delayed (increased benefits)"
        )

        scenario_options = ['conservative', 'moderate', 'optimistic', 'custom']
        scenario_labels = {
            'conservative': 'Conservative (19% cut in 2034)',
            'moderate': 'Moderate (gradual cuts, partial reform)',
            'optimistic': 'Optimistic (full benefits maintained)',
            'custom': 'Custom (set your own reduction)'
        }

        st.session_state.ss_benefit_scenario = st.sidebar.selectbox(
            "Funding Scenario",
            options=scenario_options,
            index=scenario_options.index(st.session_state.get('ss_benefit_scenario', 'moderate')),
            format_func=lambda x: scenario_labels[x],
            help="📊 **Social Security trust fund scenarios**\n\n"
                 "**Conservative**: Full 19% benefit cut starting 2034 (current law)\n"
                 "**Moderate**: Gradual cuts with partial Congressional reforms\n"
                 "**Optimistic**: Full benefits through tax increases/reforms\n"
                 "**Custom**: Define your own reduction percentage and timing"
        )

        if st.session_state.ss_benefit_scenario == 'custom':
            st.session_state.ss_custom_reduction = st.sidebar.slider(
                "Custom Reduction %",
                min_value=0.0,
                max_value=0.5,
                value=st.session_state.get('ss_custom_reduction', 0.10),
                step=0.01,
                format="%.1f%%",
                help="🔧 **Custom benefit reduction**\n\nPercentage reduction in benefits starting from the reduction year."
            ) / 100  # Convert percentage to decimal

            st.session_state.ss_reduction_start_year = st.sidebar.number_input(
                "Reduction Start Year",
                value=st.session_state.get('ss_reduction_start_year', 2034),
                min_value=2025,
                max_value=2050,
                help="📅 **Year when benefit reductions begin**\n\nTrustees project 2034 as current depletion date."
            )

        # Spousal Social Security
        st.session_state.spouse_ss_enabled = st.sidebar.checkbox(
            "Include Spouse SS",
            value=st.session_state.get('spouse_ss_enabled', False),
            help="💑 **Include spousal Social Security benefits**\n\nAdd spouse's estimated Social Security income to projections."
        )

        if st.session_state.spouse_ss_enabled:
            st.session_state.spouse_ss_annual_benefit = st.sidebar.number_input(
                "Spouse Annual SS ($)",
                value=int(st.session_state.get('spouse_ss_annual_benefit', 30000)),
                min_value=0,
                max_value=200000,
                step=1000,
                help="💰 **Spouse's annual Social Security benefit**\n\nFull benefit at spouse's full retirement age."
            )

            st.session_state.spouse_ss_start_age = st.sidebar.number_input(
                "Spouse SS Start Age",
                value=st.session_state.get('spouse_ss_start_age', 67),
                min_value=62,
                max_value=70,
                help="🎂 **Age when spouse starts Social Security**\n\n62: Early (reduced)\n67: Full retirement age\n70: Delayed (increased)"
            )

    # Market Regime
    st.sidebar.header("Market Regime")
    
    regime_options = ['baseline', 'recession_recover', 'grind_lower', 'late_recession', 
                     'inflation_shock', 'long_bear', 'tech_bubble', 'custom']
    
    st.session_state.regime = st.sidebar.selectbox(
        "Market Scenario",
        options=regime_options,
        index=regime_options.index(st.session_state.regime) if st.session_state.regime in regime_options else 0,
        help="📈 **Market scenario to model**\n\n"
             "**Baseline**: Expected returns throughout\n"
             "**Recession/Recover**: Early recession (-15% Yr1, 0% Yr2)\n"
             "**Grind Lower**: Poor returns first 10 years\n"
             "**Late Recession**: Recession in years 10-12\n"
             "**Inflation Shock**: High inflation years 3-7\n"
             "**Long Bear**: Extended bear market years 5-15\n"
             "**Tech Bubble**: Boom then bust pattern\n"
             "**Custom**: Configure your own shock timing",
        key="mc_regime"
    )
    
    # Show regime descriptions
    regime_descriptions = {
        'baseline': "📊 Normal expected returns throughout retirement",
        'recession_recover': "📉 Early recession: -15% (Yr1) → 0% (Yr2) → normal",
        'grind_lower': "⬇️ Poor returns (0.5% equity) for first 10 years",
        'late_recession': "📉 Recession in mid-retirement (years 10-12)",
        'inflation_shock': "🔥 High inflation period (years 3-7): bonds hurt, RE benefits",
        'long_bear': "🐻 Extended bear market for 10 years (years 5-15)",
        'tech_bubble': "💻 Tech bubble: high early returns → crash (years 4-6)",
        'custom': "⚙️ User-defined shock pattern"
    }
    
    if st.session_state.regime in regime_descriptions:
        st.sidebar.info(regime_descriptions[st.session_state.regime])
    
    # Custom regime controls
    if st.session_state.regime == 'custom':
        with st.sidebar.expander("Custom Regime Configuration", expanded=True):
            st.session_state.custom_equity_shock_year = st.number_input(
                "Shock Start Year (0-based)",
                value=st.session_state.custom_equity_shock_year,
                min_value=0,
                max_value=st.session_state.horizon_years - 1,
                help="📅 **When the market shock begins**\n\n0 = First year of retirement, 1 = Second year, etc.",
                key="mc_custom_equity_shock_year"
            )
            
            st.session_state.custom_equity_shock_return = st.number_input(
                "Equity Return During Shock",
                value=st.session_state.custom_equity_shock_return,
                min_value=-0.50,
                max_value=0.20,
                format="%.2f",
                help="📈 **Equity return during shock period**\n\nDecimal format (-0.20 = -20%). Typical range: -50% to +20%.",
                key="mc_custom_equity_shock_return"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.custom_shock_duration = st.number_input(
                    "Shock Duration (Years)",
                    value=st.session_state.custom_shock_duration,
                    min_value=1,
                    max_value=10,
                    help="⏱️ **How many years the shock lasts**\n\nTypically 1-3 years for recessions, longer for structural changes.",
                    key="mc_custom_shock_duration"
                )
            
            with col2:
                st.session_state.custom_recovery_years = st.number_input(
                    "Recovery Period (Years)",
                    value=st.session_state.custom_recovery_years,
                    min_value=0,
                    max_value=10,
                    help="🔄 **Years of below-normal returns after shock**\n\nRecovery period with reduced returns before returning to normal.",
                    key="mc_custom_recovery_years"
                )
            
            st.session_state.custom_recovery_equity_return = st.number_input(
                "Equity Return During Recovery",
                value=st.session_state.custom_recovery_equity_return,
                min_value=-0.10,
                max_value=0.15,
                format="%.2f",
                help="📈 **Equity return during recovery period**\n\nTypically positive but below normal expected returns.",
                key="mc_custom_recovery_equity_return"
            )
            
            # Show custom pattern summary
            shock_end = st.session_state.custom_equity_shock_year + st.session_state.custom_shock_duration - 1
            recovery_end = shock_end + st.session_state.custom_recovery_years
            
            st.info(f"🎯 **Custom Pattern Summary**\n\n"
                   f"Shock: Years {st.session_state.custom_equity_shock_year}-{shock_end} "
                   f"({st.session_state.custom_equity_shock_return:.1%})\n\n"
                   f"Recovery: Years {shock_end+1}-{recovery_end} "
                   f"({st.session_state.custom_recovery_equity_return:.1%})\n\n"
                   f"Normal: Year {recovery_end+1}+ (baseline returns)")
    
    # Currency View
    st.sidebar.header("Currency View")
    st.session_state.currency_view = st.sidebar.selectbox(
        "Display Currency", 
        options=['Real', 'Nominal'], 
        index=['Real', 'Nominal'].index(st.session_state.currency_view),
        help="💲 **How to display monetary values**\n\n**Real**: Inflation-adjusted dollars (constant purchasing power)\n**Nominal**: Future dollars (includes inflation effects)\n\nReal dollars are better for planning; nominal shows actual future amounts."
    )
    if st.session_state.currency_view == 'Nominal':
        st.session_state.inflation_rate = st.sidebar.number_input(
            "Inflation Rate", 
            value=st.session_state.inflation_rate, 
            format="%.3f",
            help="📊 **Expected annual inflation**\n\nUsed to convert real dollars to nominal. Historical average ~2.5-3%. Current environment may vary."
        )

    # Save Parameters
    st.sidebar.header("Save Parameters")
    if st.sidebar.button("📄 Download JSON", help="💾 **Download current parameters**\n\nSave all current simulation settings to a JSON file. Use the wizard to load saved parameters later."):
        params = get_current_params()
        json_str = create_parameters_download_json(params)
        st.sidebar.download_button(
            label="💾 Download",
            data=json_str,
            file_name="retirement_parameters.json",
            mime="application/json"
        )




def run_simulations():
    """Run Monte Carlo and deterministic simulations"""
    params = get_current_params()
    current_hash = params_hash(params)
    
    # Check if we need to rerun simulations
    if (st.session_state.simulation_results is None or 
        st.session_state.last_params_hash != current_hash):
        
        with st.spinner("Running Monte Carlo simulation..."):
            simulator = RetirementSimulator(params)
            st.session_state.simulation_results = simulator.run_simulation()
        
        with st.spinner("Running deterministic projection..."):
            projector = DeterministicProjector(params)
            st.session_state.deterministic_results = projector.run_projection()
        
        st.session_state.last_params_hash = current_hash
        st.success("Simulations completed!")


def display_summary_kpis():
    """Display summary KPIs"""
    if st.session_state.simulation_results is None:
        return
    
    results = st.session_state.simulation_results
    terminal_stats = calculate_summary_stats(results.terminal_wealth)
    
    st.header("Summary KPIs")
    
    col1, col2, col3, col4 = st.columns(4)
    
    currency_suffix = "(real)" if st.session_state.currency_view == "Real" else "(nominal)"
    
    # Convert to nominal if needed
    if st.session_state.currency_view == "Nominal":
        inflation_factor = (1 + st.session_state.inflation_rate) ** st.session_state.horizon_years
        for key in ['mean', 'p10', 'p50', 'p90']:
            terminal_stats[key] *= inflation_factor
    
    with col1:
        st.metric("Success Rate", f"{results.success_rate:.1%}")
        st.metric("Median Terminal Wealth", f"${terminal_stats['p50']/1_000_000:.1f}M {currency_suffix}")
    
    with col2:
        st.metric("P10 Terminal Wealth", f"${terminal_stats['p10']/1_000_000:.1f}M {currency_suffix}")
        st.metric("P90 Terminal Wealth", f"${terminal_stats['p90']/1_000_000:.1f}M {currency_suffix}")
    
    with col3:
        st.metric("Prob < $5M", f"{terminal_stats['prob_below_5m']:.1%}")
        st.metric("Prob < $10M", f"{terminal_stats['prob_below_10m']:.1%}")
    
    with col4:
        st.metric("Median Guardrail Hits", f"{np.median(results.guardrail_hits):.0f}")
        st.metric("Prob < $15M", f"{terminal_stats['prob_below_15m']:.1%}")


def display_ai_analysis_section():
    """Display the AI analysis configuration and trigger section"""
    if st.session_state.simulation_results is None:
        return

    st.subheader("🤖 AI Retirement Analysis")

    # Check if user wants AI analysis
    col_ai1, col_ai2 = st.columns([3, 1])

    with col_ai1:
        enable_ai = st.checkbox(
            "Enable AI-powered analysis and recommendations",
            value=st.session_state.get('enable_ai_analysis', False),
            help="Get personalized recommendations based on your simulation results using Google Gemini AI",
            key="mc_enable_ai"
        )
        # Save enable_ai setting if it changed
        if enable_ai != st.session_state.get('enable_ai_analysis', False):
            st.session_state.enable_ai_analysis = enable_ai
            # Save to config file
            ui_config = load_ui_config()
            ui_config['enable_ai_analysis'] = enable_ai
            if 'gemini_api_key' in st.session_state:
                ui_config['gemini_api_key'] = st.session_state.gemini_api_key
            save_ui_config(ui_config)

    if enable_ai:
        # Only show API key instructions if no key is entered
        current_api_key = st.session_state.get('gemini_api_key', '')
        if not current_api_key:
            # Instructions for getting API key
            st.info(
                "🔑 **Get Your Free Gemini API Key:**\n\n"
                "1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)\n"
                "2. Click **'Get API key'** → **'Create API key'**\n"
                "3. Copy your key and paste it below\n\n"
                "**Free Tier:** Gemini 2.5 Pro (100 requests/day), Flash models (higher limits)"
            )

            st.warning(
                "🔒 **PRIVACY WARNING:** Free tier Gemini models may use your retirement data for AI training. "
                "For maximum privacy, use paid Gemini Pro API or disable AI analysis. "
                "Never include real account numbers or sensitive personal details."
            )

        with col_ai2:
            gemini_api_key = st.text_input(
                "🔐 Gemini API Key (Optional)",
                value=st.session_state.get('gemini_api_key', ''),
                type="password",
                help="Paste your free API key from https://aistudio.google.com/app/apikey",
                key="mc_gemini_api_key"
            )

            # Model selection dropdown
            available_models = RetirementAnalyzer.get_available_models()
            model_options = list(available_models.keys())
            model_labels = [f"{key}: {value}" for key, value in available_models.items()]

            selected_model = st.selectbox(
                "🧠 Gemini Model",
                options=model_options,
                index=model_options.index(st.session_state.get('gemini_model', 'gemini-2.5-pro')),
                format_func=lambda x: available_models[x],
                help="Choose the Gemini model for analysis. Flash models are faster, Pro models are more capable.",
                key="mc_selected_model"
            )

            # Save selections if they changed
            settings_changed = False
            if gemini_api_key != st.session_state.get('gemini_api_key', ''):
                st.session_state.gemini_api_key = gemini_api_key
                settings_changed = True
            if selected_model != st.session_state.get('gemini_model', 'gemini-2.5-pro'):
                st.session_state.gemini_model = selected_model
                settings_changed = True

            if settings_changed:
                # Save to config file
                ui_config = load_ui_config()
                ui_config['gemini_api_key'] = gemini_api_key
                ui_config['gemini_model'] = selected_model
                ui_config['enable_ai_analysis'] = enable_ai
                save_ui_config(ui_config)

        st.markdown("---")

        # NEW LOGIC: Check if AI results already exist
        if st.session_state.get('ai_analysis_result') is not None:
            # If they exist, display them
            display_ai_analysis(st.session_state.ai_analysis_result)

            # Offer a button to re-run the analysis
            if st.button("🔄 Re-run AI Analysis", key="rerun_ai_analysis"):
                st.session_state.ai_analysis_result = None
                st.rerun()
        else:
            # If results DON'T exist, create the button first
            analyze_button = st.button(
                "🧠 Run AI Analysis",
                type="primary",
                key="run_ai_analysis_main",
                help="Analyze your simulation results with AI-powered insights",
                disabled=(not gemini_api_key and not enable_ai)
            )

            # Show ready message when not running analysis
            if not (analyze_button or st.session_state.get('force_ai_analysis', False)):
                if gemini_api_key:
                    st.success(f"✅ Ready to analyze with {available_models.get(selected_model, selected_model)}")
                else:
                    st.info("💡 Enter your Gemini API key above for AI-powered insights, or use offline analysis below.")

            # Run analysis when button is clicked
            if analyze_button or st.session_state.get('force_ai_analysis', False):

                # Clear the force flag if it was set
                if 'force_ai_analysis' in st.session_state:
                    del st.session_state.force_ai_analysis

                # Check if simulation results exist
                if st.session_state.simulation_results is None:
                    st.error("❌ No simulation results found. Please run a simulation first.")
                    return

                # Get current results and recalculate stats (needed after button rerun)
                current_results = st.session_state.simulation_results
                current_terminal_stats = calculate_summary_stats(current_results.terminal_wealth)

                if gemini_api_key:
                    try:
                        # Initialize analyzer and perform analysis
                        with st.spinner(f"🧠 Analyzing your retirement plan using {available_models.get(selected_model, selected_model)}..."):
                            analyzer = RetirementAnalyzer(gemini_api_key, selected_model)

                            params = get_current_params()

                            # Store analysis data for chat interface
                            st.session_state.current_analysis_data = analyzer._extract_analysis_data(current_results, params, current_terminal_stats)

                            analysis, error_type = analyzer.analyze_retirement_plan(current_results, params, current_terminal_stats)

                            if analysis is None:
                                # Show specific error message
                                error_msg = APIError.get_user_message(error_type) if error_type else "API not available"
                                st.error(error_msg)

                                # Fall back to mock analysis
                                st.info("💡 Using offline analysis as fallback")
                                analysis = create_mock_analysis(current_results.success_rate, error_type)

                            # Store the analysis result
                            st.session_state.ai_analysis_result = analysis

                    except Exception as e:
                        st.error(f"❌ AI Analysis failed: {str(e)}")
                        return
                else:
                    # Use mock analysis when no API key provided
                    st.info("💡 Using offline analysis. Get a **free** Gemini API key above for AI-powered insights!")
                    analysis = create_mock_analysis(current_results.success_rate)
                    st.session_state.ai_analysis_result = analysis

                # Results will be displayed automatically since ai_analysis_result is now set

    else:
        st.info("💡 Enable AI analysis above for **free** personalized retirement recommendations powered by Google Gemini")



def display_ai_analysis(analysis):
    """Display AI analysis results in a structured format"""

    # Success Assessment
    st.write("**📊 Success Assessment:**")
    st.write(analysis.success_assessment)

    col_analysis1, col_analysis2 = st.columns(2)

    with col_analysis1:
        st.write("**⚠️ Key Risks:**")
        for i, risk in enumerate(analysis.key_risks, 1):
            st.write(f"{i}. {risk}")

    with col_analysis2:
        st.write("**💡 Recommendations:**")
        for rec in analysis.recommendations:
            st.write(f"**{rec['category']}:** {rec['suggestion']}")
            st.caption(f"*Why: {rec['reasoning']}*")
            st.write("")

    # Summary and confidence
    st.write("**📝 Summary:**")
    st.write(analysis.summary)

    # Confidence indicator
    confidence_color = {
        'High': '🟢',
        'Medium': '🟡',
        'Low': '🔴'
    }.get(analysis.confidence_level, '⚪')

    st.caption(f"**Analysis Confidence:** {confidence_color} {analysis.confidence_level}")

    # Add chat interface
    display_chat_interface()


def display_chat_interface():
    """Display interactive chat interface for follow-up questions"""
    api_key = st.session_state.get('gemini_api_key', '')
    if not api_key:
        return

    st.markdown("---")
    st.write("**💬 Chat with AI about your retirement analysis**")

    # Initialize chat history in session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []

    # 1) Display chat history FIRST (so it appears above the input)
    for message in st.session_state.chat_messages:
        with st.chat_message(message['role']):
            st.write(message['content'])

    # 2) Process chat input LAST (so it stays at bottom) - nothing should render after this
    if prompt := st.chat_input("Ask a question about your retirement analysis..."):
        if prompt.strip():
            # Add user message to history
            st.session_state.chat_messages.append({
                'role': 'user',
                'content': prompt
            })

            # Get AI response
            try:
                model = st.session_state.get('gemini_model', 'gemini-2.5-pro')
                analyzer = RetirementAnalyzer(api_key, model)

                # Get analysis data if available
                analysis_data = getattr(st.session_state, 'current_analysis_data', None)

                # Build conversation context from recent messages
                context = ""
                if len(st.session_state.chat_messages) > 1:
                    recent_messages = st.session_state.chat_messages[-6:]  # Last 3 exchanges
                    context = "\n".join([
                        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                        for msg in recent_messages[:-1]  # Exclude the current question
                    ])

                # Get AI response (no spinner here as it interferes with chat flow)
                response, error_type = analyzer.chat_about_analysis(
                    prompt,
                    analysis_data,
                    context if context else None
                )

                if response:
                    # Add AI response to history
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': response
                    })
                else:
                    error_msg = APIError.get_user_message(error_type)
                    # Add error message to history
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': f"Chat error: {error_msg}"
                    })

            except Exception as e:
                # Add error message to history
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': f"Error: {str(e)}"
                })

            # Trigger rerun so new messages appear in the conversation above
            st.rerun()

    # Clear chat button (placed carefully to not interfere with input positioning)
    if len(st.session_state.chat_messages) > 0:
        col1, col2, col3 = st.columns([1, 1, 8])  # Small button, right-aligned
        with col2:
            if st.button("Clear Chat", key="clear_chat"):
                st.session_state.chat_messages = []
                st.rerun()


def display_charts():
    """Display interactive charts"""
    if st.session_state.simulation_results is None:
        return
    
    results = st.session_state.simulation_results
    
    st.header("Charts")
    
    # Terminal wealth distribution
    st.subheader("Terminal Wealth Distribution")
    terminal_wealth = results.terminal_wealth
    if st.session_state.currency_view == "Nominal":
        inflation_factor = (1 + st.session_state.inflation_rate) ** st.session_state.horizon_years
        terminal_wealth = terminal_wealth * inflation_factor
    
    fig = create_terminal_wealth_distribution(
        terminal_wealth, 
        currency_format=st.session_state.currency_view.lower()
    )
    st.plotly_chart(fig, width='stretch')
    
    # Percentile bands
    st.subheader("Wealth Percentile Bands Over Time")
    years = np.arange(st.session_state.start_year, st.session_state.start_year + st.session_state.horizon_years + 1)
    percentiles = calculate_percentiles(results.wealth_paths)
    
    if st.session_state.currency_view == "Nominal":
        for key in percentiles:
            percentiles[key] = convert_to_nominal(
                percentiles[key], st.session_state.start_year, st.session_state.inflation_rate
            )
    
    fig = create_wealth_percentile_bands(
        years, percentiles, 
        currency_format=st.session_state.currency_view.lower()
    )
    st.plotly_chart(fig, width='stretch')
    
    # Withdrawal rate chart (deterministic path)
    if st.session_state.deterministic_results is not None:
        det_results = st.session_state.deterministic_results
        st.subheader("Withdrawal Rate Over Time (Deterministic)")
        
        det_years = np.array(det_results.year_by_year_details['years'])
        withdrawal_rates = np.array(det_results.year_by_year_details['withdrawal_rate'])
        
        fig = create_withdrawal_rate_chart(
            det_years, withdrawal_rates,
            st.session_state.lower_wr, st.session_state.upper_wr
        )
        st.plotly_chart(fig, width='stretch')

        # Income sources stacked area chart
        st.subheader("Income Sources Over Time")
        details = det_results.year_by_year_details

        # Convert to nominal if needed
        if st.session_state.currency_view == "Nominal":
            details = create_nominal_table(
                details, st.session_state.start_year, st.session_state.inflation_rate
            )

        fig = create_income_sources_stacked_area(
            details,
            currency_format=st.session_state.currency_view.lower()
        )
        st.plotly_chart(fig, width='stretch')

        # Asset allocation evolution chart
        st.subheader("Asset Allocation Evolution")
        params = get_current_params()

        fig = create_asset_allocation_evolution(
            params,
            details,
            currency_format=st.session_state.currency_view.lower()
        )
        st.plotly_chart(fig, width='stretch')


def get_percentile_path_details(results, percentile):
    """Get path details for a given percentile using actual simulation data"""
    if percentile == 10:
        return results.p10_path_details
    elif percentile == 50:
        return results.median_path_details
    elif percentile == 90:
        return results.p90_path_details
    else:
        # Default to median for unsupported percentiles
        return results.median_path_details


def display_year_by_year_table():
    """Display year-by-year path table with percentile selection"""
    print(f"DEBUG [display_year_by_year_table]: Called, simulation_results exists: {st.session_state.simulation_results is not None}")
    if st.session_state.simulation_results is None:
        print(f"DEBUG [display_year_by_year_table]: No simulation results, returning early")
        return

    # Path selection dropdown
    col1, col2 = st.columns([1, 3])
    with col1:
        path_selection = st.selectbox(
            "Select Path:",
            options=["P10 (Pessimistic)", "P50 (Median)", "P90 (Optimistic)"],
            index=1,  # Default to P50 (Median)
            help="Choose which simulation path to display:\n• P10: 10th percentile (pessimistic case)\n• P50: 50th percentile (median case)\n• P90: 90th percentile (optimistic case)",
            key="mc_path_selection"
        )
        print(f"DEBUG [Year-by-year]: Path selection changed to: {path_selection}")

    with col2:
        if path_selection == "P10 (Pessimistic)":
            st.header("Year-by-Year Table (P10 - Pessimistic Path)")
        elif path_selection == "P90 (Optimistic)":
            st.header("Year-by-Year Table (P90 - Optimistic Path)")
        else:
            st.header("Year-by-Year Table (P50 - Median Path)")

    # Get appropriate path details
    try:
        if path_selection == "P10 (Pessimistic)":
            print(f"DEBUG [Year-by-year]: Getting P10 path details")
            details = get_percentile_path_details(st.session_state.simulation_results, 10)
            print(f"DEBUG [Year-by-year]: P10 details retrieved, has {len(details)} keys")
            # Debug first few values
            if 'start_assets' in details and len(details['start_assets']) > 3:
                print(f"DEBUG [P10]: First 3 start_assets: {details['start_assets'][:3]}")
        elif path_selection == "P90 (Optimistic)":
            print(f"DEBUG [Year-by-year]: Getting P90 path details")
            details = get_percentile_path_details(st.session_state.simulation_results, 90)
            print(f"DEBUG [Year-by-year]: P90 details retrieved, has {len(details)} keys")
            # Debug first few values
            if 'start_assets' in details and len(details['start_assets']) > 3:
                print(f"DEBUG [P90]: First 3 start_assets: {details['start_assets'][:3]}")
        else:
            print(f"DEBUG [Year-by-year]: Using median path details")
            details = st.session_state.simulation_results.median_path_details
            print(f"DEBUG [Year-by-year]: Median details retrieved, has {len(details)} keys")
            # Debug first few values
            if 'start_assets' in details and len(details['start_assets']) > 3:
                print(f"DEBUG [P50]: First 3 start_assets: {details['start_assets'][:3]}")
    except Exception as e:
        print(f"DEBUG [Year-by-year]: Exception getting path details: {str(e)}")
        st.error(f"❌ Error loading {path_selection} data: {str(e)}")
        return
    
    # Convert to nominal if needed
    if st.session_state.currency_view == "Nominal":
        details = create_nominal_table(
            details, st.session_state.start_year, st.session_state.inflation_rate
        )
    
    # Create DataFrame
    df = pd.DataFrame(details)
    
    # Format currency columns safely
    currency_cols = [col for col in df.columns if any(x in col.lower() for x in 
                    ['asset', 'spend', 'topup', 'income', 'tax', 'need', 'withdrawal', 'growth', 'inherit'])]
    
    for col in currency_cols:
        if col in df.columns:
            try:
                df[col] = df[col].apply(lambda x: f"${float(x):,.0f}" if pd.notna(x) else "")
            except:
                pass  # Keep original values if formatting fails
    
    # Format percentage columns safely
    if 'withdrawal_rate' in df.columns:
        try:
            df['withdrawal_rate'] = df['withdrawal_rate'].apply(
                lambda x: f"{float(x):.1%}" if pd.notna(x) and isinstance(x, (int, float)) else ""
            )
        except:
            pass  # Keep original values if formatting fails
    
    # Display with proper formatting
    st.dataframe(df, width='stretch')
    
    # Download CSV for selected path
    currency_suffix = st.session_state.currency_view.lower()

    # Determine path suffix for filename
    if path_selection == "P10 (Pessimistic)":
        path_suffix = "p10"
        path_label = "P10"
    elif path_selection == "P90 (Optimistic)":
        path_suffix = "p90"
        path_label = "P90"
    else:
        path_suffix = "p50"
        path_label = "P50"

    # Use original details for CSV (not formatted display data)
    csv_details = details if path_selection == "P50 (Median)" else get_percentile_path_details(st.session_state.simulation_results, 10 if "P10" in path_selection else 90 if "P90" in path_selection else 50)

    csv_data = export_year_by_year_csv(csv_details, currency_suffix)

    st.download_button(
        label=f"Download {path_label} Year-by-Year CSV ({currency_suffix.title()})",
        data=csv_data,
        file_name=f"year_by_year_{path_suffix}_{currency_suffix}.csv",
        mime="text/csv"
    )


def display_downloads():
    """Display download section"""
    if st.session_state.simulation_results is None:
        return
    
    st.header("Downloads")
    
    results = st.session_state.simulation_results
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Terminal wealth CSV
        csv_data = export_terminal_wealth_csv(results.terminal_wealth)
        st.download_button(
            label="Download Terminal Wealth CSV",
            data=csv_data,
            file_name="terminal_wealth.csv",
            mime="text/csv"
        )
    
    with col2:
        # Percentile bands CSV
        # wealth_paths includes initial wealth (year 0) + horizon_years, so total length is horizon_years + 1
        years = np.arange(st.session_state.start_year, st.session_state.start_year + results.wealth_paths.shape[1])
        percentiles = calculate_percentiles(results.wealth_paths)

        currency_suffix = st.session_state.currency_view.lower()
        if st.session_state.currency_view == "Nominal":
            for key in percentiles:
                percentiles[key] = convert_to_nominal(
                    percentiles[key], st.session_state.start_year, st.session_state.inflation_rate
                )

        csv_data = export_percentile_bands_csv(years, percentiles, currency_suffix)
        st.download_button(
            label=f"Download Percentile Bands CSV ({currency_suffix.title()})",
            data=csv_data,
            file_name=f"percentile_bands_{currency_suffix}.csv",
            mime="text/csv"
        )
    
    with col3:
        # Summary report JSON
        params = get_current_params()
        report = create_summary_report(params, results, currency_suffix)
        report_json = json.dumps(report, indent=2, default=str)
        
        st.download_button(
            label="Download Summary Report JSON",
            data=report_json,
            file_name="summary_report.json",
            mime="application/json"
        )


st.title("📊 Monte Carlo Analysis")
st.markdown("Advanced retirement simulation with tax-aware withdrawals and guardrails")

def apply_wizard_params_to_monte_carlo():
    """Transfer wizard parameters to Monte Carlo session state."""
    try:
        wizard_params = st.session_state.get('wizard_params', {})
        if not wizard_params:
            return False

        print(f"DEBUG [parameter transfer]: Starting wizard params transfer...")

        # Convert wizard params to JSON format, then to simulation parameters
        wizard_json = convert_wizard_to_json(wizard_params)
        simulation_params_dict = convert_wizard_json_to_simulation_params(wizard_json)

        print(f"DEBUG [parameter transfer]: Converted wizard params to simulation format")

        # Apply parameters with special handling for the dual-mode capital system
        for key, value in simulation_params_dict.items():
            if key == 'start_capital':
                # Handle the dual-mode capital system properly
                st.session_state.use_custom_capital = True  # Switch to custom mode
                st.session_state.custom_capital = value     # Set custom amount
                st.session_state.capital_preset = "Custom"  # Switch to custom mode in dropdown
                print(f"DEBUG [parameter transfer]: Set capital mode - use_custom_capital = True, custom_capital = {value}")
            else:
                st.session_state[key] = value
                print(f"DEBUG [parameter transfer]: Set {key} = {value}")

        # Initialize essential UI variables that widgets need (to prevent crashes)
        essential_ui_vars = {
            'capital_preset': st.session_state.get('capital_preset', "2,500,000"),
            'currency_view': st.session_state.get('currency_view', "Real"),
            'chart_type': st.session_state.get('chart_type', "Terminal Wealth Distribution"),
            'selected_percentile': st.session_state.get('selected_percentile', "Median (P50)"),
            'custom_equity_shock_year': st.session_state.get('custom_equity_shock_year', 0),
            'custom_equity_shock_return': st.session_state.get('custom_equity_shock_return', -0.2),
            'custom_shock_duration': st.session_state.get('custom_shock_duration', 1),
            'custom_recovery_years': st.session_state.get('custom_recovery_years', 2),
            'custom_recovery_equity_return': st.session_state.get('custom_recovery_equity_return', 0.02),
        }

        for var_name, default_value in essential_ui_vars.items():
            if var_name not in st.session_state:
                st.session_state[var_name] = default_value
                print(f"DEBUG [parameter transfer]: Set UI variable {var_name} = {default_value}")

        # Handle expense streams - ensure empty streams clear the UI
        expense_streams = simulation_params_dict.get('expense_streams', [])
        if not expense_streams:
            # Clear the main expense stream array that UI uses
            st.session_state.onetime_expenses = []
            # Clear any existing expense stream session state keys
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith('expense_amount_') or k.startswith('expense_start_') or k.startswith('expense_years_')]
            for key in keys_to_clear:
                del st.session_state[key]
            print(f"DEBUG [parameter transfer]: Cleared expense streams and {len(keys_to_clear)} expense variables")
        else:
            # Set expense streams if they exist
            st.session_state.onetime_expenses = expense_streams

        # Handle income streams - ensure empty streams clear the UI
        income_streams = simulation_params_dict.get('income_streams', [])
        if not income_streams:
            # Clear the main income stream array that UI uses
            st.session_state.other_income_streams = []
            # Clear any existing income stream session state keys
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith('income_amount_') or k.startswith('income_start_') or k.startswith('income_years_')]
            for key in keys_to_clear:
                del st.session_state[key]
            print(f"DEBUG [parameter transfer]: Cleared income streams and {len(keys_to_clear)} income variables")
        else:
            # Set income streams if they exist
            st.session_state.other_income_streams = income_streams

        print(f"DEBUG [parameter transfer]: Successfully transferred all wizard parameters")
        return True

    except Exception as e:
        print(f"ERROR [parameter transfer]: Failed to transfer wizard params: {e}")
        st.error(f"Error transferring parameters from wizard: {e}")
        return False

# Initialize session state first (required for UI components)
if not st.session_state.get('monte_carlo_initialized', False):
    initialize_session_state()
    st.session_state.monte_carlo_initialized = True

# Check if wizard was completed and apply wizard parameters AFTER session state initialization
if st.session_state.get('wizard_completed', False) and not st.session_state.get('parameters_loaded', False):
    st.write("🔧 DEBUG: Wizard completed flag detected, attempting parameter transfer...")
    print(f"DEBUG [parameter transfer]: Wizard completed, applying parameters...")
    if apply_wizard_params_to_monte_carlo():
        st.session_state.parameters_loaded = True
        st.success("✅ Parameters loaded from wizard successfully!")
        st.write(f"🔧 DEBUG: Custom capital set to: {st.session_state.get('custom_capital', 'NOT SET')}")
        st.write(f"🔧 DEBUG: Use custom capital: {st.session_state.get('use_custom_capital', 'NOT SET')}")
        st.write(f"🔧 DEBUG: w_equity: {st.session_state.get('w_equity', 'NOT SET')}")
        st.write(f"🔧 DEBUG: w_bonds: {st.session_state.get('w_bonds', 'NOT SET')}")
        st.write(f"🔧 DEBUG: expense_streams: {st.session_state.get('expense_streams', 'NOT SET')}")

        # Show ALL session state keys for debugging
        st.write("🔧 DEBUG: All session state keys:")
        debug_keys = [k for k in st.session_state.keys() if not k.startswith('FormSubmitter')]
        st.write(f"Keys: {sorted(debug_keys)[:20]}...")  # Show first 20 keys
        print(f"DEBUG [parameter transfer]: Parameters loaded and marked as complete")
        # Rerun to refresh UI with new parameter values
        st.rerun()

# Initialize session state if not done already
if not st.session_state.get('parameters_loaded', False):
    st.info("""
    🧙‍♂️ **New to retirement planning?** Try the **Setup Wizard** first for guided parameter configuration!

    The wizard guides you through parameter setup with beautiful visualizations and educational content.

    **Quick Access:** Use the sidebar navigation to switch to the Setup Wizard page.
    """)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🧙‍♂️ Go to Setup Wizard", type="primary"):
            st.switch_page("pages/wizard.py")

    # Session state already initialized above

# Now that parameters are loaded (either from wizard or defaults), show the main interface
# Create sidebar
create_sidebar()

# Main content
tab1, tab2, tab3 = st.tabs(["Run Simulation", "Charts", "Year-by-Year"])

with tab1:
    # Validation
    total_weight = st.session_state.w_equity + st.session_state.w_bonds + st.session_state.w_real_estate + st.session_state.w_cash
    if abs(total_weight - 1.0) > 1e-6:
        st.error(f"⚠️ Allocation weights must sum to 1.0. Current sum: {total_weight:.3f}")
        st.stop()

    # Run simulation button
    if st.button("🚀 Run Simulation", type="primary"):
        run_simulations()

    # Display summary KPIs
    display_summary_kpis()

    # Display AI analysis section
    display_ai_analysis_section()

with tab2:
    display_charts()

with tab3:
    display_year_by_year_table()

# Downloads section moved to end of page
display_downloads()

# Footer
st.markdown("---")
st.markdown("Built with Streamlit • Monte Carlo simulation with tax-aware withdrawals")