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
        other_income_amount=sum([stream['amount'] for stream in st.session_state.other_income_streams]),
        other_income_start_year=min([stream['start_year'] for stream in st.session_state.other_income_streams]) if st.session_state.other_income_streams else 2026,
        other_income_years=max([stream['start_year'] + stream['years'] for stream in st.session_state.other_income_streams]) - min([stream['start_year'] for stream in st.session_state.other_income_streams]) if st.session_state.other_income_streams else 0,
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
    params_str = str(params.__dict__)
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
            help="📊 **Expected annual real return for stocks**\n\nHistorical average ~7% nominal, ~5% real after inflation. Accounts for long-term economic growth and corporate earnings."
        )
        st.session_state.bonds_mean = st.number_input(
            "Bonds Mean", value=st.session_state.bonds_mean, format="%.3f",
            help="🏛️ **Expected annual real return for bonds**\n\nDepends on interest rates and credit quality. Currently low due to low yields. Historical real returns ~1-3%."
        )
        st.session_state.real_estate_mean = st.number_input(
            "Real Estate Mean", value=st.session_state.real_estate_mean, format="%.3f",
            help="🏘️ **Expected annual real return for REITs**\n\nCombines rental income and property appreciation. Historically ~2-4% real returns with inflation protection."
        )
        st.session_state.cash_mean = st.number_input(
            "Cash Mean", value=st.session_state.cash_mean, format="%.3f",
            help="💵 **Expected annual real return for cash**\n\nTypically near zero real return (matches inflation). Provides stability and liquidity, not growth."
        )
    
    with st.sidebar.expander("Volatilities", expanded=False):
        st.session_state.equity_vol = st.number_input(
            "Equity Volatility", value=st.session_state.equity_vol, format="%.3f",
            help="📈 **Annual return volatility (standard deviation)**\n\nMeasures year-to-year variability. Equity: ~15-20%. Higher volatility = wider range of possible outcomes."
        )
        st.session_state.bonds_vol = st.number_input(
            "Bonds Volatility", value=st.session_state.bonds_vol, format="%.3f",
            help="🏛️ **Bond return volatility**\n\nTypically 5-10%. Lower than stocks but still varies with interest rate changes and credit events."
        )
        st.session_state.real_estate_vol = st.number_input(
            "Real Estate Volatility", value=st.session_state.real_estate_vol, format="%.3f",
            help="🏘️ **REIT return volatility**\n\nTypically 8-15%. Less volatile than stocks, more than bonds. Affected by interest rates and property cycles."
        )
        st.session_state.cash_vol = st.number_input(
            "Cash Volatility", value=st.session_state.cash_vol, format="%.4f",
            help="💵 **Cash return volatility**\n\nNear zero (~0.01%). Cash provides stability with minimal fluctuation in returns."
        )
    
    # Spending & Guardrails
    st.sidebar.header("Spending & Guardrails")
    st.session_state.cape_now = st.sidebar.number_input(
        "CAPE Ratio", 
        value=st.session_state.cape_now,
        help="📊 **CAPE = Cyclically Adjusted P/E Ratio** (Market Valuation)\n\n"
             "What it is: Stock market 'expensiveness' smoothed over 10 years\n"
             "• Low CAPE (15-20): Stocks cheap → Higher safe withdrawal rates\n"
             "• High CAPE (30-40): Stocks expensive → Lower safe withdrawal rates\n\n"
             "How we use it: Sets your initial withdrawal rate\n"
             "Formula: Base 1.75% + 0.5 × (1/CAPE)\n\n"
             "Current market: ~28-35 (check Robert Shiller's data)\n"
             "Historical range: 5 (1920s) to 45+ (dot-com bubble)"
    )
    
    with st.sidebar.expander("Guardrails (Guyton-Klinger)", expanded=False):
        st.session_state.lower_wr = st.number_input(
            "Lower Guardrail", value=st.session_state.lower_wr, format="%.3f",
            help="📉 **Minimum withdrawal rate trigger**\n\nWhen withdrawal rate falls below this, increase spending by adjustment %. Typically 2.8-3.5%."
        )
        st.session_state.upper_wr = st.number_input(
            "Upper Guardrail", value=st.session_state.upper_wr, format="%.3f", 
            help="📈 **Maximum withdrawal rate trigger**\n\nWhen withdrawal rate exceeds this, decrease spending by adjustment %. Typically 4.5-6.0%."
        )
        st.session_state.adjustment_pct = st.number_input(
            "Adjustment %", value=st.session_state.adjustment_pct, format="%.2f",
            help="⚖️ **Spending adjustment magnitude**\n\nPercentage to increase/decrease spending when guardrails trigger. Typically 10-15%."
        )
    
    with st.sidebar.expander("Spending Bounds", expanded=False):
        st.session_state.spending_floor_real = st.number_input(
            "Spending Floor ($)", value=st.session_state.spending_floor_real,
            help="🛡️ **Minimum annual spending**\n\nAbsolute minimum spending level, regardless of portfolio performance. Covers essential expenses."
        )
        st.session_state.spending_ceiling_real = st.number_input(
            "Spending Ceiling ($)", value=st.session_state.spending_ceiling_real,
            help="🏠 **Maximum annual spending**\n\nCaps spending even when portfolio performs well. Prevents lifestyle inflation and preserves capital."
        )
        st.session_state.floor_end_year = st.number_input(
            "Floor End Year", value=st.session_state.floor_end_year,
            help="📅 **When floor protection ends**\n\nAfter this year, spending can go below the floor if necessary. Allows flexibility in later years."
        )
    
    # College Expenses
    st.sidebar.header("College Expenses")
    st.session_state.college_enabled = st.sidebar.checkbox(
        "Enable College Expenses",
        value=st.session_state.college_enabled,
        help="🎓 **Toggle college expense system**\n\nEnable or disable all college-related expenses. When disabled, no college costs are included in the simulation."
    )
    
    if st.session_state.college_enabled:
        with st.sidebar.expander("College Configuration", expanded=True):
            st.session_state.college_base_amount = st.number_input(
                "Base Annual Amount ($)", 
                value=st.session_state.college_base_amount,
                min_value=0,
                help="💰 **Annual college cost in first year**\n\nBase amount for college expenses in the starting year. This grows each year by the growth rate. Typical range: $50K-$150K per year."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.college_start_year = st.number_input(
                    "Start Year", 
                    value=st.session_state.college_start_year,
                    min_value=st.session_state.start_year,
                    max_value=st.session_state.start_year + st.session_state.horizon_years,
                    help="📅 **When college expenses begin**\n\nFirst year college costs are incurred. Typically when your first child starts college."
                )
            
            with col2:
                st.session_state.college_end_year = st.number_input(
                    "End Year", 
                    value=st.session_state.college_end_year,
                    min_value=st.session_state.college_start_year,
                    max_value=st.session_state.start_year + st.session_state.horizon_years,
                    help="📅 **When college expenses end**\n\nLast year of college costs. Typically when your last child graduates college."
                )
            
            st.session_state.college_growth_real = st.number_input(
                "Annual Growth Rate", 
                value=st.session_state.college_growth_real, 
                format="%.3f",
                help="📈 **Real growth in college costs**\n\nAnnual growth rate above inflation. College costs historically grow 1-3% above inflation due to education cost increases."
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
        help="🏘️ **Toggle real estate income stream**\n\nEnable or disable all real estate income. When disabled, no RE cash flow is included in the simulation."
    )
    
    if st.session_state.re_flow_enabled:
        st.session_state.re_flow_preset = st.sidebar.selectbox(
            "Cash Flow Pattern", 
            options=['ramp', 'delayed', 'custom'], 
            index=['ramp', 'delayed', 'custom'].index(st.session_state.re_flow_preset),
            help="🏘️ **Real estate income pattern**\n\n**Ramp**: $50K (Yr1) → $60K (Yr2) → $75K (Yr3+)\n**Delayed**: 5-year delay, then ramp up\n**Custom**: Configure your own amounts and timing"
        )
        
        if st.session_state.re_flow_preset == 'custom':
            with st.sidebar.expander("Custom RE Configuration", expanded=True):
                st.session_state.re_flow_start_year = st.number_input(
                    "Start Year", 
                    value=st.session_state.re_flow_start_year,
                    min_value=st.session_state.start_year,
                    max_value=st.session_state.start_year + st.session_state.horizon_years,
                    help="📅 **When real estate income begins**\n\nFirst year you expect to receive real estate cash flow."
                )
                
                st.session_state.re_flow_delay_years = st.number_input(
                    "Additional Delay (Years)", 
                    value=st.session_state.re_flow_delay_years,
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
                        help="💰 **First year income amount**\n\nReal estate cash flow in the first year of operation."
                    )
                    
                    st.session_state.re_flow_year2_amount = st.number_input(
                        "Year 2 Amount ($)", 
                        value=st.session_state.re_flow_year2_amount,
                        min_value=0,
                        help="💰 **Second year income amount**\n\nReal estate cash flow in the second year. Often higher than year 1 due to rent increases or stabilization."
                    )
                
                with col2:
                    st.session_state.re_flow_steady_amount = st.number_input(
                        "Ongoing Amount ($)", 
                        value=st.session_state.re_flow_steady_amount,
                        min_value=0,
                        help="💰 **Steady-state annual income**\n\nOngoing real estate cash flow from year 3 onwards. The stabilized annual amount."
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
        help="📋 **Standard tax deduction**\n\nAmount deducted from gross income before calculating taxes. 2024: MFJ ~$29K, Single ~$15K."
    )
    
    with st.sidebar.expander("Tax Brackets", expanded=False):
        st.session_state.bracket_1_threshold = st.number_input(
            "Bracket 1 Start ($)", value=st.session_state.bracket_1_threshold,
            help="💰 **First tax bracket threshold**\n\nTaxable income level where this rate starts. Usually $0."
        )
        st.session_state.bracket_1_rate = st.number_input(
            "Bracket 1 Rate", value=st.session_state.bracket_1_rate, format="%.2f",
            help="📊 **Tax rate for first bracket**\n\nDecimal format (0.10 = 10%). Typically 10-12%."
        )
        st.session_state.bracket_2_threshold = st.number_input(
            "Bracket 2 Start ($)", value=st.session_state.bracket_2_threshold,
            help="💰 **Second tax bracket threshold**\n\nIncome level where higher rate begins. MFJ ~$94K, Single ~$47K."
        )
        st.session_state.bracket_2_rate = st.number_input(
            "Bracket 2 Rate", value=st.session_state.bracket_2_rate, format="%.2f",
            help="📊 **Tax rate for second bracket**\n\nTypically 22-24%. Applied to income above threshold."
        )
        st.session_state.bracket_3_threshold = st.number_input(
            "Bracket 3 Start ($)", value=st.session_state.bracket_3_threshold,
            help="💰 **Third tax bracket threshold**\n\nHigh-income bracket start. MFJ ~$201K, Single ~$100K."
        )
        st.session_state.bracket_3_rate = st.number_input(
            "Bracket 3 Rate", value=st.session_state.bracket_3_rate, format="%.2f",
            help="📊 **Tax rate for third bracket**\n\nHighest rate modeled. Typically 24-32%."
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
            value=st.session_state.get('ss_annual_benefit', 40000),
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
                value=st.session_state.get('spouse_ss_annual_benefit', 30000),
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
             "**Custom**: Configure your own shock timing"
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
                help="📅 **When the market shock begins**\n\n0 = First year of retirement, 1 = Second year, etc."
            )
            
            st.session_state.custom_equity_shock_return = st.number_input(
                "Equity Return During Shock", 
                value=st.session_state.custom_equity_shock_return,
                min_value=-0.50,
                max_value=0.20,
                format="%.2f",
                help="📈 **Equity return during shock period**\n\nDecimal format (-0.20 = -20%). Typical range: -50% to +20%."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.custom_shock_duration = st.number_input(
                    "Shock Duration (Years)", 
                    value=st.session_state.custom_shock_duration,
                    min_value=1,
                    max_value=10,
                    help="⏱️ **How many years the shock lasts**\n\nTypically 1-3 years for recessions, longer for structural changes."
                )
            
            with col2:
                st.session_state.custom_recovery_years = st.number_input(
                    "Recovery Period (Years)", 
                    value=st.session_state.custom_recovery_years,
                    min_value=0,
                    max_value=10,
                    help="🔄 **Years of below-normal returns after shock**\n\nRecovery period with reduced returns before returning to normal."
                )
            
            st.session_state.custom_recovery_equity_return = st.number_input(
                "Equity Return During Recovery", 
                value=st.session_state.custom_recovery_equity_return,
                min_value=-0.10,
                max_value=0.15,
                format="%.2f",
                help="📈 **Equity return during recovery period**\n\nTypically positive but below normal expected returns."
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


def save_load_section():
    """Create save/load parameters section"""
    st.header("Save/Load Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Save Parameters")
        if st.button("Download Parameters JSON"):
            params = get_current_params()
            json_str = create_parameters_download_json(params)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name="retirement_parameters.json",
                mime="application/json"
            )
    
    with col2:
        st.subheader("Load Parameters")
        uploaded_file = st.file_uploader("Upload Parameters JSON", type=['json'])
        
        if uploaded_file is not None:
            # Show file info and load button
            st.info(f"📁 Selected: {uploaded_file.name} ({uploaded_file.size} bytes)")
            
            if st.button("Load Parameters", type="primary"):
                try:
                    json_str = uploaded_file.read().decode('utf-8')
                    is_valid, error = validate_parameters_json(json_str)
                    
                    if is_valid:
                        params = parse_parameters_upload_json(json_str)
                    
                        # Update session state - ALL parameters
                        st.session_state.start_year = params.start_year
                        st.session_state.horizon_years = params.horizon_years
                        st.session_state.num_sims = params.num_sims
                        st.session_state.random_seed = params.random_seed
                        
                        # Capital and allocation
                        st.session_state.custom_capital = params.start_capital
                        st.session_state.use_custom_capital = True
                        st.session_state.w_equity = params.w_equity
                        st.session_state.w_bonds = params.w_bonds
                        st.session_state.w_real_estate = params.w_real_estate
                        st.session_state.w_cash = params.w_cash
                        
                        # Return model
                        st.session_state.equity_mean = params.equity_mean
                        st.session_state.equity_vol = params.equity_vol
                        st.session_state.bonds_mean = params.bonds_mean
                        st.session_state.bonds_vol = params.bonds_vol
                        st.session_state.real_estate_mean = params.real_estate_mean
                        st.session_state.real_estate_vol = params.real_estate_vol
                        st.session_state.cash_mean = params.cash_mean
                        st.session_state.cash_vol = params.cash_vol
                        
                        # CAPE and guardrails
                        st.session_state.cape_now = params.cape_now
                        st.session_state.lower_wr = params.lower_wr
                        st.session_state.upper_wr = params.upper_wr
                        st.session_state.adjustment_pct = params.adjustment_pct
                        
                        # Spending bounds
                        st.session_state.spending_floor_real = params.spending_floor_real
                        st.session_state.spending_ceiling_real = params.spending_ceiling_real
                        st.session_state.floor_end_year = params.floor_end_year
                        
                        # College expenses
                        st.session_state.college_enabled = params.college_enabled
                        st.session_state.college_base_amount = params.college_base_amount
                        st.session_state.college_start_year = params.college_start_year
                        st.session_state.college_end_year = params.college_end_year
                        st.session_state.college_growth_real = params.college_growth_real
                        
                        # Multi-year expenses - use expense streams directly
                        st.session_state.onetime_expenses = params.expense_streams or []
                        
                        # Real estate
                        st.session_state.re_flow_enabled = params.re_flow_enabled
                        st.session_state.re_flow_preset = params.re_flow_preset
                        st.session_state.re_flow_start_year = params.re_flow_start_year
                        st.session_state.re_flow_year1_amount = params.re_flow_year1_amount
                        st.session_state.re_flow_year2_amount = params.re_flow_year2_amount
                        st.session_state.re_flow_steady_amount = params.re_flow_steady_amount
                        st.session_state.re_flow_delay_years = params.re_flow_delay_years
                        
                        # Inheritance
                        st.session_state.inherit_amount = params.inherit_amount
                        st.session_state.inherit_year = params.inherit_year
                        
                        # Other income - convert from aggregated back to UI list format
                        other_income_streams = []
                        if params.other_income_amount > 0 and params.other_income_years > 0:
                            other_income_streams.append({
                                'amount': params.other_income_amount,
                                'start_year': params.other_income_start_year,
                                'years': params.other_income_years,
                                'description': 'Loaded from file'
                            })
                        st.session_state.other_income_streams = other_income_streams
                        
                        # Tax parameters
                        st.session_state.filing_status = params.filing_status
                        st.session_state.standard_deduction = params.standard_deduction
                        if params.tax_brackets:
                            # Convert back to individual session state values
                            if len(params.tax_brackets) >= 1:
                                st.session_state.bracket_1_threshold = params.tax_brackets[0][0]
                                st.session_state.bracket_1_rate = params.tax_brackets[0][1]
                            if len(params.tax_brackets) >= 2:
                                st.session_state.bracket_2_threshold = params.tax_brackets[1][0]
                                st.session_state.bracket_2_rate = params.tax_brackets[1][1]
                            if len(params.tax_brackets) >= 3:
                                st.session_state.bracket_3_threshold = params.tax_brackets[2][0]
                                st.session_state.bracket_3_rate = params.tax_brackets[2][1]
                        
                        # Market regime
                        st.session_state.regime = params.regime
                        st.session_state.custom_equity_shock_year = params.custom_equity_shock_year
                        st.session_state.custom_equity_shock_return = params.custom_equity_shock_return
                        st.session_state.custom_shock_duration = params.custom_shock_duration
                        st.session_state.custom_recovery_years = params.custom_recovery_years
                        st.session_state.custom_recovery_equity_return = params.custom_recovery_equity_return
                        
                        # Clear old simulation results since parameters changed
                        st.session_state.simulation_results = None
                        st.session_state.deterministic_results = None
                        
                        st.success("Parameters loaded successfully!")
                        st.rerun()
                    else:
                        st.error(f"Invalid parameters file: {error}")
                except Exception as e:
                    st.error(f"Error loading parameters: {str(e)}")


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

    # AI Analysis Section
    st.subheader("🤖 AI Retirement Analysis")

    # Check if user wants AI analysis
    col_ai1, col_ai2 = st.columns([3, 1])

    with col_ai1:
        enable_ai = st.checkbox(
            "Enable AI-powered analysis and recommendations",
            value=st.session_state.get('enable_ai_analysis', False),
            help="Get personalized recommendations based on your simulation results using Google Gemini AI"
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

        with col_ai2:
            gemini_api_key = st.text_input(
                "🔐 Gemini API Key (Optional)",
                value=st.session_state.get('gemini_api_key', ''),
                type="password",
                help="Paste your free API key from https://aistudio.google.com/app/apikey"
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
                help="Choose the Gemini model for analysis. Flash models are faster, Pro models are more capable."
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

        if gemini_api_key:
            # Initialize analyzer and perform analysis
            with st.spinner(f"🧠 Analyzing your retirement plan using {available_models.get(selected_model, selected_model)}..."):
                analyzer = RetirementAnalyzer(gemini_api_key, selected_model)
                params = get_current_params()
                # Store analysis data for chat interface
                st.session_state.current_analysis_data = analyzer._extract_analysis_data(results, params, terminal_stats)
                analysis, error_type = analyzer.analyze_retirement_plan(results, params, terminal_stats)

                if analysis is None:
                    # Show specific error message
                    error_msg = APIError.get_user_message(error_type) if error_type else "API not available"
                    st.error(error_msg)

                    # Fall back to mock analysis
                    st.info("💡 Using offline analysis as fallback")
                    analysis = create_mock_analysis(results.success_rate, error_type)

        else:
            # Use mock analysis when no API key provided
            st.info("💡 Using offline analysis. Get a **free** Gemini API key above for AI-powered insights!")
            analysis = create_mock_analysis(results.success_rate)

        # Display analysis results
        if 'analysis' in locals():
            display_ai_analysis(analysis)
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

    # Display chat history
    for message in st.session_state.chat_messages:
        if message['role'] == 'user':
            st.write(f"**You:** {message['content']}")
        else:
            st.write(f"**AI:** {message['content']}")
        st.write("")

    # Chat input
    user_question = st.text_input(
        "Ask a question about your retirement analysis:",
        placeholder="e.g., What if I retire 2 years earlier? How does inflation affect my plan?",
        key="chat_input"
    )

    if st.button("Send", key="chat_send"):
        if user_question.strip():
            # Add user message to history
            st.session_state.chat_messages.append({
                'role': 'user',
                'content': user_question
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

                response, error_type = analyzer.chat_about_analysis(
                    user_question,
                    analysis_data,
                    context if context else None
                )

                if response:
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': response
                    })
                    st.rerun()
                else:
                    error_msg = APIError.get_user_message(error_type)
                    st.error(f"Chat error: {error_msg}")

            except Exception as e:
                st.error(f"Error: {str(e)}")

    # Clear chat button
    if len(st.session_state.chat_messages) > 0:
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


def display_year_by_year_table():
    """Display year-by-year median path table"""
    if st.session_state.simulation_results is None:
        return
    
    st.header("Year-by-Year Table (Median Path)")
    
    # Get median path details
    details = st.session_state.simulation_results.median_path_details
    
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
    
    # Download CSV
    currency_suffix = st.session_state.currency_view.lower()
    csv_data = export_year_by_year_csv(
        st.session_state.simulation_results.median_path_details, currency_suffix
    )
    
    st.download_button(
        label=f"Download Year-by-Year CSV ({currency_suffix.title()})",
        data=csv_data,
        file_name=f"year_by_year_{currency_suffix}.csv",
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
        years = np.arange(st.session_state.start_year, st.session_state.start_year + st.session_state.horizon_years + 1)
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


def main():
    """Main application"""
    st.set_page_config(
        page_title="Retirement Monte Carlo Simulator",
        page_icon="💰",
        layout="wide"
    )
    
    st.title("💰 Retirement Monte Carlo Simulator")
    st.markdown("Advanced retirement simulation with tax-aware withdrawals and guardrails")

    # Wizard promotion for new users
    if not st.session_state.get('parameters_loaded', False):
        st.info("""
        🧙‍♂️ **New to retirement planning?** Try the [**Interactive Setup Wizard**](http://localhost:8502) first!

        The wizard guides you through parameter setup with beautiful visualizations and educational content,
        then generates a configuration file you can upload here.
        """)

    # Initialize session state
    initialize_session_state()
    
    # Create sidebar
    create_sidebar()
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["Run Simulation", "Charts", "Year-by-Year", "Save/Load"])
    
    with tab1:
        # Validation
        total_weight = st.session_state.w_equity + st.session_state.w_bonds + st.session_state.w_real_estate + st.session_state.w_cash
        if abs(total_weight - 1.0) > 1e-6:
            st.error(f"⚠️ Allocation weights must sum to 1.0. Current sum: {total_weight:.3f}")
            st.stop()
        
        # Initial base withdrawal rate warning
        params = get_current_params()
        base_wr = 0.0175 + 0.5 * (1.0 / params.cape_now)
        if base_wr > params.upper_wr:
            st.warning(f"⚠️ Initial withdrawal rate ({base_wr:.1%}) exceeds upper guardrail ({params.upper_wr:.1%})")
        
        # Run simulations button
        if st.button("🚀 Run Simulation", type="primary"):
            run_simulations()
        
        # Display results if available
        if st.session_state.simulation_results is not None:
            display_summary_kpis()
            display_downloads()
    
    with tab2:
        display_charts()
    
    with tab3:
        display_year_by_year_table()
    
    with tab4:
        save_load_section()
    
    # Footer
    st.markdown("---")
    st.markdown("Built with Streamlit • Monte Carlo simulation with tax-aware withdrawals")


if __name__ == "__main__":
    main()