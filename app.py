"""
Streamlit web application for Monte Carlo retirement simulation.
Provides intuitive UI for configuring assumptions and viewing results.
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
    create_tax_analysis_chart
)
from io_utils import (
    create_parameters_download_json, parse_parameters_upload_json,
    export_terminal_wealth_csv, export_percentile_bands_csv, export_year_by_year_csv,
    validate_parameters_json, format_currency, create_summary_report
)


def initialize_session_state():
    """Initialize session state variables with defaults for hypothetical CA family ($250K income)"""
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
        'college_growth_real': 0.015,  # Slightly above inflation
        
        # One-time expenses (realistic family expenses)
        'onetime_expenses': [
            {'year': 2030, 'amount': 75_000, 'description': 'Home renovation'},
            {'year': 2035, 'amount': 50_000, 'description': 'Vehicle replacement'},
            {'year': 2045, 'amount': 60_000, 'description': 'Healthcare/mobility upgrades'}
        ],
        
        # Real estate cash flow (no rental income initially)
        're_flow_preset': 'delayed',
        
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
        'bracket_1_threshold': 0,
        'bracket_1_rate': 0.10,
        'bracket_2_threshold': 94_300,
        'bracket_2_rate': 0.22,
        'bracket_3_threshold': 201_000,
        'bracket_3_rate': 0.24,  # Simplified - CA has additional state taxes
        
        # Regime (baseline for demo)
        'regime': 'baseline',
        
        # Results caching
        'simulation_results': None,
        'deterministic_results': None,
        'last_params_hash': None,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
        college_growth_real=st.session_state.college_growth_real,
        onetime_2033=sum([exp['amount'] for exp in st.session_state.onetime_expenses if exp['year'] == 2033]),
        onetime_2040=sum([exp['amount'] for exp in st.session_state.onetime_expenses if exp['year'] == 2040]),
        re_flow_preset=st.session_state.re_flow_preset,
        inherit_amount=st.session_state.inherit_amount,
        inherit_year=st.session_state.inherit_year,
        other_income_amount=sum([stream['amount'] for stream in st.session_state.other_income_streams]),
        other_income_start_year=min([stream['start_year'] for stream in st.session_state.other_income_streams]) if st.session_state.other_income_streams else 2026,
        other_income_years=max([stream['start_year'] + stream['years'] for stream in st.session_state.other_income_streams]) - min([stream['start_year'] for stream in st.session_state.other_income_streams]) if st.session_state.other_income_streams else 0,
        filing_status=st.session_state.filing_status,
        standard_deduction=st.session_state.standard_deduction,
        tax_brackets=tax_brackets,
        regime=st.session_state.regime
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
        help="📊 **Current market valuation metric**\n\nCyclically Adjusted PE Ratio. Used to set initial withdrawal rate:\nBase Rate = 1.75% + 0.5 × (1/CAPE)\n\n• Low CAPE (~15): Higher safe withdrawal\n• High CAPE (~35+): Lower safe withdrawal"
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
    
    # College Top-Up
    st.sidebar.header("College Top-Up")
    st.session_state.college_growth_real = st.sidebar.number_input(
        "College Growth Rate", 
        value=st.session_state.college_growth_real, 
        format="%.3f",
        help="🎓 **Annual growth in college costs**\n\nReal growth rate for college expenses (2032-2041). Base amount $100K in 2032, growing annually. Typical: 1-3% above inflation."
    )
    
    # One-Time Expenses
    st.sidebar.header("One-Time Expenses")
    
    with st.sidebar.expander("Manage One-Time Expenses", expanded=True):
        # Display existing expenses
        for i, expense in enumerate(st.session_state.onetime_expenses):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                new_year = st.number_input(f"Year {i+1}", value=expense['year'], min_value=st.session_state.start_year, max_value=st.session_state.start_year + st.session_state.horizon_years, key=f"expense_year_{i}")
            with col2:
                new_amount = st.number_input(f"Amount {i+1}", value=expense['amount'], min_value=0, key=f"expense_amount_{i}")
            with col3:
                if st.button("🗑️", key=f"delete_expense_{i}", help="Delete this expense"):
                    st.session_state.onetime_expenses.pop(i)
                    st.rerun()
            
            # Update the expense
            st.session_state.onetime_expenses[i] = {
                'year': new_year, 
                'amount': new_amount, 
                'description': expense.get('description', f'Expense {i+1}')
            }
        
        # Add new expense button
        if st.button("➕ Add One-Time Expense"):
            st.session_state.onetime_expenses.append({
                'year': st.session_state.start_year + 5,
                'amount': 50_000,
                'description': f'New expense {len(st.session_state.onetime_expenses) + 1}'
            })
            st.rerun()
    
    # Real Estate Cash Flow
    st.sidebar.header("Real Estate Cash Flow")
    st.session_state.re_flow_preset = st.sidebar.selectbox(
        "Cash Flow Pattern", 
        options=['ramp', 'delayed'], 
        index=['ramp', 'delayed'].index(st.session_state.re_flow_preset),
        help="🏘️ **Real estate income pattern**\n\n**Ramp**: $50K (2026) → $60K (2027) → $75K (2028+)\n**Delayed**: $0 (2026-2030) → $50K (2031) → $60K (2032) → $75K (2033+)\n\nReal dollars, net of expenses and taxes."
    )
    
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
    
    # Regime
    st.sidebar.header("Market Regime")
    st.session_state.regime = st.sidebar.selectbox(
        "Market Scenario", 
        options=['baseline', 'recession_recover', 'grind_lower'],
        index=['baseline', 'recession_recover', 'grind_lower'].index(st.session_state.regime),
        help="📈 **Market scenario to model**\n\n**Baseline**: Use expected returns throughout\n**Recession/Recover**: -15% equity (Yr 1), 0% (Yr 2), then baseline\n**Grind Lower**: Reduced returns first 10 years, then baseline\n\nTests different economic environments."
    )
    
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
                        st.session_state.college_growth_real = params.college_growth_real
                        
                        # One-time expenses - convert from aggregated back to UI list format
                        onetime_expenses = []
                        if params.onetime_2033 > 0:
                            onetime_expenses.append({
                                'year': 2033, 
                                'amount': params.onetime_2033, 
                                'description': 'Loaded from file'
                            })
                        if params.onetime_2040 > 0:
                            onetime_expenses.append({
                                'year': 2040, 
                                'amount': params.onetime_2040, 
                                'description': 'Loaded from file'
                            })
                        st.session_state.onetime_expenses = onetime_expenses
                        
                        # Real estate
                        st.session_state.re_flow_preset = params.re_flow_preset
                        
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
    st.plotly_chart(fig, use_container_width=True)
    
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
    st.plotly_chart(fig, use_container_width=True)
    
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
        st.plotly_chart(fig, use_container_width=True)


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
    st.dataframe(df, use_container_width=True)
    
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