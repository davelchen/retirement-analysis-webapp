"""
Retirement Planning Wizard - Interactive Parameter Setup
A beautiful, step-by-step wizard to guide users through retirement planning parameters.
Part of the unified multipage Retirement Analysis Suite - seamlessly transitions to Monte Carlo analysis.

"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List
import json
from datetime import datetime
import math

# Import from main app for compatibility
from io_utils import create_parameters_download_json, convert_wizard_to_json
from simulation import SimulationParams
from ai_analysis import RetirementAnalyzer
import os

def load_ui_config():
    """Load UI configuration like API keys from ui_config.json"""
    print(f"DEBUG [load_ui_config]: CALLED - Starting UI config load from ui_config.json")
    try:
        if os.path.exists('ui_config.json'):
            print(f"DEBUG [load_ui_config]: File exists, reading...")
            with open('ui_config.json', 'r') as f:
                config = json.load(f)
            print(f"DEBUG [load_ui_config]: Successfully loaded config with {len(config)} keys")
            print(f"DEBUG [load_ui_config]: enable_ai_analysis = {config.get('enable_ai_analysis', 'MISSING')}")
            print(f"DEBUG [load_ui_config]: gemini_api_key = {config.get('gemini_api_key', 'MISSING')[:10] if config.get('gemini_api_key') else 'EMPTY'}...")
            print(f"DEBUG [load_ui_config]: gemini_model = {config.get('gemini_model', 'MISSING')}")
            return config
        else:
            print(f"DEBUG [load_ui_config]: ui_config.json does not exist")
    except Exception as e:
        print(f"ERROR [load_ui_config]: Could not load ui_config.json: {e}")
    default_config = {}
    print(f"DEBUG [load_ui_config]: Returning empty config")
    return default_config

def save_ui_config(config):
    """Save UI configuration to ui_config.json"""
    print(f"DEBUG [save_ui_config]: CALLED - Starting UI config save to ui_config.json")
    print(f"DEBUG [save_ui_config]: Config to save has {len(config)} keys:")
    print(f"DEBUG [save_ui_config]: enable_ai_analysis = {config.get('enable_ai_analysis', 'MISSING')}")
    print(f"DEBUG [save_ui_config]: gemini_api_key = {config.get('gemini_api_key', 'MISSING')[:10] if config.get('gemini_api_key') else 'EMPTY'}...")
    print(f"DEBUG [save_ui_config]: gemini_model = {config.get('gemini_model', 'MISSING')}")
    try:
        with open('ui_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        print(f"DEBUG [save_ui_config]: Successfully saved to ui_config.json")
    except Exception as e:
        print(f"ERROR [save_ui_config]: Could not save ui_config.json: {e}")

# Wizard configuration
WIZARD_STEPS = [
    {"id": "welcome", "title": "🏠 Welcome", "description": "Getting started with your retirement plan"},
    {"id": "basics", "title": "💰 Financial Basics", "description": "Current situation and spending needs"},
    {"id": "allocation", "title": "📊 Asset Allocation", "description": "Portfolio mix and risk tolerance"},
    {"id": "market", "title": "📈 Market Expectations", "description": "Return assumptions and volatility"},
    {"id": "taxes", "title": "🏛️ Tax Planning", "description": "State taxes and brackets"},
    {"id": "social_security", "title": "🏛️ Social Security", "description": "Benefit planning and scenarios"},
    {"id": "guardrails", "title": "⚖️ Spending Guardrails", "description": "Dynamic spending adjustments"},
    {"id": "cash_flows", "title": "💸 Income & Expenses", "description": "Additional cash flows over time"},
    {"id": "ai_setup", "title": "🤖 AI Analysis", "description": "Optional AI-powered insights"},
    {"id": "advanced", "title": "⚙️ Advanced Options", "description": "Market scenarios and fine-tuning"},
    {"id": "review", "title": "📋 Review & Generate", "description": "Final review and JSON export"}
]

def safe_get_wizard_param(key, default_value):
    """Safely get a wizard parameter with default fallback"""
    # Initialize state should have already run, but double-check
    if 'wizard_params' not in st.session_state:
        print(f"WARNING [safe_get_wizard_param]: wizard_params missing, returning default for {key}")
        return default_value
    return st.session_state.wizard_params.get(key, default_value)

def sync_widget_values_to_wizard_params():
    """Collect current widget values from their keys and update wizard_params"""
    if 'wizard_params' not in st.session_state:
        print(f"DEBUG [sync_widget_values]: wizard_params missing, creating empty one")
        st.session_state.wizard_params = {}

    print(f"DEBUG [sync_widget_values]: Starting sync, checking key widgets...")

    # Check if key widget values exist in session state
    key_widgets = ['wiz_horizon_years', 'wiz_start_capital', 'wiz_retirement_age', 'wiz_start_year']
    for widget_key in key_widgets:
        if widget_key in st.session_state:
            print(f"DEBUG [sync_widget_values]: Found {widget_key} = {st.session_state[widget_key]}")
        else:
            print(f"DEBUG [sync_widget_values]: MISSING {widget_key}")

    # Map widget keys to wizard_params keys
    widget_mappings = {
        # Financial Basics
        'wiz_start_capital': 'start_capital',
        'wiz_retirement_age': 'retirement_age',
        'wiz_start_year': 'start_year',
        'wiz_horizon_years': 'horizon_years',
        'wiz_spending_method': 'spending_method',
        'wiz_annual_spending': 'annual_spending',
        'wiz_cape_now': 'cape_now',

        # Asset Allocation
        'wiz_equity_pct': 'equity_pct',
        'wiz_bonds_pct': 'bonds_pct',
        'wiz_real_estate_pct': 'real_estate_pct',
        'wiz_glide_path': 'glide_path',
        'wiz_equity_reduction': 'equity_reduction_per_year',

        # Market Expectations
        'wiz_equity_return': 'equity_return',
        'wiz_bonds_return': 'bonds_return',
        'wiz_real_estate_return': 'real_estate_return',
        'wiz_cash_return': 'cash_return',
        'wiz_equity_vol': 'equity_vol',
        'wiz_bonds_vol': 'bonds_vol',
        'wiz_real_estate_vol': 'real_estate_vol',
        'wiz_inflation_rate': 'inflation_rate',

        # Tax Planning
        'wiz_selected_state': 'state',
        'wiz_filing_status': 'filing_status',
        'wiz_standard_deduction': 'standard_deduction',

        # Social Security
        'wiz_ss_primary_benefit': 'ss_primary_benefit',
        'wiz_ss_primary_start_age': 'ss_primary_start_age',
        'wiz_ss_spousal_benefit': 'ss_spousal_benefit',
        'wiz_ss_spousal_start_age': 'ss_spousal_start_age',
        'wiz_ss_funding_scenario': 'ss_funding_scenario',
        'wiz_custom_reduction': 'ss_custom_reduction',
        'wiz_reduction_start_year': 'ss_reduction_start_year',

        # Guardrails
        'wiz_lower_guardrail': 'lower_guardrail',
        'wiz_upper_guardrail': 'upper_guardrail',
        'wiz_spending_adjustment': 'spending_adjustment',
        'wiz_max_increase': 'max_spending_increase',
        'wiz_max_decrease': 'max_spending_decrease',
        'wiz_spending_floor': 'spending_floor_real',
        'wiz_spending_ceiling': 'spending_ceiling_real',
        'wiz_floor_end_year': 'floor_end_year',

        # AI Setup
        'wiz_enable_ai': 'enable_ai',
        'wiz_api_key': 'gemini_api_key',
        'wiz_selected_model': 'gemini_model',

        # Advanced Options
        'wiz_college_enabled': 'college_enabled',
        'wiz_college_amount': 'college_amount',
        'wiz_college_years': 'college_years',
        'wiz_college_start_year': 'college_start_year',
        'wiz_inheritance_amount': 'inheritance_amount',
        'wiz_inheritance_year': 'inheritance_year',
        'wiz_market_regime': 'market_regime',
        'wiz_num_simulations': 'num_simulations',
        'wiz_cape_now_final': 'cape_now',
    }

    # Sync values from widget keys to wizard_params
    synced_count = 0

    # Skip widgets that already have immediate sync to prevent overwriting
    widgets_with_immediate_sync = [
        # Financial Basics (already had immediate sync)
        'wiz_horizon_years', 'wiz_start_capital', 'wiz_retirement_age', 'wiz_start_year',
        # Financial Basics (newly added)
        'wiz_spending_method', 'wiz_annual_spending', 'wiz_cape_now',
        # Asset Allocation (newly added)
        'wiz_equity_pct', 'wiz_bonds_pct', 'wiz_real_estate_pct', 'wiz_glide_path',
        'wiz_equity_reduction',  # already had immediate sync
        # Market Expectations (newly added)
        'wiz_equity_return', 'wiz_bonds_return', 'wiz_real_estate_return', 'wiz_cash_return',
        'wiz_equity_vol', 'wiz_bonds_vol', 'wiz_real_estate_vol', 'wiz_inflation_rate',
        # AI Setup (newly added)
        'wiz_enable_ai', 'wiz_api_key', 'wiz_selected_model',
        # Tax Planning (newly added)
        'wiz_selected_state', 'wiz_filing_status', 'wiz_standard_deduction',
        # Social Security (newly added)
        'wiz_ss_primary_benefit', 'wiz_ss_primary_start_age', 'wiz_ss_spousal_benefit',
        'wiz_ss_spousal_start_age', 'wiz_ss_funding_scenario', 'wiz_custom_reduction', 'wiz_reduction_start_year',
        # Guardrails (newly added)
        'wiz_lower_guardrail', 'wiz_upper_guardrail', 'wiz_spending_adjustment',
        'wiz_max_increase', 'wiz_max_decrease', 'wiz_spending_floor', 'wiz_spending_ceiling', 'wiz_floor_end_year',
        # Advanced Options (newly added)
        'wiz_college_enabled', 'wiz_college_amount', 'wiz_college_years', 'wiz_college_start_year',
        'wiz_inheritance_amount',  # already had immediate sync
        'wiz_inheritance_year', 'wiz_market_regime',
        'wiz_num_simulations',  # already had immediate sync
        'wiz_cape_now_final'
    ]

    for widget_key, param_key in widget_mappings.items():
        if widget_key in st.session_state:
            # Skip widgets that already have immediate sync
            if widget_key in widgets_with_immediate_sync:
                print(f"DEBUG [sync_widget_values]: SKIPPING {param_key} - has immediate sync")
                continue

            value = st.session_state[widget_key]

            # Debug key values we're testing
            if param_key in ['horizon_years', 'start_capital', 'retirement_age', 'start_year']:
                print(f"DEBUG [sync_widget_values]: {param_key}: {st.session_state.wizard_params.get(param_key, 'MISSING')} -> {value}")

            # Handle percentage conversions (widgets show as 0-100, params stored as 0-1)
            if param_key in ['equity_pct', 'bonds_pct', 'real_estate_pct', 'cash_pct', 'equity_reduction_per_year',
                           'equity_return', 'bonds_return', 'real_estate_return', 'cash_return',
                           'equity_vol', 'bonds_vol', 'real_estate_vol', 'inflation_rate',
                           'lower_guardrail', 'upper_guardrail', 'spending_adjustment',
                           'max_spending_increase', 'max_spending_decrease']:
                value = value / 100.0  # Convert from percentage to decimal

            st.session_state.wizard_params[param_key] = value
            synced_count += 1

    print(f"DEBUG [sync_widget_values]: Synced {synced_count} widget values to wizard_params")

def initialize_wizard_state():
    """Initialize all wizard state variables - runs when needed"""
    # Initialize wizard_step if missing
    if 'wizard_step' not in st.session_state:
        print(f"DEBUG [initialize_wizard_state]: First-time initialization...")
        st.session_state.wizard_step = 0
        print(f"DEBUG [initialize_wizard_state]: Set wizard_step to 0")

    # Initialize wizard_params if missing (can happen independently of wizard_step)
    if 'wizard_params' not in st.session_state:
        print(f"DEBUG [initialize_wizard_state]: Creating wizard_params...")
        st.session_state.wizard_params = {
            # Financial basics
            'start_capital': 2_500_000,
            'annual_spending': 100_000,
            'retirement_age': 65,
            'start_year': 2025,
            'horizon_years': 50,

            # Asset allocation
            'equity_pct': 0.65,
            'bonds_pct': 0.25,
            'real_estate_pct': 0.08,
            'cash_pct': 0.02,
            'glide_path': True,
            'equity_reduction_per_year': 0.005,

            # Market assumptions
            'equity_return': 0.0742,
            'bonds_return': 0.0318,
            'real_estate_return': 0.0563,
            'cash_return': 0.0225,
            'equity_vol': 0.1734,
            'bonds_vol': 0.0576,
            'real_estate_vol': 0.1612,
            'cash_vol': 0.0096,
            'inflation_rate': 0.025,

            # Taxes
            'state': 'CA',
            'filing_status': 'MFJ',
            'standard_deduction': 29200,

            # Social Security
            'ss_primary_benefit': 40000,
            'ss_primary_start_age': 67,
            'ss_spousal_benefit': 0,
            'ss_spousal_start_age': 67,
            'ss_funding_scenario': 'moderate',

            # Guardrails
            'lower_guardrail': 0.03,
            'upper_guardrail': 0.05,
            'spending_adjustment': 0.10,
            'max_spending_increase': 0.10,
            'max_spending_decrease': 0.10,

            # Cash flows
            'income_streams': [],
            'expense_streams': [],

            # AI setup - will be loaded from config below
            'enable_ai': False,
            'gemini_api_key': '',
            'gemini_model': 'gemini-2.5-pro',

            # Advanced
            'market_regime': 'baseline',
            'num_simulations': 10000,
            'cape_now': 28.0
        }

        # ONLY load UI config when creating wizard_params for first time
        print(f"DEBUG [initialize_wizard_state]: Loading UI config for first time wizard_params creation...")
        ui_config = load_ui_config()
        print(f"DEBUG [initialize_wizard_state]: UI config loaded, has {len(ui_config)} keys")
        if ui_config:
            # Set AI settings from saved config
            api_key = ui_config.get('gemini_api_key', '')
            enable_ai = ui_config.get('enable_ai_analysis', False)
            model = ui_config.get('gemini_model', 'gemini-2.5-pro')

            print(f"DEBUG [initialize_wizard_state]: WRITING to wizard_params from ui_config.json:")
            print(f"DEBUG [initialize_wizard_state]: enable_ai: {enable_ai} -> wizard_params['enable_ai']")
            print(f"DEBUG [initialize_wizard_state]: api_key: {api_key[:10] if api_key else 'EMPTY'}... -> wizard_params['gemini_api_key']")
            print(f"DEBUG [initialize_wizard_state]: model: {model} -> wizard_params['gemini_model']")

            st.session_state.wizard_params['enable_ai'] = enable_ai
            st.session_state.wizard_params['gemini_api_key'] = api_key
            st.session_state.wizard_params['gemini_model'] = model

            print(f"DEBUG [initialize_wizard_state]: AFTER WRITING - wizard_params AI values:")
            print(f"DEBUG [initialize_wizard_state]: wizard_params['enable_ai'] = {st.session_state.wizard_params.get('enable_ai', 'MISSING')}")
            print(f"DEBUG [initialize_wizard_state]: wizard_params['gemini_api_key'] = {st.session_state.wizard_params.get('gemini_api_key', 'MISSING')[:10] if st.session_state.wizard_params.get('gemini_api_key') else 'EMPTY'}...")
            print(f"DEBUG [initialize_wizard_state]: wizard_params['gemini_model'] = {st.session_state.wizard_params.get('gemini_model', 'MISSING')}")
        else:
            print(f"DEBUG [initialize_wizard_state]: No UI config loaded, keeping default AI values in wizard_params")
            print(f"DEBUG [initialize_wizard_state]: Default wizard_params AI values:")
            print(f"DEBUG [initialize_wizard_state]: wizard_params['enable_ai'] = {st.session_state.wizard_params.get('enable_ai', 'MISSING')}")
            print(f"DEBUG [initialize_wizard_state]: wizard_params['gemini_api_key'] = {st.session_state.wizard_params.get('gemini_api_key', 'MISSING')[:10] if st.session_state.wizard_params.get('gemini_api_key') else 'EMPTY'}...")
            print(f"DEBUG [initialize_wizard_state]: wizard_params['gemini_model'] = {st.session_state.wizard_params.get('gemini_model', 'MISSING')}")

def create_progress_bar():
    """Create a beautiful progress bar"""
    current_step = st.session_state.wizard_step
    total_steps = len(WIZARD_STEPS)
    progress = (current_step + 1) / total_steps

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.progress(progress)
        st.caption(f"Step {current_step + 1} of {total_steps}: {WIZARD_STEPS[current_step]['title']}")

def create_navigation_buttons():
    """Create navigation buttons"""
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.session_state.wizard_step > 0:
            if st.button("← Previous"):
                st.session_state.wizard_step -= 1
                st.rerun()

    with col3:
        if st.session_state.wizard_step < len(WIZARD_STEPS) - 1:
            if st.button("Next →"):
                st.session_state.wizard_step += 1
                st.rerun()

def create_allocation_pie_chart(equity, bonds, real_estate, cash):
    """Create an interactive allocation pie chart"""
    labels = ['Stocks/Equity', 'Bonds', 'Real Estate', 'Cash']
    values = [equity * 100, bonds * 100, real_estate * 100, cash * 100]
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors,
        textinfo='label+percent',
        textposition='outside'
    )])

    fig.update_layout(
        title="Your Portfolio Allocation",
        font=dict(size=14),
        height=400,
        showlegend=False
    )

    return fig

def create_risk_return_scatter():
    """Create risk vs return visualization"""
    assets = ['Cash', 'Bonds', 'Real Estate', 'Stocks']
    returns = [2.25, 3.18, 5.63, 7.42]
    risks = [0.96, 5.76, 16.12, 17.34]
    colors = ['#96CEB4', '#4ECDC4', '#45B7D1', '#FF6B6B']

    fig = go.Figure()

    for i, asset in enumerate(assets):
        fig.add_trace(go.Scatter(
            x=[risks[i]],
            y=[returns[i]],
            mode='markers+text',
            marker=dict(size=20, color=colors[i]),
            text=asset,
            textposition="top center",
            name=asset,
            showlegend=False
        ))

    fig.update_layout(
        title="Asset Classes: Risk vs Expected Return",
        xaxis_title="Volatility (Risk) %",
        yaxis_title="Expected Return %",
        height=400,
        template="plotly_white"
    )

    return fig

def step_welcome():
    """Welcome step"""
    st.markdown("""
    # 🌟 Welcome to Your Retirement Planning Wizard

    This interactive wizard will guide you through setting up a comprehensive retirement analysis.
    We'll cover everything from your current finances to advanced market scenarios.

    ## What You'll Configure:

    - 💰 **Financial Basics** - Your starting point and spending needs
    - 📊 **Asset Allocation** - How to invest your portfolio
    - 📈 **Market Expectations** - Return and risk assumptions
    - 🏛️ **Tax Planning** - State taxes and optimization
    - 🏛️ **Social Security** - Benefit planning and timing
    - ⚖️ **Spending Rules** - Dynamic adjustments over time
    - 💸 **Cash Flows** - Income streams and major expenses
    - 🤖 **AI Analysis** - Optional AI-powered insights
    - ⚙️ **Advanced Options** - Market scenarios and fine-tuning

    At the end, you'll get a complete parameter file to run your Monte Carlo simulation!

    ## 🎯 Take Your Time
    Each step includes educational content, examples, and interactive visualizations
    to help you make informed decisions about your retirement planning.
    """)

    # JSON Parameter Loading Section
    st.markdown("---")
    st.markdown("### 📂 Pick Up Where You Left Off")

    # Initialize state flag to manage the button flow
    if 'params_loaded_and_waiting_for_choice' not in st.session_state:
        st.session_state.params_loaded_and_waiting_for_choice = False

    with st.expander("Load Previous Session Parameters", expanded=False):
        st.markdown("""
        Already have a saved configuration? Upload your JSON parameter file to continue
        where you left off instead of starting from scratch.

        **Compatible with:**
        - Wizard session exports (from this wizard)
        - Monte Carlo parameter files
        - Default configuration files
        """)

        uploaded_file = st.file_uploader(
            "Choose JSON parameter file",
            type="json",
            help="Upload a previously saved parameter file to load your configuration",
            key="wizard_json_upload"
        )

        if uploaded_file is not None:
            try:
                # Read the uploaded file
                json_data = json.loads(uploaded_file.read())

                col1, col2 = st.columns([3, 1])

                with col1:
                    # Show preview of loaded parameters
                    st.success(f"✅ Loaded configuration with {len(json_data)} parameter sections")

                    # Show key parameters preview
                    if 'basic_params' in json_data:
                        basic = json_data['basic_params']
                        capital = basic.get('start_capital', 'N/A')
                        spending = basic.get('annual_spending', 'N/A')
                        horizon = basic.get('horizon_years', 'N/A')

                        st.write(f"**Starting Capital:** ${capital:,.0f}" if isinstance(capital, (int, float)) else f"**Starting Capital:** {capital}")
                        st.write(f"**Annual Spending:** ${spending:,.0f}" if isinstance(spending, (int, float)) else f"**Annual Spending:** {spending}")
                        st.write(f"**Horizon:** {horizon} years")
                    elif 'start_capital' in json_data:
                        # Handle flat parameter format
                        capital = json_data.get('start_capital', 'N/A')
                        spending = json_data.get('annual_spending', 'N/A')
                        horizon = json_data.get('horizon_years', 'N/A')

                        st.write(f"**Starting Capital:** ${capital:,.0f}" if isinstance(capital, (int, float)) else f"**Starting Capital:** {capital}")
                        st.write(f"**Annual Spending:** ${spending:,.0f}" if isinstance(spending, (int, float)) else f"**Annual Spending:** {spending}")
                        st.write(f"**Horizon:** {horizon} years")

                with col2:
                    # STATE 2: Params are loaded, show the choice buttons
                    if st.session_state.params_loaded_and_waiting_for_choice:
                        if st.button("🧙‍♂️ Review in Wizard", key="review_in_wizard"):
                            st.session_state.params_loaded_and_waiting_for_choice = False  # Reset flag
                            st.session_state.wizard_step = 1  # Move to step 1
                            st.rerun()

                        if st.button("🚀 Jump to Simulation", type="primary", key="jump_to_simulation"):
                            st.session_state.params_loaded_and_waiting_for_choice = False  # Reset flag
                            st.session_state.jump_to_sim_requested = True
                            st.rerun()

                    # STATE 1: File is present, show the initial "Load" button
                    else:
                        if st.button("Load These Parameters", type="primary", key="load_json_params"):
                            # Convert JSON to wizard parameters and load into session state
                            try:
                                # Check if it's wizard format or flat format
                                if 'basic_params' in json_data:
                                    # It's wizard format, convert back to wizard params
                                    wizard_params = convert_json_to_wizard_params(json_data)
                                else:
                                    # It's flat format, convert to wizard params
                                    wizard_params = convert_flat_to_wizard_params(json_data)

                                # Load into session state, but preserve existing AI config
                                print(f"DEBUG [JSON loading]: About to load wizard params, preserving AI config...")

                                # Mark that JSON loading is complete to prevent repeated widget key updates
                                st.session_state.json_loading_complete = True

                                # Preserve current AI configuration before overwriting
                                current_ai_config = {
                                    'enable_ai': st.session_state.wizard_params.get('enable_ai', False),
                                    'gemini_api_key': st.session_state.wizard_params.get('gemini_api_key', ''),
                                    'gemini_model': st.session_state.wizard_params.get('gemini_model', 'gemini-2.5-pro')
                                }
                                print(f"DEBUG [JSON loading]: PRESERVING current AI config before overwrite:")
                                print(f"DEBUG [JSON loading]: Current enable_ai: {current_ai_config['enable_ai']}")
                                print(f"DEBUG [JSON loading]: Current api_key: {current_ai_config['gemini_api_key'][:10] if current_ai_config['gemini_api_key'] else 'EMPTY'}...")
                                print(f"DEBUG [JSON loading]: Current model: {current_ai_config['gemini_model']}")

                                # Overwrite wizard params with loaded data
                                print(f"DEBUG [JSON loading]: OVERWRITING wizard_params with loaded JSON data...")
                                st.session_state.wizard_params = wizard_params

                                # ALWAYS use ui_config.json for AI settings, ignore JSON file AI config
                                print(f"DEBUG [JSON loading]: Loading current ui_config.json to override any AI config from JSON file...")
                                current_ui_config = load_ui_config()
                                if current_ui_config:
                                    print(f"DEBUG [JSON loading]: OVERRIDING JSON AI config with ui_config.json:")
                                    print(f"DEBUG [JSON loading]: ui_config enable_ai: {current_ui_config.get('enable_ai_analysis', False)} -> wizard_params['enable_ai']")
                                    print(f"DEBUG [JSON loading]: ui_config api_key: {current_ui_config.get('gemini_api_key', '')[:10] if current_ui_config.get('gemini_api_key') else 'EMPTY'}... -> wizard_params['gemini_api_key']")
                                    print(f"DEBUG [JSON loading]: ui_config model: {current_ui_config.get('gemini_model', 'gemini-2.5-pro')} -> wizard_params['gemini_model']")

                                    st.session_state.wizard_params['enable_ai'] = current_ui_config.get('enable_ai_analysis', False)
                                    st.session_state.wizard_params['gemini_api_key'] = current_ui_config.get('gemini_api_key', '')
                                    st.session_state.wizard_params['gemini_model'] = current_ui_config.get('gemini_model', 'gemini-2.5-pro')
                                    print(f"DEBUG [JSON loading]: AI config set from ui_config.json (ignoring JSON file AI values)")
                                else:
                                    print(f"DEBUG [JSON loading]: No ui_config.json found, using preserved AI config:")
                                    print(f"DEBUG [JSON loading]: Restoring enable_ai: {current_ai_config['enable_ai']} -> wizard_params['enable_ai']")
                                    print(f"DEBUG [JSON loading]: Restoring api_key: {current_ai_config['gemini_api_key'][:10] if current_ai_config['gemini_api_key'] else 'EMPTY'}... -> wizard_params['gemini_api_key']")
                                    print(f"DEBUG [JSON loading]: Restoring model: {current_ai_config['gemini_model']} -> wizard_params['gemini_model']")
                                    st.session_state.wizard_params.update(current_ai_config)

                                print(f"DEBUG [JSON loading]: FINAL wizard_params AI values:")
                                print(f"DEBUG [JSON loading]: Final enable_ai: {st.session_state.wizard_params.get('enable_ai', 'MISSING')}")
                                print(f"DEBUG [JSON loading]: Final api_key: {st.session_state.wizard_params.get('gemini_api_key', 'MISSING')[:10] if st.session_state.wizard_params.get('gemini_api_key') else 'EMPTY'}...")
                                print(f"DEBUG [JSON loading]: Final model: {st.session_state.wizard_params.get('gemini_model', 'MISSING')}")

                                # Also set widget keys directly to avoid circular state references
                                # This ensures widgets show loaded values immediately
                                widget_key_mappings = {
                                    # Financial Basics
                                    'start_capital': 'wiz_start_capital',
                                    'retirement_age': 'wiz_retirement_age',
                                    'start_year': 'wiz_start_year',
                                    'horizon_years': 'wiz_horizon_years',
                                    'spending_method': 'wiz_spending_method',
                                    'annual_spending': 'wiz_annual_spending',
                                    'cape_now': 'wiz_cape_now',

                                    # Asset Allocation (percentages will be converted)
                                    'equity_pct': 'wiz_equity_pct',
                                    'bonds_pct': 'wiz_bonds_pct',
                                    'real_estate_pct': 'wiz_real_estate_pct',
                                    'glide_path': 'wiz_glide_path',
                                    'equity_reduction_per_year': 'wiz_equity_reduction',

                                    # Market Assumptions (percentages will be converted)
                                    'equity_return': 'wiz_equity_return',
                                    'bonds_return': 'wiz_bonds_return',
                                    'real_estate_return': 'wiz_real_estate_return',
                                    'cash_return': 'wiz_cash_return',
                                    'equity_vol': 'wiz_equity_vol',
                                    'bonds_vol': 'wiz_bonds_vol',
                                    'real_estate_vol': 'wiz_real_estate_vol',
                                    'inflation_rate': 'wiz_inflation_rate',

                                    # Tax Planning
                                    'state': 'wiz_selected_state',
                                    'filing_status': 'wiz_filing_status',
                                    'standard_deduction': 'wiz_standard_deduction',

                                    # Social Security
                                    'ss_primary_benefit': 'wiz_ss_primary_benefit',
                                    'ss_primary_start_age': 'wiz_ss_primary_start_age',
                                    'ss_spousal_benefit': 'wiz_ss_spousal_benefit',
                                    'ss_spousal_start_age': 'wiz_ss_spousal_start_age',
                                    'ss_funding_scenario': 'wiz_ss_funding_scenario',
                                    'ss_custom_reduction': 'wiz_custom_reduction',
                                    'ss_reduction_start_year': 'wiz_reduction_start_year',

                                    # Guardrails (percentages will be converted)
                                    'lower_guardrail': 'wiz_lower_guardrail',
                                    'upper_guardrail': 'wiz_upper_guardrail',
                                    'spending_adjustment': 'wiz_spending_adjustment',
                                    'max_spending_increase': 'wiz_max_increase',
                                    'max_spending_decrease': 'wiz_max_decrease',
                                    'spending_floor_real': 'wiz_spending_floor',
                                    'spending_ceiling_real': 'wiz_spending_ceiling',
                                    'floor_end_year': 'wiz_floor_end_year',

                                    # AI Setup
                                    'enable_ai': 'wiz_enable_ai',
                                    'gemini_api_key': 'wiz_api_key',
                                    'gemini_model': 'wiz_selected_model',

                                    # Advanced Options
                                    'college_enabled': 'wiz_college_enabled',
                                    'college_amount': 'wiz_college_amount',
                                    'college_years': 'wiz_college_years',
                                    'college_start_year': 'wiz_college_start_year',
                                    'inheritance_amount': 'wiz_inheritance_amount',
                                    'inheritance_year': 'wiz_inheritance_year',
                                    'market_regime': 'wiz_market_regime',
                                    'num_simulations': 'wiz_num_simulations',
                                    'cape_now_final': 'wiz_cape_now_final',
                                }

                                # Only set widget keys immediately after JSON loading, not on every rerun
                                if not st.session_state.get('json_widget_keys_set', False):
                                    print(f"DEBUG [JSON loading]: Setting widget keys for the FIRST TIME after JSON load...")

                                    # Clear any existing widget keys first to prevent old values from persisting
                                    for param_key, widget_key in widget_key_mappings.items():
                                        if widget_key in st.session_state:
                                            print(f"DEBUG [JSON loading]: Clearing old {widget_key} = {st.session_state[widget_key]}")
                                            del st.session_state[widget_key]

                                    # Set new values from loaded JSON
                                    percentage_params = ['equity_pct', 'bonds_pct', 'real_estate_pct', 'cash_pct', 'equity_reduction_per_year',
                                                       'equity_return', 'bonds_return', 'real_estate_return', 'cash_return',
                                                       'equity_vol', 'bonds_vol', 'real_estate_vol', 'inflation_rate',
                                                       'lower_guardrail', 'upper_guardrail', 'spending_adjustment',
                                                       'max_spending_increase', 'max_spending_decrease']

                                    for param_key, widget_key in widget_key_mappings.items():
                                        if param_key in wizard_params:
                                            value = wizard_params[param_key]

                                            # For AI settings, use the corrected values from wizard_params (which now has ui_config.json values)
                                            if param_key in ['enable_ai', 'gemini_api_key', 'gemini_model']:
                                                # Use the updated wizard_params value (from ui_config.json)
                                                value = st.session_state.wizard_params[param_key]
                                                print(f"DEBUG [JSON loading]: Set {widget_key} = {value} (from ui_config.json, not JSON file)")
                                            # Convert decimal to percentage for widget display
                                            elif param_key in percentage_params:
                                                value = value * 100.0
                                                print(f"DEBUG [JSON loading]: Set {widget_key} = {value}% (converted from {wizard_params[param_key]})")
                                            else:
                                                print(f"DEBUG [JSON loading]: Set {widget_key} = {value}")

                                            st.session_state[widget_key] = value

                                    print(f"DEBUG [JSON loading]: Updated {len(widget_key_mappings)} widget keys from loaded data")

                                    # Mark that widget keys have been set to prevent doing this again
                                    st.session_state.json_widget_keys_set = True
                                    print(f"DEBUG [JSON loading]: Marked json_widget_keys_set = True to prevent future resets")
                                else:
                                    print(f"DEBUG [JSON loading]: SKIPPING widget key setting - already done (json_widget_keys_set = True)")

                                # Set flag to show choice buttons on next rerun
                                st.session_state.params_loaded_and_waiting_for_choice = True

                                # Set flag to indicate we just loaded JSON (so we don't reset widget keys on every rerun)
                                st.session_state.json_just_loaded = True

                                st.success("✅ Parameters loaded successfully!")
                                st.rerun()

                            except Exception as e:
                                st.error(f"Error loading parameters: {str(e)}")

            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid parameter file.")
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

    st.markdown("---")

    # Add a sample visualization
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 📊 What We'll Build Together
        A complete picture of your retirement plan with:
        - Monte Carlo simulation (thousands of scenarios)
        - Tax-aware withdrawal strategies
        - Dynamic spending adjustments
        - Social Security optimization
        """)

    with col2:
        # Create sample wealth trajectory
        years = np.arange(2025, 2075)
        np.random.seed(42)

        # Generate sample paths
        paths = []
        for i in range(5):
            returns = np.random.normal(0.06, 0.12, len(years))
            wealth = [2_500_000]
            for r in returns[:-1]:
                wealth.append(wealth[-1] * (1 + r) - 100_000)
            paths.append(wealth)

        fig = go.Figure()
        colors = ['rgba(255,107,107,0.3)', 'rgba(78,205,196,0.3)', 'rgba(69,183,209,0.3)',
                 'rgba(150,206,180,0.3)', 'rgba(255,193,7,0.3)']

        for i, path in enumerate(paths):
            fig.add_trace(go.Scatter(
                x=years, y=path,
                mode='lines',
                line=dict(color=colors[i], width=1),
                showlegend=False,
                hovertemplate='Year: %{x}<br>Wealth: $%{y:,.0f}<extra></extra>'
            ))

        fig.update_layout(
            title="Sample Retirement Wealth Paths",
            xaxis_title="Year",
            yaxis_title="Portfolio Value",
            height=300,
            template="plotly_white",
            yaxis=dict(tickformat='$,.0s')
        )

        st.plotly_chart(fig)

def step_basics():
    """Financial basics step"""
    st.markdown("""
    # 💰 Financial Basics

    Let's start with your current financial situation and retirement goals.
    These are the foundation of your retirement plan.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🏦 Your Starting Point")

        start_capital = st.number_input(
            "Current Portfolio Value",
            min_value=0,
            value=int(st.session_state.wizard_params.get('start_capital', 2_500_000)),  # Keep for JSON loading
            step=50000,
            format="%d",
            help="Total value of your investment accounts (401k, IRA, taxable accounts, etc.)",
            key="wiz_start_capital"
        )

        # Immediately sync change back to wizard_params to keep them in sync
        if start_capital != st.session_state.wizard_params.get('start_capital'):
            st.session_state.wizard_params['start_capital'] = start_capital

        retirement_age = st.slider(
            "Retirement Age",
            min_value=30,
            max_value=75,
            value=st.session_state.wizard_params.get('retirement_age', 65),  # Keep for JSON loading
            help="Age when you plan to retire and start drawing from your portfolio. FIRE (Financial Independence, Retire Early) movement targets 30-50.",
            key="wiz_retirement_age"
        )

        # Immediately sync change back to wizard_params to keep them in sync
        if retirement_age != st.session_state.wizard_params.get('retirement_age'):
            st.session_state.wizard_params['retirement_age'] = retirement_age

        start_year = st.number_input(
            "Retirement Year",
            min_value=2024,
            max_value=2040,
            value=st.session_state.wizard_params.get('start_year', 2025),  # Keep for JSON loading
            help="Year you plan to start retirement",
            key="wiz_start_year"
        )

        # Immediately sync change back to wizard_params to keep them in sync
        if start_year != st.session_state.wizard_params.get('start_year'):
            st.session_state.wizard_params['start_year'] = start_year

        # Debug: Check widget key value before rendering
        widget_key_value = st.session_state.get('wiz_horizon_years', 'NOT_SET')
        wizard_params_value = st.session_state.wizard_params.get('horizon_years', 'NOT_SET')
        value_param_will_use = st.session_state.wizard_params.get('horizon_years', 50)
        print(f"DEBUG [horizon_years widget]: Before render - widget_key: {widget_key_value}, wizard_params: {wizard_params_value}, value_param: {value_param_will_use}")

        horizon_years = st.slider(
            "Planning Horizon (Years)",
            min_value=20,
            max_value=60,
            value=st.session_state.wizard_params.get('horizon_years', 50),  # Use wizard_params as source of truth
            help="How many years to plan for in retirement",
            key="wiz_horizon_years"
        )

        print(f"DEBUG [horizon_years widget]: After render - slider returned: {horizon_years}")

        # Immediately sync widget change back to wizard_params to keep them in sync
        if horizon_years != st.session_state.wizard_params.get('horizon_years'):
            st.session_state.wizard_params['horizon_years'] = horizon_years
            print(f"DEBUG [horizon_years widget]: Synced change to wizard_params: {horizon_years}")

        # Age-aware horizon validation
        current_retirement_age = st.session_state.wizard_params.get('retirement_age', 65)
        current_horizon = st.session_state.wizard_params.get('horizon_years', 50)
        end_age = current_retirement_age + current_horizon

        # Warning for young people with short horizons
        if current_retirement_age < 50 and current_horizon < 40:
            st.warning(
                f"⚠️ **Planning Horizon Recommendation**: You're planning to retire at {current_retirement_age} "
                f"with only {current_horizon} years of retirement funding. Consider extending your horizon to 40-50 years "
                f"to account for longer life expectancy and inflation over time."
            )

        # Longevity risk warning for everyone if end age < 80
        elif end_age < 80:
            years_to_80 = 80 - current_retirement_age
            st.info(
                f"💡 **Longevity Planning**: Your current plan covers until age {end_age}. "
                f"Consider extending to at least {years_to_80} years (age 80) to manage longevity risk, "
                f"as many people live well beyond their initial retirement planning assumptions."
            )

        # Positive confirmation for good planning
        elif end_age >= 90:
            st.success(
                f"✅ **Excellent Longevity Planning**: Your {current_horizon}-year horizon covers until age {end_age}, "
                f"providing strong protection against longevity risk."
            )

    with col2:
        st.markdown("### 💸 Annual Spending Needs")

        # Initialize spending method if not set
        if 'spending_method' not in st.session_state.wizard_params:
            st.session_state.wizard_params['spending_method'] = 'fixed'
        if 'cape_now' not in st.session_state.wizard_params:
            st.session_state.wizard_params['cape_now'] = 28.0

        spending_method = st.radio(
            "How to set spending?",
            options=['fixed', 'cape'],
            format_func=lambda x: "💰 Fixed amount every year" if x == 'fixed' else "📊 CAPE-based with guardrails",
            index=0 if st.session_state.wizard_params['spending_method'] == 'fixed' else 1,
            help="Choose your approach:\n• Fixed: Same amount every year (no adjustments)\n• CAPE: Market valuation-based calculation with dynamic guardrails\n\nCAPE = Cyclically Adjusted P/E Ratio (measures market expensiveness)",
            key="wiz_spending_method"
        )
        # Immediately sync change back to wizard_params
        if spending_method != st.session_state.wizard_params.get('spending_method'):
            st.session_state.wizard_params['spending_method'] = spending_method

        if spending_method == 'fixed':
            annual_spending = st.number_input(
                "Annual Spending in Retirement",
                min_value=0,
                value=int(st.session_state.wizard_params.get('annual_spending', 100_000)),
                step=5000,
                format="%d",
                help="How much you plan to spend each year in retirement (today's dollars)",
                key="wiz_annual_spending"
            )
            # Immediately sync change back to wizard_params
            if annual_spending != st.session_state.wizard_params.get('annual_spending'):
                st.session_state.wizard_params['annual_spending'] = annual_spending
        else:
            # CAPE-based spending
            st.markdown("**🔧 CAPE Parameters**")
            cape_now = st.slider(
                "Current CAPE Ratio",
                min_value=15.0,
                max_value=45.0,
                value=st.session_state.wizard_params.get('cape_now', 28.0),
                step=1.0,
                help="📊 **CAPE = Cyclically Adjusted P/E Ratio** (Market Valuation)\n\n"
                     "What it is: Stock market 'expensiveness' smoothed over 10 years\n"
                     "• Low CAPE (15-20): Stocks cheap → Higher safe withdrawal rates\n"
                     "• High CAPE (30-40): Stocks expensive → Lower safe withdrawal rates\n\n"
                     "How we use it: Sets your initial withdrawal rate\n"
                     "Formula: Base 3.2% + 0.5 × (1/CAPE)\n"
                     "• Low CAPE = Higher bonus (cheap stocks = higher safe rate)\n"
                     "• High CAPE = Lower bonus (expensive stocks = lower safe rate)\n\n"
                     "Current market: ~28-35 (check Robert Shiller's data)\n"
                     "Historical range: 5 (1920s) to 45+ (dot-com bubble)",
                key="wiz_cape_now"
            )
            # Immediately sync change back to wizard_params
            if cape_now != st.session_state.wizard_params.get('cape_now'):
                st.session_state.wizard_params['cape_now'] = cape_now

            # Calculate CAPE-based spending
            cape_withdrawal_rate = (3.2 + 0.5 * (1.0 / cape_now)) / 100
            annual_spending = cape_withdrawal_rate * start_capital
            st.session_state.wizard_params['annual_spending'] = annual_spending

            # Show the calculation
            st.info(
                f"📊 **CAPE Calculation:**\n"
                f"• Withdrawal Rate: {cape_withdrawal_rate:.2%}\n"
                f"• Annual Spending: ${annual_spending:,.0f}\n"
                f"• Formula: 3.2% + 0.5 × (1/{cape_now})\n"
                f"• Logic: Higher CAPE (expensive markets) = lower bonus rate"
            )

        # Calculate and display key metrics
        st.markdown("### 📊 Key Metrics")

        withdrawal_rate = (annual_spending / start_capital) * 100 if start_capital > 0 else 0
        years_to_retirement = start_year - 2025
        retirement_duration = f"{retirement_age} to {retirement_age + horizon_years}"

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Initial Withdrawal Rate", f"{withdrawal_rate:.1f}%")
            st.metric("Years to Retirement", f"{years_to_retirement}")
        with col_b:
            st.metric("Retirement Duration", retirement_duration)
            st.metric("Total Spending (Nominal)", f"${annual_spending * horizon_years:,}")

        # Guidelines based on retirement age and withdrawal rate
        if retirement_age <= 40:
            # Early retirement (FIRE) guidelines
            if withdrawal_rate > 4:
                st.warning("⚠️ Early retirement typically requires withdrawal rates ≤ 3.5%")
            elif withdrawal_rate > 3:
                st.info("ℹ️ For retirement in 30s-40s, consider reducing to ≤ 3%")
            else:
                st.success("✅ Great withdrawal rate for early retirement!")
        elif retirement_age <= 55:
            # Traditional early retirement
            if withdrawal_rate > 5:
                st.warning("⚠️ Withdrawal rate above 5% may be aggressive")
            elif withdrawal_rate > 4:
                st.info("ℹ️ Withdrawal rate above 4% requires careful planning")
            else:
                st.success("✅ Conservative withdrawal rate")
        else:
            # Traditional retirement with Social Security
            if withdrawal_rate > 6:
                st.warning("⚠️ Very high withdrawal rate, even with Social Security")
            elif withdrawal_rate > 4.5:
                st.info("ℹ️ Moderate rate - Social Security will help reduce portfolio withdrawals")
            else:
                st.success("✅ Conservative rate, Social Security provides additional support")

    # Add educational content
    with st.expander("📚 Learn More About These Parameters"):
        st.markdown("""
        **Portfolio Value**: Include all retirement accounts (401k, IRA, Roth IRA, taxable brokerage).
        Don't include home equity unless you plan to downsize.

        **Annual Spending**: Think about your current spending and how it might change:
        - Housing costs (mortgage paid off?)
        - Healthcare (typically increases with age)
        - Travel and hobbies (might increase early, decrease later)
        - General expenses (often 70-80% of pre-retirement)

        **Withdrawal Rate**: The percentage of your portfolio you spend each year.
        - 2.5-3%: Ultra-conservative, supports very early retirement (30-40s)
        - 3-4%: Conservative, traditional retirement planning
        - 4-5%: Moderate, requires good planning and flexibility
        - 5%+: Aggressive, consider reducing spending or working longer

        **Early Retirement (FIRE Movement)**:
        - 30-40: Requires 25-33x annual expenses saved
        - 45-55: More traditional early retirement
        - 65+: Standard retirement with Social Security benefits
        """)

def step_allocation():
    """Asset allocation step with interactive visuals"""
    st.markdown("""
    # 📊 Asset Allocation

    How should your retirement portfolio be invested? This is one of the most important decisions
    for your long-term success. Let's build your ideal allocation.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🎯 Choose Your Mix")

        # Asset allocation sliders
        equity_pct = st.slider(
            "Stocks/Equity (%)",
            min_value=0,
            max_value=100,
            value=int(st.session_state.wizard_params.get('equity_pct', 0.65) * 100),
            step=5,
            help="Stocks provide growth but with higher volatility",
            key="wiz_equity_pct"
        ) / 100

        bonds_pct = st.slider(
            "Bonds (%)",
            min_value=0,
            max_value=100 - int(equity_pct * 100),
            value=min(int(st.session_state.wizard_params.get('bonds_pct', 0.25) * 100), 100 - int(equity_pct * 100)),
            step=5,
            help="Bonds provide stability and income with lower volatility",
            key="wiz_bonds_pct"
        ) / 100

        remaining = 100 - int((equity_pct + bonds_pct) * 100)

        real_estate_pct = st.slider(
            "Real Estate/REITs (%)",
            min_value=0,
            max_value=remaining,
            value=min(int(st.session_state.wizard_params.get('real_estate_pct', 0.08) * 100), remaining),
            step=2,
            help="REITs provide diversification and inflation protection",
            key="wiz_real_estate_pct"
        ) / 100

        cash_remaining = remaining - int(real_estate_pct * 100)
        cash_pct = cash_remaining / 100

        st.info(f"Cash/Money Market: {cash_pct:.1%} (auto-calculated)")

        # Calculate cash percentage
        cash_pct = max(0, 1.0 - equity_pct - bonds_pct - real_estate_pct)

        # Immediately sync changes back to wizard_params
        if equity_pct != st.session_state.wizard_params.get('equity_pct'):
            st.session_state.wizard_params['equity_pct'] = equity_pct
        if bonds_pct != st.session_state.wizard_params.get('bonds_pct'):
            st.session_state.wizard_params['bonds_pct'] = bonds_pct
        if real_estate_pct != st.session_state.wizard_params.get('real_estate_pct'):
            st.session_state.wizard_params['real_estate_pct'] = real_estate_pct
        if cash_pct != st.session_state.wizard_params.get('cash_pct'):
            st.session_state.wizard_params['cash_pct'] = cash_pct

        # Glide path option
        st.markdown("### 📉 Age-Based Adjustment")

        glide_path = st.checkbox(
            "Enable Glide Path (Reduce Risk Over Time)",
            value=st.session_state.wizard_params.get('glide_path', True),
            help="Automatically reduce stock allocation as you age",
            key="wiz_glide_path"
        )
        # Immediately sync change back to wizard_params
        if glide_path != st.session_state.wizard_params.get('glide_path'):
            st.session_state.wizard_params['glide_path'] = glide_path

        if glide_path:
            equity_reduction_pct = st.slider(
                "Annual Equity Reduction (%)",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.wizard_params.get('equity_reduction_per_year', 0.005) * 100,
                step=0.1,
                help="How much to reduce equity allocation each year",
                key="wiz_equity_reduction"
            )

            # Convert to decimal and immediately sync back to wizard_params
            equity_reduction = equity_reduction_pct / 100
            if equity_reduction != st.session_state.wizard_params.get('equity_reduction_per_year'):
                st.session_state.wizard_params['equity_reduction_per_year'] = equity_reduction
                print(f"DEBUG [equity_reduction widget]: Synced change to wizard_params: {equity_reduction}")

    with col2:
        st.markdown("### 📈 Your Portfolio Visualization")

        # Create and display pie chart
        fig_pie = create_allocation_pie_chart(equity_pct, bonds_pct, real_estate_pct, cash_pct)
        st.plotly_chart(fig_pie)

        # Risk/return characteristics
        st.markdown("### ⚡ Risk & Return Profile")

        # Calculate portfolio metrics
        returns = [0.0742, 0.0318, 0.0563, 0.0225]  # Equity, bonds, RE, cash
        vols = [0.1734, 0.0576, 0.1612, 0.0096]
        weights = [equity_pct, bonds_pct, real_estate_pct, cash_pct]

        portfolio_return = sum(w * r for w, r in zip(weights, returns))
        portfolio_vol = math.sqrt(sum((w * v) ** 2 for w, v in zip(weights, vols)))

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Expected Return", f"{portfolio_return:.1%}")
            st.metric("Portfolio Risk", f"{portfolio_vol:.1%}")
        with col_b:
            # Risk tolerance gauge
            if portfolio_vol > 0.15:
                risk_level = "🔴 Aggressive"
            elif portfolio_vol > 0.10:
                risk_level = "🟡 Moderate"
            else:
                risk_level = "🟢 Conservative"

            st.metric("Risk Level", risk_level)

            # Diversification score
            diversity = 1 - sum(w**2 for w in weights)
            st.metric("Diversification", f"{diversity:.1%}")

    # Risk vs Return scatter plot
    st.markdown("### 📊 Asset Classes: Risk vs Return")
    fig_scatter = create_risk_return_scatter()

    # Add portfolio point
    fig_scatter.add_trace(go.Scatter(
        x=[portfolio_vol * 100],
        y=[portfolio_return * 100],
        mode='markers+text',
        marker=dict(size=25, color='gold', symbol='star', line=dict(width=2, color='black')),
        text="Your Portfolio",
        textposition="top center",
        name="Your Portfolio",
        showlegend=False
    ))

    st.plotly_chart(fig_scatter)

    # Glide path visualization
    if glide_path:
        st.markdown("### 📉 Glide Path Over Time")

        years = list(range(2025, 2025 + st.session_state.wizard_params.get('horizon_years', 50) + 1))
        equity_over_time = []
        bonds_over_time = []

        for i, year in enumerate(years):
            reduced_equity = max(0.1, equity_pct - (equity_reduction * i))
            increased_bonds = bonds_pct + max(0, equity_pct - reduced_equity)
            equity_over_time.append(reduced_equity * 100)
            bonds_over_time.append(increased_bonds * 100)

        fig_glide = go.Figure()
        fig_glide.add_trace(go.Scatter(
            x=years, y=equity_over_time,
            mode='lines+markers',
            name='Stocks %',
            line=dict(color='#FF6B6B', width=3)
        ))
        fig_glide.add_trace(go.Scatter(
            x=years, y=bonds_over_time,
            mode='lines+markers',
            name='Bonds %',
            line=dict(color='#4ECDC4', width=3)
        ))

        fig_glide.update_layout(
            title="Portfolio Allocation Over Time (Glide Path)",
            xaxis_title="Year",
            yaxis_title="Allocation %",
            height=300
        )

        st.plotly_chart(fig_glide)

    # Educational content
    with st.expander("📚 Learn More About Asset Allocation"):
        st.markdown("""
        **Common Allocation Strategies:**

        **Conservative (40/50/8/2):** Lower risk, steady returns
        - Good for: 5+ years from retirement, risk-averse investors
        - Expected return: ~4-5%, volatility: ~8-10%

        **Moderate (60/30/8/2):** Balanced growth and stability
        - Good for: Most retirees, balanced approach
        - Expected return: ~5-6%, volatility: ~10-12%

        **Aggressive (80/10/8/2):** Higher growth potential
        - Good for: Early retirement, high risk tolerance
        - Expected return: ~6-7%, volatility: ~13-15%

        **Glide Path Benefits:**
        - Reduces risk as you age
        - Locks in gains from good market years
        - Typical rule: Age in bonds (65-year-old = 65% bonds)
        """)

def step_market():
    """Market expectations step with historical context"""
    st.markdown("""
    # 📈 Market Expectations

    What returns should we expect from different asset classes? These assumptions drive your entire analysis,
    so let's ground them in historical data and realistic expectations.
    """)

    # Historical context chart
    st.markdown("### 📊 Historical Asset Class Returns (1970-2023)")

    # Create historical returns visualization
    historical_data = {
        'Asset Class': ['Stocks (S&P 500)', 'Bonds (10Y Treasury)', 'Real Estate (REITs)', 'Cash (T-Bills)'],
        'Historical Average': [10.5, 6.8, 9.7, 4.2],
        'Volatility': [17.3, 5.8, 16.1, 0.9],
        'Your Assumption': [
            st.session_state.wizard_params.get('equity_return', 0.0742) * 100,
            st.session_state.wizard_params.get('bonds_return', 0.0318) * 100,
            st.session_state.wizard_params.get('real_estate_return', 0.0563) * 100,
            st.session_state.wizard_params.get('cash_return', 0.0225) * 100
        ]
    }

    fig_hist = go.Figure()
    x_pos = np.arange(len(historical_data['Asset Class']))

    fig_hist.add_trace(go.Bar(
        x=historical_data['Asset Class'],
        y=historical_data['Historical Average'],
        name='Historical (1970-2023)',
        marker_color='lightblue',
        opacity=0.7
    ))

    fig_hist.add_trace(go.Bar(
        x=historical_data['Asset Class'],
        y=historical_data['Your Assumption'],
        name='Your Assumptions',
        marker_color='orange'
    ))

    fig_hist.update_layout(
        title="Expected Returns: Historical vs Your Assumptions",
        yaxis_title="Annual Return (%)",
        barmode='group',
        height=400
    )

    st.plotly_chart(fig_hist)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📊 Expected Returns")

        equity_return = st.slider(
            "Stock/Equity Return (%)",
            min_value=3.0,
            max_value=12.0,
            value=st.session_state.wizard_params.get('equity_return', 0.0742) * 100,
            step=0.1,
            help="Historical average: ~10.5%. Conservative: 6-8%, Moderate: 7-9%, Aggressive: 9-11%",
            key="wiz_equity_return"
        ) / 100

        bonds_return = st.slider(
            "Bonds Return (%)",
            min_value=1.0,
            max_value=8.0,
            value=st.session_state.wizard_params.get('bonds_return', 0.0318) * 100,
            step=0.1,
            help="Historical average: ~6.8%. Current low-rate environment: 2-4%",
            key="wiz_bonds_return"
        ) / 100

        real_estate_return = st.slider(
            "Real Estate/REITs Return (%)",
            min_value=2.0,
            max_value=10.0,
            value=st.session_state.wizard_params.get('real_estate_return', 0.0563) * 100,
            step=0.1,
            help="Historical average: ~9.7%. Typically between bonds and stocks",
            key="wiz_real_estate_return"
        ) / 100

        cash_return = st.slider(
            "Cash/Money Market Return (%)",
            min_value=0.5,
            max_value=6.0,
            value=st.session_state.wizard_params.get('cash_return', 0.0225) * 100,
            step=0.1,
            help="Usually close to inflation. Current rates: 4-5%",
            key="wiz_cash_return"
        ) / 100

        # Immediately sync changes back to wizard_params
        if equity_return != st.session_state.wizard_params.get('equity_return'):
            st.session_state.wizard_params['equity_return'] = equity_return
        if bonds_return != st.session_state.wizard_params.get('bonds_return'):
            st.session_state.wizard_params['bonds_return'] = bonds_return
        if real_estate_return != st.session_state.wizard_params.get('real_estate_return'):
            st.session_state.wizard_params['real_estate_return'] = real_estate_return
        if cash_return != st.session_state.wizard_params.get('cash_return'):
            st.session_state.wizard_params['cash_return'] = cash_return

    with col2:
        st.markdown("### 📊 Volatility (Risk)")

        equity_vol = st.slider(
            "Stock/Equity Volatility (%)",
            min_value=10.0,
            max_value=25.0,
            value=st.session_state.wizard_params.get('equity_vol', 0.1734) * 100,
            step=0.5,
            help="Historical: ~17%. How much stocks bounce around year-to-year",
            key="wiz_equity_vol"
        ) / 100

        bonds_vol = st.slider(
            "Bonds Volatility (%)",
            min_value=2.0,
            max_value=10.0,
            value=st.session_state.wizard_params.get('bonds_vol', 0.0576) * 100,
            step=0.2,
            help="Historical: ~5.8%. Bonds are much more stable than stocks",
            key="wiz_bonds_vol"
        ) / 100

        real_estate_vol = st.slider(
            "Real Estate Volatility (%)",
            min_value=8.0,
            max_value=25.0,
            value=st.session_state.wizard_params.get('real_estate_vol', 0.1612) * 100,
            step=0.5,
            help="Historical: ~16.1%. Similar to stocks but with different timing",
            key="wiz_real_estate_vol"
        ) / 100

        inflation_rate = st.slider(
            "Inflation Rate (%)",
            min_value=1.0,
            max_value=5.0,
            value=st.session_state.wizard_params.get('inflation_rate', 0.025) * 100,
            step=0.1,
            help="Long-term Fed target: 2%. Historical average: ~2.5%",
            key="wiz_inflation_rate"
        ) / 100

        # Immediately sync changes back to wizard_params
        if equity_vol != st.session_state.wizard_params.get('equity_vol'):
            st.session_state.wizard_params['equity_vol'] = equity_vol
        if bonds_vol != st.session_state.wizard_params.get('bonds_vol'):
            st.session_state.wizard_params['bonds_vol'] = bonds_vol
        if real_estate_vol != st.session_state.wizard_params.get('real_estate_vol'):
            st.session_state.wizard_params['real_estate_vol'] = real_estate_vol
        if inflation_rate != st.session_state.wizard_params.get('inflation_rate'):
            st.session_state.wizard_params['inflation_rate'] = inflation_rate

    # Real returns calculation
    st.markdown("### 🔍 Real Returns (After Inflation)")

    real_returns = {
        'Stocks': (equity_return - inflation_rate) * 100,
        'Bonds': (bonds_return - inflation_rate) * 100,
        'Real Estate': (real_estate_return - inflation_rate) * 100,
        'Cash': (cash_return - inflation_rate) * 100
    }

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Stocks (Real)", f"{real_returns['Stocks']:.1f}%")
    with col_b:
        st.metric("Bonds (Real)", f"{real_returns['Bonds']:.1f}%")
    with col_c:
        st.metric("Real Estate (Real)", f"{real_returns['Real Estate']:.1f}%")
    with col_d:
        st.metric("Cash (Real)", f"{real_returns['Cash']:.1f}%")

    # Educational content
    with st.expander("📚 Understanding Market Assumptions"):
        st.markdown("""
        **Why These Matter:**
        - Your return assumptions determine if your plan succeeds or fails
        - Being too optimistic can lead to running out of money
        - Being too conservative might mean working longer than necessary

        **Guidelines:**
        - **Conservative planning**: Use below-historical averages
        - **Stocks**: 6-8% (vs 10.5% historical) accounts for higher valuations today
        - **Bonds**: 2-4% (vs 6.8% historical) due to current low rates
        - **Inflation**: 2-3% is reasonable for long-term planning

        **Real vs Nominal Returns:**
        - All your planning should be in "real" (inflation-adjusted) terms
        - A 7% nominal return with 2.5% inflation = 4.5% real return
        - Real returns matter for purchasing power
        """)

def step_ai_setup():
    """AI analysis setup step"""
    st.markdown("""
    # 🤖 AI Analysis Setup (Optional)

    Get sophisticated, expert-level analysis of your retirement plan using Google's Gemini AI.
    This step is completely optional, but provides valuable insights and recommendations.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🔑 API Key Setup")

        # Debug: Check what's in wizard_params before rendering checkbox
        current_wizard_enable_ai = st.session_state.wizard_params.get('enable_ai', False)
        print(f"DEBUG: About to render checkbox with wizard_params value: {current_wizard_enable_ai}")

        enable_ai = st.checkbox(
            "Enable AI-Powered Analysis",
            value=current_wizard_enable_ai,
            help="Get personalized recommendations from Google Gemini AI",
            key="wiz_enable_ai"
        )
        print(f"DEBUG: Checkbox returned: {enable_ai}")
        # Immediately sync change back to wizard_params
        if enable_ai != st.session_state.wizard_params.get('enable_ai'):
            st.session_state.wizard_params['enable_ai'] = enable_ai

        if enable_ai:
            current_api_key = st.session_state.wizard_params.get('gemini_api_key', '')
            if current_api_key:
                st.success("✅ **API Key loaded from previous session!** You're all set for AI analysis.")
            else:
                st.info("""
                **🔑 Get Your Free Gemini API Key:**

                1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
                2. Click **'Get API key'** → **'Create API key'**
                3. Copy your key and paste it below

                **Free Tier:** Gemini 2.5 Pro (100 requests/day), Flash models (higher limits)
                """)

                st.warning("""
                **🔒 IMPORTANT PRIVACY NOTICE:**

                **Free Tier Data Usage:** Google may use your conversations with Gemini free tier models to improve their AI services. Your retirement planning data could be used for training.

                **For Maximum Privacy:**
                - Use Gemini Pro API (paid tier) which doesn't use data for training
                - Or disable AI analysis entirely
                - Never include real account numbers or sensitive personal details

                ⚠️ **This app processes sensitive financial information. Consider the privacy implications before enabling AI analysis.**
                """)

            # Debug: Check API key in wizard_params before rendering
            current_wizard_api_key = st.session_state.wizard_params.get('gemini_api_key', '')
            print(f"DEBUG: About to render text input with wizard_params API key: {current_wizard_api_key[:10] if current_wizard_api_key else 'empty'}...")

            api_key = st.text_input(
                "Gemini API Key",
                value=current_wizard_api_key,
                type="password",
                help="Your free API key from Google AI Studio",
                key="wiz_api_key"
            )
            print(f"DEBUG: Text input returned: {api_key[:10] if api_key else 'empty'}...")
            # Immediately sync change back to wizard_params
            if api_key != st.session_state.wizard_params.get('gemini_api_key'):
                st.session_state.wizard_params['gemini_api_key'] = api_key

            # Model selection
            available_models = RetirementAnalyzer.get_available_models()
            model_options = list(available_models.keys())

            selected_model = st.selectbox(
                "AI Model",
                options=model_options,
                index=model_options.index(st.session_state.wizard_params.get('gemini_model', 'gemini-2.5-pro')) if st.session_state.wizard_params.get('gemini_model', 'gemini-2.5-pro') in model_options else 0,
                format_func=lambda x: available_models[x],
                help="Gemini 2.5 Pro is the most capable model for retirement analysis",
                key="wiz_selected_model"
            )
            # Immediately sync change back to wizard_params
            if selected_model != st.session_state.wizard_params.get('gemini_model'):
                st.session_state.wizard_params['gemini_model'] = selected_model

    with col2:
        st.markdown("### 🎯 What You'll Get")

        if enable_ai:
            st.success("""
            **✨ AI Analysis Features:**

            🎯 **Expert Assessment**
            - Success probability analysis
            - Risk identification
            - Strategic recommendations

            💡 **Personalized Advice**
            - Asset allocation optimization
            - Spending adjustment strategies
            - Tax planning insights

            💬 **Interactive Chat**
            - Ask follow-up questions
            - Explore "what-if" scenarios
            - Get detailed explanations

            🧠 **Expert Positioning**
            - Nobel Prize-level financial economist
            - Political economist understanding
            - Behavioral psychology insights
            - Master strategist experience
            """)

            if api_key:
                st.info("✅ Ready for AI analysis!")
            else:
                st.warning("⚠️ API key needed for AI features")
        else:
            st.info("""
            **📊 Standard Analysis:**

            Without AI, you'll still get:
            - Complete Monte Carlo simulation
            - Interactive visualizations
            - Success rate calculations
            - Year-by-year projections
            - Comprehensive charts and tables

            *AI analysis adds expert insights and recommendations on top of these core features.*
            """)

    # Test API key functionality
    if enable_ai and api_key:
        if st.button("🧪 Test API Key", help="Verify your API key works"):
            with st.spinner("Testing API connection..."):
                try:
                    analyzer = RetirementAnalyzer(api_key, selected_model)
                    if analyzer.is_available:
                        st.success("✅ API key works! Ready for AI analysis.")
                    else:
                        st.error("❌ API key test failed. Please check your key.")
                except Exception as e:
                    st.error(f"❌ Error testing API: {str(e)}")

    with st.expander("📚 Learn More About AI Analysis"):
        st.markdown("""
        **How It Works:**
        1. The wizard generates your complete parameter set
        2. Parameters automatically transfer to Monte Carlo analysis
        3. AI analyzes your results using comprehensive context
        4. Get expert recommendations and interactive chat

        **Privacy & Security:**
        - Your API key is stored locally only
        - No personal data is sent to our servers
        - All AI analysis happens directly with Google
        - You control what data to include

        **Model Comparison:**
        - **Gemini 2.5 Pro**: Most capable, best for complex analysis (100/day)
        - **Gemini 2.5 Flash**: Fast and efficient, good for quick insights
        - **Older models**: Stable but less sophisticated

        **Cost:** The free tier is generous for personal retirement planning!
        """)

    # Save AI settings to UI config when they change
    # Only save if user has actually made changes (detect when values differ from loaded config)
    current_ui_config = load_ui_config()

    # Get the original loaded values to compare against
    original_enable_ai = current_ui_config.get('enable_ai_analysis', False)
    original_api_key = current_ui_config.get('gemini_api_key', '')
    original_model = current_ui_config.get('gemini_model', 'gemini-2.5-pro')

    # Check if user has actually changed values from what was loaded
    current_api_key = st.session_state.wizard_params.get('gemini_api_key', '')
    current_model = st.session_state.wizard_params.get('gemini_model', 'gemini-2.5-pro')

    # Only save if there are real changes from the user
    user_made_changes = (
        enable_ai != original_enable_ai or
        current_api_key != original_api_key or
        current_model != original_model
    )

    if user_made_changes:
        current_ui_config['enable_ai_analysis'] = enable_ai
        current_ui_config['gemini_api_key'] = current_api_key
        current_ui_config['gemini_model'] = current_model
        save_ui_config(current_ui_config)
        print(f"DEBUG: User made changes, saved UI config - enable_ai: {enable_ai}, api_key: {current_api_key[:10] if current_api_key else 'empty'}...")
    else:
        print(f"DEBUG: No user changes detected, not saving config")

def step_taxes():
    """Tax planning step with state comparison"""
    st.markdown("""
    # 🏛️ Tax Planning

    Where you retire can significantly impact your after-tax income. Let's set up your
    tax situation and see how different states compare.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🌍 State Selection")

        # Import state tax function from tax utils
        from tax_utils import get_state_tax_rates

        state_options = ['CA', 'NY', 'TX', 'FL', 'WA', 'NV', 'PA', 'OH', 'IL', 'Federal Only']
        state_names = {
            'CA': 'California (High Tax)',
            'NY': 'New York (High Tax)',
            'TX': 'Texas (No State Tax)',
            'FL': 'Florida (No State Tax)',
            'WA': 'Washington (No State Tax)',
            'NV': 'Nevada (No State Tax)',
            'PA': 'Pennsylvania (Moderate Tax)',
            'OH': 'Ohio (Moderate Tax)',
            'IL': 'Illinois (Moderate Tax)',
            'Federal Only': 'Federal Only'
        }

        selected_state = st.selectbox(
            "Retirement State",
            options=state_options,
            index=state_options.index(st.session_state.wizard_params.get('state', 'CA')),
            format_func=lambda x: state_names[x],
            help="Choose where you plan to spend most of your retirement",
            key="wiz_selected_state"
        )
        # Immediately sync change back to wizard_params
        if selected_state != st.session_state.wizard_params.get('state'):
            st.session_state.wizard_params['state'] = selected_state

        filing_status = st.radio(
            "Filing Status",
            options=['MFJ', 'Single'],
            index=0 if st.session_state.wizard_params.get('filing_status', 'MFJ') == 'MFJ' else 1,
            help="Married Filing Jointly typically has lower rates",
            key="wiz_filing_status"
        )
        # Immediately sync change back to wizard_params
        if filing_status != st.session_state.wizard_params.get('filing_status'):
            st.session_state.wizard_params['filing_status'] = filing_status

        standard_deduction = st.number_input(
            "Standard Deduction",
            min_value=10000,
            max_value=50000,
            value=int(st.session_state.wizard_params.get('standard_deduction', 29200)),
            step=1000,
            help="2025 standard deduction amounts",
            key="wiz_standard_deduction"
        )
        # Immediately sync change back to wizard_params
        if standard_deduction != st.session_state.wizard_params.get('standard_deduction'):
            st.session_state.wizard_params['standard_deduction'] = standard_deduction

    with col2:
        st.markdown("### 💰 Tax Bracket Preview")

        # Get tax brackets for selected state
        tax_rates = get_state_tax_rates(selected_state, filing_status)

        # Display brackets
        brackets_df = pd.DataFrame([
            {"Income Range": f"${bracket[0]:,}+", "Tax Rate": f"{bracket[1]:.1%}"}
            for bracket in tax_rates
        ])

        st.dataframe(brackets_df)

        # Calculate sample taxes
        st.markdown("### 📊 Sample Tax Calculations")

        sample_withdrawals = [50000, 100000, 150000, 200000]

        for withdrawal in sample_withdrawals:
            from tax import calculate_tax
            taxable_income = max(0, withdrawal - standard_deduction)
            tax = calculate_tax(taxable_income, tax_rates)
            effective_rate = tax / withdrawal * 100 if withdrawal > 0 else 0

            st.metric(
                f"${withdrawal:,} withdrawal",
                f"${tax:,.0f} tax ({effective_rate:.1f}%)"
            )

    # State comparison visualization
    st.markdown("### 🗺️ State Tax Comparison")

    # Calculate taxes across different states for comparison
    comparison_withdrawal = 100000
    taxable_income_comp = max(0, comparison_withdrawal - standard_deduction)

    comparison_data = []
    for state in ['TX', 'FL', 'CA', 'NY', 'PA']:
        state_rates = get_state_tax_rates(state, filing_status)
        state_tax = calculate_tax(taxable_income_comp, state_rates)
        effective_rate = state_tax / comparison_withdrawal * 100

        comparison_data.append({
            'State': state_names[state],
            'Tax': state_tax,
            'Effective Rate': effective_rate
        })

    comparison_df = pd.DataFrame(comparison_data)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=comparison_df['State'],
        y=comparison_df['Tax'],
        marker_color=['red' if state == state_names[selected_state] else 'lightblue'
                     for state in comparison_df['State']],
        text=[f"${tax:,.0f}" for tax in comparison_df['Tax']],
        textposition='auto'
    ))

    fig.update_layout(
        title=f"Annual Tax on ${comparison_withdrawal:,} Withdrawal",
        yaxis_title="Tax ($)",
        height=400
    )

    st.plotly_chart(fig)

    # Educational content
    with st.expander("📚 Learn More About Retirement Tax Planning"):
        st.markdown("""
        **State Tax Strategies:**

        **No-Tax States (TX, FL, WA, NV):**
        - No state income tax on retirement withdrawals
        - May have higher property/sales taxes
        - Popular for retirees seeking tax efficiency

        **High-Tax States (CA, NY):**
        - Significant state income tax (up to 13.3% in CA)
        - Often have good healthcare and services
        - Consider partial year residency strategies

        **Moderate-Tax States (PA, OH, IL):**
        - Balanced approach with reasonable rates
        - Often lower cost of living
        - Good compromise between taxes and lifestyle

        **Tax-Efficient Withdrawal Strategies:**
        - Use standard deduction effectively
        - Consider Roth conversions in low-tax years
        - Coordinate with Social Security timing
        - Balance withdrawal amounts across tax years
        """)

def step_social_security():
    """Social Security step with benefit calculator"""
    st.markdown("""
    # 🏛️ Social Security Planning

    Social Security can provide a significant portion of your retirement income.
    Let's plan when to claim benefits and account for potential funding challenges.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 👤 Primary Beneficiary")

        ss_primary_benefit = st.number_input(
            "Annual Social Security Benefit",
            min_value=0,
            max_value=80000,
            value=int(st.session_state.wizard_params.get('ss_primary_benefit', 40000)),
            step=1000,
            help="Estimated annual benefit at full retirement age (check ssa.gov)",
            key="wiz_ss_primary_benefit"
        )
        # Immediately sync change back to wizard_params
        if ss_primary_benefit != st.session_state.wizard_params.get('ss_primary_benefit'):
            st.session_state.wizard_params['ss_primary_benefit'] = ss_primary_benefit

        ss_primary_start_age = st.slider(
            "Benefit Start Age",
            min_value=62,
            max_value=70,
            value=st.session_state.wizard_params.get('ss_primary_start_age', 67),
            help="62=reduced benefits, 67=full benefits, 70=maximum benefits",
            key="wiz_ss_primary_start_age"
        )
        # Immediately sync change back to wizard_params
        if ss_primary_start_age != st.session_state.wizard_params.get('ss_primary_start_age'):
            st.session_state.wizard_params['ss_primary_start_age'] = ss_primary_start_age

        # Calculate adjustment for early/delayed claiming
        if ss_primary_start_age < 67:
            reduction = (67 - ss_primary_start_age) * 0.067  # ~6.7% per year early
            adjusted_benefit = ss_primary_benefit * (1 - reduction)
            st.info(f"Early claiming reduces benefit to ~${adjusted_benefit:,.0f}/year")
        elif ss_primary_start_age > 67:
            increase = (ss_primary_start_age - 67) * 0.08  # 8% per year delayed
            adjusted_benefit = ss_primary_benefit * (1 + increase)
            st.success(f"Delayed claiming increases benefit to ~${adjusted_benefit:,.0f}/year")
        else:
            adjusted_benefit = ss_primary_benefit
            st.info(f"Full retirement age benefit: ${adjusted_benefit:,.0f}/year")

        st.markdown("### 👫 Spousal Benefits")

        ss_spousal_benefit = st.number_input(
            "Spouse's Social Security Benefit",
            min_value=0,
            max_value=60000,
            value=int(st.session_state.wizard_params.get('ss_spousal_benefit', 0)),
            step=1000,
            help="Leave at 0 if no spouse or spouse has no benefits",
            key="wiz_ss_spousal_benefit"
        )
        # Immediately sync change back to wizard_params
        if ss_spousal_benefit != st.session_state.wizard_params.get('ss_spousal_benefit'):
            st.session_state.wizard_params['ss_spousal_benefit'] = ss_spousal_benefit

        if ss_spousal_benefit > 0:
            ss_spousal_start_age = st.slider(
                "Spouse Benefit Start Age",
                min_value=62,
                max_value=70,
                value=st.session_state.wizard_params.get('ss_spousal_start_age', 67),
                help="Spouse's claiming age",
                key="wiz_ss_spousal_start_age"
            )
            # Immediately sync change back to wizard_params
            if ss_spousal_start_age != st.session_state.wizard_params.get('ss_spousal_start_age'):
                st.session_state.wizard_params['ss_spousal_start_age'] = ss_spousal_start_age

    with col2:
        st.markdown("### ⚠️ Social Security Trust Fund Scenarios")

        funding_scenarios = {
            'conservative': 'Conservative: 19% benefit cuts starting 2034',
            'moderate': 'Moderate: Gradual cuts with partial reform',
            'optimistic': 'Optimistic: Full benefits through tax increases',
            'custom': 'Custom: Define your own scenario'
        }

        ss_funding_scenario = st.selectbox(
            "Trust Fund Scenario",
            options=list(funding_scenarios.keys()),
            index=list(funding_scenarios.keys()).index(st.session_state.wizard_params.get('ss_funding_scenario', 'moderate')),
            format_func=lambda x: funding_scenarios[x],
            help="Based on 2024 Social Security Trustees Report projections",
            key="wiz_ss_funding_scenario"
        )
        # Immediately sync change back to wizard_params
        if ss_funding_scenario != st.session_state.wizard_params.get('ss_funding_scenario'):
            st.session_state.wizard_params['ss_funding_scenario'] = ss_funding_scenario

        if ss_funding_scenario == 'custom':
            custom_reduction = st.slider(
                "Benefit Reduction %",
                min_value=0.0,
                max_value=30.0,
                value=st.session_state.wizard_params.get('ss_custom_reduction', 10.0),
                step=1.0,
                help="Percentage reduction in benefits",
                key="wiz_custom_reduction"
            ) / 100
            # Immediately sync change back to wizard_params
            if custom_reduction != st.session_state.wizard_params.get('ss_custom_reduction'):
                st.session_state.wizard_params['ss_custom_reduction'] = custom_reduction

            reduction_start_year = st.number_input(
                "Reduction Start Year",
                min_value=2025,
                max_value=2050,
                value=st.session_state.wizard_params.get('ss_reduction_start_year', 2034),
                help="When benefit cuts begin",
                key="wiz_reduction_start_year"
            )
            # Immediately sync change back to wizard_params
            if reduction_start_year != st.session_state.wizard_params.get('ss_reduction_start_year'):
                st.session_state.wizard_params['ss_reduction_start_year'] = reduction_start_year

        # Show total household Social Security income
        st.markdown("### 💰 Total Household SS Income")

        total_ss = adjusted_benefit + (ss_spousal_benefit if ss_spousal_benefit > 0 else 0)
        st.metric("Combined Annual Benefits", f"${total_ss:,.0f}")

        if ss_funding_scenario == 'conservative':
            reduced_benefits = total_ss * 0.81  # 19% cut
            st.warning(f"After 2034 cuts: ${reduced_benefits:,.0f}")
        elif ss_funding_scenario == 'moderate':
            reduced_benefits = total_ss * 0.90  # 10% eventual cut
            st.info(f"After gradual cuts: ${reduced_benefits:,.0f}")

    # Timing visualization
    st.markdown("### 📅 Benefit Timeline Visualization")

    years = list(range(2025, 2065))
    primary_benefits = []
    spousal_benefits = []

    for year in years:
        # Primary benefits
        if year >= 2025 + (ss_primary_start_age - 30):  # Assuming current age 30 for calculation
            primary_annual = adjusted_benefit

            # Apply funding scenario
            if ss_funding_scenario == 'conservative' and year >= 2034:
                primary_annual *= 0.81
            elif ss_funding_scenario == 'moderate' and year >= 2034:
                # Gradual reduction
                years_since_2034 = year - 2034
                reduction = min(0.10, 0.05 + years_since_2034 * 0.01)  # 5% + 1%/year, cap at 10%
                primary_annual *= (1 - reduction)
            elif ss_funding_scenario == 'custom' and year >= reduction_start_year:
                primary_annual *= (1 - custom_reduction)

            primary_benefits.append(primary_annual)
        else:
            primary_benefits.append(0)

        # Spousal benefits (simplified)
        if ss_spousal_benefit > 0 and year >= 2025 + (ss_spousal_start_age - 30):
            spousal_annual = ss_spousal_benefit
            # Apply same funding scenario
            if ss_funding_scenario == 'conservative' and year >= 2034:
                spousal_annual *= 0.81
            elif ss_funding_scenario == 'moderate' and year >= 2034:
                years_since_2034 = year - 2034
                reduction = min(0.10, 0.05 + years_since_2034 * 0.01)
                spousal_annual *= (1 - reduction)
            elif ss_funding_scenario == 'custom' and year >= reduction_start_year:
                spousal_annual *= (1 - custom_reduction)

            spousal_benefits.append(spousal_annual)
        else:
            spousal_benefits.append(0)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years, y=primary_benefits,
        mode='lines+markers',
        name='Primary SS',
        line=dict(color='blue', width=3)
    ))

    if ss_spousal_benefit > 0:
        fig.add_trace(go.Scatter(
            x=years, y=spousal_benefits,
            mode='lines+markers',
            name='Spousal SS',
            line=dict(color='green', width=3)
        ))

    fig.update_layout(
        title="Social Security Benefits Over Time",
        xaxis_title="Year",
        yaxis_title="Annual Benefits ($)",
        height=400
    )

    st.plotly_chart(fig)

    # Educational content
    with st.expander("📚 Learn More About Social Security Planning"):
        st.markdown("""
        **Claiming Age Strategies:**

        **Age 62 (Earliest):**
        - Benefits reduced by ~25-30%
        - Good if you need income immediately
        - Consider health and longevity

        **Age 67 (Full Retirement Age):**
        - 100% of calculated benefit
        - Standard planning assumption
        - Balanced approach for most people

        **Age 70 (Maximum):**
        - Benefits increased by ~32% vs age 62
        - Excellent if you can delay and expect longevity
        - Provides inflation-protected income

        **Trust Fund Scenarios:**
        - **Conservative**: Current law with scheduled cuts
        - **Moderate**: Likely Congressional intervention
        - **Optimistic**: Full funding through tax increases/reforms
        - **Custom**: Plan for your own assumptions

        **Spousal Benefits:**
        - Can claim on spouse's record (50% of their benefit)
        - File and suspend strategies (consult professional)
        - Survivor benefits considerations
        """)

def step_guardrails():
    """Spending guardrails step with interactive examples"""
    st.markdown("""
    # ⚖️ Spending Guardrails

    Guardrails help you adjust spending based on portfolio performance, improving your
    chances of not running out of money while allowing you to spend more when things go well.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🎯 Guardrail Settings")

        lower_guardrail = st.slider(
            "Lower Guardrail (Withdrawal Rate %)",
            min_value=0.0,
            max_value=5.0,
            value=st.session_state.wizard_params.get('lower_guardrail', 0.03) * 100,  # Convert from decimal to %
            step=0.1,
            help="If withdrawal rate exceeds this, cut spending",
            key="wiz_lower_guardrail"
        ) / 100
        # Immediately sync change back to wizard_params
        if lower_guardrail != st.session_state.wizard_params.get('lower_guardrail'):
            st.session_state.wizard_params['lower_guardrail'] = lower_guardrail

        upper_guardrail = st.slider(
            "Upper Guardrail (Withdrawal Rate %)",
            min_value=0.0,
            max_value=5.0,
            value=st.session_state.wizard_params.get('upper_guardrail', 0.05) * 100,  # Convert from decimal to %
            step=0.1,
            help="If withdrawal rate falls below this, increase spending",
            key="wiz_upper_guardrail"
        ) / 100
        # Immediately sync change back to wizard_params
        if upper_guardrail != st.session_state.wizard_params.get('upper_guardrail'):
            st.session_state.wizard_params['upper_guardrail'] = upper_guardrail

        spending_adjustment = st.slider(
            "Spending Adjustment %",
            min_value=5.0,
            max_value=20.0,
            value=st.session_state.wizard_params.get('spending_adjustment', 0.10) * 100,  # Convert from decimal to %
            step=1.0,
            help="How much to adjust spending when guardrails trigger",
            key="wiz_spending_adjustment"
        ) / 100
        # Immediately sync change back to wizard_params
        if spending_adjustment != st.session_state.wizard_params.get('spending_adjustment'):
            st.session_state.wizard_params['spending_adjustment'] = spending_adjustment

        max_increase = st.slider(
            "Maximum Spending Increase %",
            min_value=2.0,
            max_value=15.0,
            value=st.session_state.wizard_params.get('max_spending_increase', 0.10) * 100,  # Convert from decimal to %
            step=1.0,
            help="Cap on annual spending increases",
            key="wiz_max_increase"
        ) / 100
        # Immediately sync change back to wizard_params
        if max_increase != st.session_state.wizard_params.get('max_spending_increase'):
            st.session_state.wizard_params['max_spending_increase'] = max_increase

        max_decrease = st.slider(
            "Maximum Spending Decrease %",
            min_value=5.0,
            max_value=25.0,
            value=st.session_state.wizard_params.get('max_spending_decrease', 0.10) * 100,  # Convert from decimal to %
            step=1.0,
            key="wiz_max_decrease",
            help="Cap on annual spending decreases"
        ) / 100
        # Immediately sync change back to wizard_params
        if max_decrease != st.session_state.wizard_params.get('max_spending_decrease'):
            st.session_state.wizard_params['max_spending_decrease'] = max_decrease

    with col2:
        st.markdown("### 🏠 Spending Bounds")

        spending_floor = st.number_input(
            "Spending Floor ($)",
            min_value=0,
            max_value=500_000,
            value=int(st.session_state.wizard_params.get('spending_floor_real', 160_000)),
            step=5_000,
            help="💰 **Minimum annual spending** - Never go below this amount (real dollars)\n\n• Essential expenses coverage\n• Healthcare and housing minimums\n• Only applies until Floor End Year",
            key="wiz_spending_floor"
        )
        # Immediately sync change back to wizard_params
        if spending_floor != st.session_state.wizard_params.get('spending_floor_real'):
            st.session_state.wizard_params['spending_floor_real'] = spending_floor

        spending_ceiling = st.number_input(
            "Spending Ceiling ($)",
            min_value=spending_floor,
            max_value=1_000_000,
            value=int(st.session_state.wizard_params.get('spending_ceiling_real', 275_000)),
            step=5_000,
            help="🏠 **Maximum annual spending** - Never exceed this amount (real dollars)\n\n• Lifestyle cap or practical limit\n• Applies throughout retirement\n• Prevents excessive withdrawals",
            key="wiz_spending_ceiling"
        )
        # Immediately sync change back to wizard_params
        if spending_ceiling != st.session_state.wizard_params.get('spending_ceiling_real'):
            st.session_state.wizard_params['spending_ceiling_real'] = spending_ceiling

        floor_end_year = st.number_input(
            "Floor End Year",
            min_value=2025,
            max_value=2080,
            value=st.session_state.wizard_params.get('floor_end_year', 2041),
            step=1,
            help="📅 **When spending floor stops applying**\n\n• Typical: First 15-20 years of retirement\n• After this year, spending can drop below floor\n• Reflects reduced needs in later retirement",
            key="wiz_floor_end_year"
        )
        # Immediately sync change back to wizard_params
        if floor_end_year != st.session_state.wizard_params.get('floor_end_year'):
            st.session_state.wizard_params['floor_end_year'] = floor_end_year
        st.markdown("### 📊 How Guardrails Work")

        # Example scenarios
        portfolio_values = [2000000, 1500000, 1000000]
        base_spending = 100000

        for portfolio in portfolio_values:
            withdrawal_rate = base_spending / portfolio * 100

            if withdrawal_rate > lower_guardrail * 100:
                action = "🔴 Cut spending"
                new_spending = base_spending * (1 - spending_adjustment)
            elif withdrawal_rate < upper_guardrail * 100:
                action = "🟢 Increase spending"
                new_spending = base_spending * (1 + min(spending_adjustment, max_increase))
            else:
                action = "➖ No change"
                new_spending = base_spending

            st.metric(
                f"Portfolio: ${portfolio:,}",
                f"{withdrawal_rate:.1f}% → {action}",
                f"${new_spending:,.0f} spending"
            )

    # Interactive guardrails visualization
    st.markdown("### 📈 Guardrails in Action")

    # Simulate market scenarios
    years = list(range(2025, 2045))
    scenarios = {
        "Bull Market": [1.08] * len(years),
        "Bear Market": [0.92] * len(years),
        "Volatile Market": [1.15, 0.85, 1.20, 0.80, 1.10, 0.90] * (len(years) // 6)
    }

    fig = go.Figure()

    for scenario_name, returns in scenarios.items():
        portfolio_values = [2500000]  # Starting value
        spending_values = [100000]   # Starting spending

        for i, annual_return in enumerate(returns[:len(years)-1]):
            # Apply return
            new_portfolio = portfolio_values[-1] * annual_return - spending_values[-1]
            portfolio_values.append(max(0, new_portfolio))

            # Apply guardrails
            if new_portfolio > 0:
                wr = spending_values[-1] / new_portfolio
                if wr > lower_guardrail:
                    new_spending = spending_values[-1] * (1 - spending_adjustment)
                elif wr < upper_guardrail:
                    new_spending = spending_values[-1] * (1 + min(spending_adjustment, max_increase))
                else:
                    new_spending = spending_values[-1]
                spending_values.append(max(new_spending, spending_values[-1] * (1 - max_decrease)))
            else:
                spending_values.append(0)

        fig.add_trace(go.Scatter(
            x=years,
            y=spending_values,
            mode='lines+markers',
            name=scenario_name,
            line=dict(width=3)
        ))

    fig.update_layout(
        title="Spending Over Time with Guardrails",
        xaxis_title="Year",
        yaxis_title="Annual Spending ($)",
        height=400
    )

    st.plotly_chart(fig)

    with st.expander("📚 Learn More About Guardrails"):
        st.markdown("""
        **Benefits of Guardrails:**
        - Increase success rates by 15-25%
        - Allow higher initial spending than fixed withdrawal rates
        - Provide automatic adjustment mechanism
        - Reduce sequence of returns risk

        **How They Work:**
        - Monitor withdrawal rate each year
        - Cut spending if rate gets too high (preserve capital)
        - Increase spending if rate gets too low (enjoy wealth)
        - Smooth adjustments prevent dramatic lifestyle changes

        **Typical Settings:**
        - Lower guardrail: 5.0-6.0% (trigger spending cuts)
        - Upper guardrail: 3.5-4.5% (trigger spending increases)
        - Adjustment: 10% (moderate lifestyle change)
        - Caps: Prevent extreme year-over-year changes
        """)

def step_cash_flows():
    """Cash flows (income & expenses) step"""
    st.markdown("""
    # 💸 Income & Expense Streams

    Beyond your basic retirement spending, you'll likely have other income sources
    and major expenses over time. Let's plan for these cash flows.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 💰 Income Streams")

        # Initialize income streams if not exists
        if 'income_streams' not in st.session_state.wizard_params:
            st.session_state.wizard_params['income_streams'] = []

        income_streams = st.session_state.wizard_params.get('income_streams', [])

        # Add new income stream
        if st.button("➕ Add Income Stream"):
            income_streams.append({
                'description': 'Consulting income',
                'amount': 25000,
                'start_year': 2026,
                'duration': 5
            })

        # Edit existing income streams
        for i, stream in enumerate(income_streams):
            st.markdown(f"**Income Stream {i+1}:**")

            col_desc, col_amount = st.columns([2, 1])
            with col_desc:
                stream['description'] = st.text_input(
                    f"Description",
                    value=stream['description'],
                    key=f"income_desc_{i}"
                )
            with col_amount:
                stream['amount'] = st.number_input(
                    f"Annual Amount",
                    min_value=0,
                    value=stream['amount'],
                    step=1000,
                    key=f"income_amount_{i}"
                )

            col_start, col_duration, col_delete = st.columns([1, 1, 1])
            with col_start:
                stream['start_year'] = st.number_input(
                    f"Start Year",
                    min_value=2025,
                    max_value=2070,
                    value=stream['start_year'],
                    key=f"income_start_{i}"
                )
            with col_duration:
                stream['duration'] = st.number_input(
                    f"Duration (years)",
                    min_value=1,
                    max_value=30,
                    value=stream['duration'],
                    key=f"income_duration_{i}"
                )
            with col_delete:
                if st.button("🗑️", key=f"delete_income_{i}", help="Delete this income stream"):
                    income_streams.pop(i)
                    st.rerun()

    with col2:
        st.markdown("### 💸 Expense Streams")

        # Initialize expense streams if not exists
        if 'expense_streams' not in st.session_state.wizard_params:
            st.session_state.wizard_params['expense_streams'] = []

        expense_streams = st.session_state.wizard_params.get('expense_streams', [])

        # Add new expense stream
        if st.button("➕ Add Expense Stream"):
            expense_streams.append({
                'description': 'College tuition',
                'amount': 50000,
                'start_year': 2030,
                'duration': 4
            })

        # Edit existing expense streams
        for i, stream in enumerate(expense_streams):
            st.markdown(f"**Expense Stream {i+1}:**")

            col_desc, col_amount = st.columns([2, 1])
            with col_desc:
                stream['description'] = st.text_input(
                    f"Description",
                    value=stream['description'],
                    key=f"expense_desc_{i}"
                )
            with col_amount:
                stream['amount'] = st.number_input(
                    f"Annual Amount",
                    min_value=0,
                    value=stream['amount'],
                    step=1000,
                    key=f"expense_amount_{i}"
                )

            col_start, col_duration, col_delete = st.columns([1, 1, 1])
            with col_start:
                stream['start_year'] = st.number_input(
                    f"Start Year",
                    min_value=2025,
                    max_value=2070,
                    value=stream['start_year'],
                    key=f"expense_start_{i}"
                )
            with col_duration:
                stream['duration'] = st.number_input(
                    f"Duration (years)",
                    min_value=1,
                    max_value=30,
                    value=stream['duration'],
                    key=f"expense_duration_{i}"
                )
            with col_delete:
                if st.button("🗑️", key=f"delete_expense_{i}", help="Delete this expense stream"):
                    expense_streams.pop(i)
                    st.rerun()

    # Timeline visualization
    if income_streams or expense_streams:
        st.markdown("### 📅 Cash Flow Timeline")

        years = list(range(2025, 2055))
        annual_income = [0] * len(years)
        annual_expenses = [0] * len(years)

        # Calculate annual totals
        for stream in income_streams:
            for year_idx, year in enumerate(years):
                if stream['start_year'] <= year < stream['start_year'] + stream['duration']:
                    annual_income[year_idx] += stream['amount']

        for stream in expense_streams:
            for year_idx, year in enumerate(years):
                if stream['start_year'] <= year < stream['start_year'] + stream['duration']:
                    annual_expenses[year_idx] += stream['amount']

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=years,
            y=annual_income,
            name='Additional Income',
            marker_color='green',
            opacity=0.7
        ))

        fig.add_trace(go.Bar(
            x=years,
            y=[-x for x in annual_expenses],  # Negative for expenses
            name='Additional Expenses',
            marker_color='red',
            opacity=0.7
        ))

        fig.update_layout(
            title="Additional Cash Flows Over Time",
            xaxis_title="Year",
            yaxis_title="Amount ($)",
            barmode='relative',
            height=400
        )

        st.plotly_chart(fig)

def step_advanced():
    """Advanced options step"""
    st.markdown("""
    # ⚙️ Advanced Options

    Fine-tune your retirement analysis with additional scenarios and market assumptions.
    These are optional but can provide more comprehensive planning.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🎓 College Planning")

        college_enabled = st.checkbox(
            "Include College Expenses",
            value=st.session_state.wizard_params.get('college_enabled', False),
            help="Add college tuition and expenses to your plan",
            key="wiz_college_enabled"
        )
        # Immediately sync change back to wizard_params
        if college_enabled != st.session_state.wizard_params.get('college_enabled'):
            st.session_state.wizard_params['college_enabled'] = college_enabled

        if college_enabled:
            college_amount = st.number_input(
                "Annual College Cost",
                min_value=0,
                max_value=200000,
                value=int(st.session_state.wizard_params.get('college_amount', 75000)),
                step=5000,
                help="Annual cost per student",
                key="wiz_college_amount"
            )
            # Immediately sync change back to wizard_params
            if college_amount != st.session_state.wizard_params.get('college_amount'):
                st.session_state.wizard_params['college_amount'] = college_amount

            college_years = st.slider(
                "Total College Years",
                min_value=2,
                max_value=16,
                value=st.session_state.wizard_params.get('college_years', 8),
                help="Total years across all children",
                key="wiz_college_years"
            )
            # Immediately sync change back to wizard_params
            if college_years != st.session_state.wizard_params.get('college_years'):
                st.session_state.wizard_params['college_years'] = college_years

            college_start_year = st.number_input(
                "College Start Year",
                min_value=2025,
                max_value=2050,
                value=st.session_state.wizard_params.get('college_start_year', 2032),
                key="wiz_college_start_year"
            )
            # Immediately sync change back to wizard_params
            if college_start_year != st.session_state.wizard_params.get('college_start_year'):
                st.session_state.wizard_params['college_start_year'] = college_start_year

        st.markdown("### 🏠 Inheritance")

        inheritance_amount = st.number_input(
            "Expected Inheritance",
            min_value=0,
            max_value=5000000,
            value=int(st.session_state.wizard_params.get('inheritance_amount', 0)),
            step=25000,
            help="One-time inheritance expected during retirement",
            key="wiz_inheritance_amount"
        )

        # Immediately sync change back to wizard_params to keep them in sync
        if inheritance_amount != st.session_state.wizard_params.get('inheritance_amount'):
            st.session_state.wizard_params['inheritance_amount'] = inheritance_amount
            print(f"DEBUG [inheritance_amount widget]: Synced change to wizard_params: {inheritance_amount}")

        if inheritance_amount > 0:
            inheritance_year = st.number_input(
                "Inheritance Year",
                min_value=2025,
                max_value=2065,
                value=st.session_state.wizard_params.get('inheritance_year', 2040),
                key="wiz_inheritance_year"
            )
            # Immediately sync change back to wizard_params
            if inheritance_year != st.session_state.wizard_params.get('inheritance_year'):
                st.session_state.wizard_params['inheritance_year'] = inheritance_year

    with col2:
        st.markdown("### 📊 Market Scenarios")

        market_scenarios = {
            'baseline': 'Baseline: Historical average returns',
            'recession_early': 'Early Recession: Bad returns years 1-3',
            'recession_late': 'Late Recession: Bad returns years 15-17',
            'inflation_shock': 'Inflation Shock: High inflation scenario',
            'long_bear': 'Extended Bear Market: Prolonged low returns'
        }

        market_regime = st.selectbox(
            "Market Scenario",
            options=list(market_scenarios.keys()),
            index=list(market_scenarios.keys()).index(st.session_state.wizard_params.get('market_regime', 'baseline')),
            format_func=lambda x: market_scenarios[x],
            help="Test your plan against different market conditions",
            key="wiz_market_regime"
        )
        # Immediately sync change back to wizard_params
        if market_regime != st.session_state.wizard_params.get('market_regime'):
            st.session_state.wizard_params['market_regime'] = market_regime

        st.markdown("### 🔢 Simulation Settings")

        # Get current value and find its index in options
        options = [1000, 5000, 10000, 25000]
        current_sims = st.session_state.wizard_params.get('num_simulations', 10000)
        try:
            current_index = options.index(current_sims)
        except ValueError:
            current_index = 2  # Default to 10,000 if not found

        num_simulations = st.selectbox(
            "Number of Simulations",
            options=options,
            index=current_index,  # Use wizard_params as source of truth
            help="More simulations = more accurate but slower",
            key="wiz_num_simulations"
        )

        # Immediately sync back to wizard_params
        if num_simulations != st.session_state.wizard_params.get('num_simulations'):
            st.session_state.wizard_params['num_simulations'] = num_simulations
            print(f"DEBUG [num_simulations widget]: Synced change to wizard_params: {num_simulations}")

        cape_now = st.slider(
            "Current CAPE Ratio",
            min_value=15.0,
            max_value=45.0,
            value=st.session_state.wizard_params.get('cape_now', 28.0),
            step=1.0,
            help="📊 **CAPE = Cyclically Adjusted P/E Ratio** (Market Valuation)\n\n"
                 "What it is: Stock market 'expensiveness' smoothed over 10 years\n"
                 "• Low CAPE (15-20): Stocks cheap → Higher safe withdrawal rates\n"
                 "• High CAPE (30-40): Stocks expensive → Lower safe withdrawal rates\n\n"
                 "How we use it: Sets your initial withdrawal rate\n"
                 "Formula: Base 1.75% + 0.5 × (1/CAPE)\n\n"
                 "Current market: ~28-35 (check Robert Shiller's data)\n"
                 "Historical range: 5 (1920s) to 45+ (dot-com bubble)",
            key="wiz_cape_now_final"
        )
        # Immediately sync change back to wizard_params
        if cape_now != st.session_state.wizard_params.get('cape_now'):
            st.session_state.wizard_params['cape_now'] = cape_now

    # Summary of advanced settings
    st.markdown("### 📋 Advanced Settings Summary")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if college_enabled:
            total_college_cost = college_amount * college_years
            st.metric("Total College Cost", f"${total_college_cost:,.0f}")

    with col_b:
        if inheritance_amount > 0:
            st.metric("Inheritance", f"${inheritance_amount:,.0f}")

    with col_c:
        st.metric("Market Scenario", market_scenarios[market_regime].split(':')[0])

    # Show CAPE-based withdrawal rate calculation
    cape_now = st.session_state.wizard_params.get('cape_now', 28.0)
    start_capital = st.session_state.wizard_params.get('start_capital', 1000000)
    cape_wr = 3.2 + 0.5 * (1.0 / cape_now)
    initial_spending_cape = (cape_wr / 100) * start_capital

    st.info(
        f"📊 **CAPE-Based Calculation** (CAPE: {cape_now})\n"
        f"• Withdrawal Rate: {cape_wr:.2f}%\n"
        f"• Initial Year 1 Spending: ${initial_spending_cape:,.0f}\n"
        f"• Formula: 3.2% + 0.5 × (1/CAPE) - Conservative base rate"
    )

def step_review():
    """Final review and JSON generation step"""

    # Check if wizard was completed - but allow re-entry for parameter edits
    if st.session_state.get('wizard_completed', False):
        st.info("🔄 **Wizard was previously completed.** You can review and modify your configuration below.")
        # Allow user to continue using wizard instead of auto-redirecting

    st.markdown("""
    # 📋 Review & Generate Configuration

    Perfect! Let's review your retirement planning parameters and generate the configuration file
    for your Monte Carlo analysis.
    """)

    # Parameter summary
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 💰 Financial Summary")
        params = st.session_state.wizard_params

        st.write(f"**Starting Portfolio:** ${params['start_capital']:,}")
        st.write(f"**Annual Spending:** ${params['annual_spending']:,}")
        st.write(f"**Retirement Age:** {params['retirement_age']}")
        st.write(f"**Planning Horizon:** {params['horizon_years']} years")

        withdrawal_rate = (params['annual_spending'] / params['start_capital']) * 100
        st.write(f"**Initial Withdrawal Rate:** {withdrawal_rate:.1f}%")

        st.markdown("### 📊 Portfolio Allocation")
        st.write(f"**Stocks:** {params['equity_pct']:.1%}")
        st.write(f"**Bonds:** {params['bonds_pct']:.1%}")
        st.write(f"**Real Estate:** {params['real_estate_pct']:.1%}")
        st.write(f"**Cash:** {params['cash_pct']:.1%}")

        if params['glide_path']:
            st.write(f"**Glide Path:** -{params['equity_reduction_per_year']:.1%} equity/year")

    with col2:
        st.markdown("### 📈 Market Assumptions")

        st.write(f"**Stock Returns:** {params['equity_return']:.1%}")
        st.write(f"**Bond Returns:** {params['bonds_return']:.1%}")
        st.write(f"**RE Returns:** {params['real_estate_return']:.1%}")
        st.write(f"**Cash Returns:** {params['cash_return']:.1%}")
        st.write(f"**Inflation:** {params['inflation_rate']:.1%}")

        st.markdown("### 🤖 AI Analysis")
        if params['enable_ai']:
            st.write(f"**AI Enabled:** ✅ {params['gemini_model']}")
            if params['gemini_api_key']:
                st.write("**API Key:** ✅ Configured")
            else:
                st.write("**API Key:** ❌ Missing")
        else:
            st.write("**AI Enabled:** ❌ Disabled")

    # Generate visualization of portfolio allocation
    st.markdown("### 📊 Your Portfolio Allocation")
    fig_final = create_allocation_pie_chart(
        params['equity_pct'], params['bonds_pct'],
        params['real_estate_pct'], params['cash_pct']
    )
    st.plotly_chart(fig_final)

    # Generate JSON and provide download
    st.markdown("### 📁 Generate Configuration File")

    if st.button("🔄 Generate JSON Configuration"):
        try:
            # Convert wizard params to SimulationParams format
            json_params = convert_wizard_to_json(params)

            # Create download button
            json_str = json.dumps(json_params, indent=2)

            st.success("✅ Configuration generated successfully!")

            st.download_button(
                label="📥 Download Configuration File",
                data=json_str,
                file_name=f"retirement_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

            # Show preview
            with st.expander("👁️ Preview Configuration File"):
                st.json(json_params)

        except Exception as e:
            st.error(f"❌ Error generating configuration: {str(e)}")

    # Instructions for next steps
    st.markdown("### 🚀 Next Steps")

    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.info("""
        **🚀 Ready to Run Your Analysis:**

        Click **"Continue to Monte Carlo Analysis"** below to:
        1. **Automatically load** all your parameters
        2. **Review settings** in the sidebar (pre-configured)
        3. **Run simulation** with one click!

        *Optional: Download the JSON file above to save your configuration.*
        """)

    with col_b:
        st.success("""
        **✨ What You'll Get:**

        - Complete Monte Carlo analysis (thousands of scenarios)
        - Success rate calculations with confidence intervals
        - Interactive visualizations and charts
        - Year-by-year wealth projections
        - AI-powered insights and recommendations (if enabled)
        - Comprehensive downloadable reports
        - Interactive chat with AI about your results
        """)

        st.markdown("**⏱️ Runtime:** 10K simulations ≈ 5-15 seconds")

    # Start over option
    if st.button("🔄 Start Over", help="Reset wizard and start from beginning"):
        # Clear all wizard state
        for key in list(st.session_state.keys()):
            if key.startswith('wizard_'):
                del st.session_state[key]
        st.session_state.wizard_step = 0
        st.rerun()

# Function moved to io_utils.py to avoid circular imports

# Initialize wizard state only if needed
if 'wizard_step' not in st.session_state or 'wizard_params' not in st.session_state:
    initialize_wizard_state()

# Header
st.markdown("""
<div style='text-align: center; padding: 1rem; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;'>
    <h1 style='color: white; margin: 0;'>🧙‍♂️ Retirement Planning Wizard</h1>
    <p style='color: white; margin: 0; opacity: 0.9;'>Interactive setup for Monte Carlo retirement analysis</p>
</div>
""", unsafe_allow_html=True)

# Progress bar
create_progress_bar()

def convert_json_to_wizard_params(wizard_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert wizard JSON back to wizard parameters format.
    This is the inverse of convert_wizard_to_json().
    """
    wizard_params = {}

    # Basic parameters
    basic = wizard_json.get('basic_params', {})
    wizard_params.update({
        'start_capital': basic.get('start_capital', 2_500_000),
        'annual_spending': basic.get('annual_spending', 150_000),
        'retirement_age': basic.get('retirement_age', 65),
        'start_year': basic.get('start_year', 2025),
        'horizon_years': basic.get('horizon_years', 50),
    })

    # Asset allocation
    allocation = wizard_json.get('allocation', {})
    wizard_params.update({
        'equity_pct': allocation.get('equity_pct', 0.65),
        'bonds_pct': allocation.get('bonds_pct', 0.25),
        'real_estate_pct': allocation.get('real_estate_pct', 0.08),
        'cash_pct': allocation.get('cash_pct', 0.02),
        'glide_path': allocation.get('glide_path', False),
        'equity_reduction_per_year': allocation.get('equity_reduction_per_year', 0.005),
    })

    # Market assumptions
    market = wizard_json.get('market_assumptions', {})
    wizard_params.update({
        'equity_return': market.get('equity_return', 0.0742),
        'bonds_return': market.get('bonds_return', 0.0318),
        'real_estate_return': market.get('real_estate_return', 0.0563),
        'cash_return': market.get('cash_return', 0.0225),
        'equity_vol': market.get('equity_vol', 0.1734),
        'bonds_vol': market.get('bonds_vol', 0.0576),
        'real_estate_vol': market.get('real_estate_vol', 0.1612),
        'cash_vol': market.get('cash_vol', 0.0096),
        'inflation_rate': market.get('inflation_rate', 0.025),
    })

    # Taxes
    taxes = wizard_json.get('taxes', {})
    wizard_params.update({
        'state': taxes.get('state', 'CA'),
        'filing_status': taxes.get('filing_status', 'MFJ'),
        'standard_deduction': taxes.get('standard_deduction', 29200),
    })

    # Social Security
    ss = wizard_json.get('social_security', {})
    wizard_params.update({
        'ss_primary_benefit': ss.get('ss_primary_benefit', 40000),
        'ss_primary_start_age': ss.get('ss_primary_start_age', 67),
        'ss_spousal_benefit': ss.get('ss_spousal_benefit', 0),
        'ss_spousal_start_age': ss.get('ss_spousal_start_age', 67),
        'ss_funding_scenario': ss.get('ss_funding_scenario', 'conservative'),
    })

    # Guardrails
    guardrails = wizard_json.get('guardrails', {})
    wizard_params.update({
        'lower_guardrail': guardrails.get('lower_guardrail', 0.03),
        'upper_guardrail': guardrails.get('upper_guardrail', 0.05),
        'spending_adjustment': guardrails.get('spending_adjustment', 0.10),
        'max_spending_increase': guardrails.get('max_spending_increase', 0.10),
        'max_spending_decrease': guardrails.get('max_spending_decrease', 0.10),
    })

    # Advanced options
    advanced = wizard_json.get('advanced_options', {})
    wizard_params.update({
        'spending_floor_real': advanced.get('spending_floor_real', 120000),
        'spending_ceiling_real': advanced.get('spending_ceiling_real', 200000),
        'floor_end_year': advanced.get('floor_end_year', 2045),
        'college_enabled': advanced.get('college_enabled', False),
        'college_amount': advanced.get('college_amount', 70000),
        'college_years': advanced.get('college_years', 8),
        'college_start_year': advanced.get('college_start_year', 2032),
        'inheritance_amount': advanced.get('inheritance_amount', 0),
        'inheritance_year': advanced.get('inheritance_year', 2040),
    })

    # Simulation parameters
    simulation = wizard_json.get('simulation', {})
    wizard_params.update({
        'market_regime': simulation.get('market_regime', 'baseline'),
        'num_simulations': simulation.get('num_simulations', 10000),
        'cape_now': simulation.get('cape_now', 25),
    })

    # AI config
    ai = wizard_json.get('ai_config', {})
    wizard_params.update({
        'enable_ai': ai.get('enable_ai', False),
        'gemini_api_key': ai.get('gemini_api_key', ''),
        'gemini_model': ai.get('gemini_model', 'gemini-2.5-pro'),
    })

    # Cash flows (income and expense streams)
    cash_flows = wizard_json.get('cash_flows', {})
    wizard_params['income_streams'] = cash_flows.get('income_streams', [])
    wizard_params['expense_streams'] = cash_flows.get('expense_streams', [])

    return wizard_params


def convert_flat_to_wizard_params(flat_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert flat Monte Carlo parameters to wizard parameters format.
    This handles flat parameter files from Monte Carlo exports.
    """
    wizard_params = {}

    # Direct mappings for basic parameters
    wizard_params.update({
        'start_capital': flat_params.get('start_capital', 2_500_000),
        'annual_spending': flat_params.get('annual_spending', 150_000),
        'retirement_age': 65,  # Default, not stored in flat format
        'start_year': flat_params.get('start_year', 2025),
        'horizon_years': flat_params.get('horizon_years', 50),
    })

    # Asset allocation (simulation names to wizard names)
    wizard_params.update({
        'equity_pct': flat_params.get('w_equity', 0.65),
        'bonds_pct': flat_params.get('w_bonds', 0.25),
        'real_estate_pct': flat_params.get('w_real_estate', 0.08),
        'cash_pct': flat_params.get('w_cash', 0.02),
        'glide_path': flat_params.get('glide_path_enabled', False),
        'equity_reduction_per_year': flat_params.get('equity_reduction_per_year', 0.005),
    })

    # Market assumptions (simulation names to wizard names)
    wizard_params.update({
        'equity_return': flat_params.get('equity_mean', 0.0742),
        'bonds_return': flat_params.get('bonds_mean', 0.0318),
        'real_estate_return': flat_params.get('real_estate_mean', 0.0563),
        'cash_return': flat_params.get('cash_mean', 0.0225),
        'equity_vol': flat_params.get('equity_vol', 0.1734),
        'bonds_vol': flat_params.get('bonds_vol', 0.0576),
        'real_estate_vol': flat_params.get('real_estate_vol', 0.1612),
        'cash_vol': flat_params.get('cash_vol', 0.0096),
        'inflation_rate': flat_params.get('inflation_rate', 0.025),
    })

    # Taxes
    wizard_params.update({
        'state': 'CA',  # Default, state info not typically in flat params
        'filing_status': flat_params.get('filing_status', 'MFJ'),
        'standard_deduction': flat_params.get('standard_deduction', 29200),
    })

    # Social Security (simulation names to wizard names)
    wizard_params.update({
        'ss_primary_benefit': flat_params.get('ss_annual_benefit', 40000),
        'ss_primary_start_age': flat_params.get('ss_start_age', 67),
        'ss_spousal_benefit': flat_params.get('spouse_ss_annual_benefit', 0),
        'ss_spousal_start_age': flat_params.get('spouse_ss_start_age', 67),
        'ss_funding_scenario': flat_params.get('ss_benefit_scenario', 'conservative'),
    })

    # Guardrails (simulation names to wizard names)
    wizard_params.update({
        'lower_guardrail': flat_params.get('lower_wr', 0.03),
        'upper_guardrail': flat_params.get('upper_wr', 0.05),
        'spending_adjustment': flat_params.get('adjustment_pct', 0.10),
        'max_spending_increase': 0.10,  # Default
        'max_spending_decrease': 0.10,  # Default
    })

    # Advanced options
    wizard_params.update({
        'spending_floor_real': flat_params.get('spending_floor_real', 120000),
        'spending_ceiling_real': flat_params.get('spending_ceiling_real', 200000),
        'floor_end_year': flat_params.get('floor_end_year', 2045),
        'college_enabled': flat_params.get('college_enabled', False),
        'college_amount': flat_params.get('college_base_amount', 70000),
        'college_years': 8,  # Default
        'college_start_year': flat_params.get('college_start_year', 2032),
        'inheritance_amount': flat_params.get('inherit_amount', 0),
        'inheritance_year': flat_params.get('inherit_year', 2040),
    })

    # Simulation parameters
    wizard_params.update({
        'market_regime': flat_params.get('regime', 'baseline'),
        'num_simulations': flat_params.get('num_sims', 10000),
        'cape_now': flat_params.get('cape_now', 25),
    })

    # AI config - not typically in flat params
    wizard_params.update({
        'enable_ai': False,
        'gemini_api_key': '',
        'gemini_model': 'gemini-2.5-pro',
    })

    # Cash flows - simplified, flat params typically don't have complex cash flows
    wizard_params['income_streams'] = []
    wizard_params['expense_streams'] = []

    return wizard_params


st.markdown("---")

# Check for jump to simulation request (must be before step routing)
if st.session_state.get('jump_to_sim_requested', False):
    # Sync current widget values to wizard_params before transition
    sync_widget_values_to_wizard_params()
    st.session_state.wizard_completed = True
    st.session_state.parameters_loaded = False  # Force re-transfer on Monte Carlo page
    st.session_state.jump_to_sim_requested = False  # Reset flag
    st.write("🚀 Jumping to simulation...")
    st.switch_page("pages/monte_carlo.py")

# Route to appropriate step
current_step_id = WIZARD_STEPS[st.session_state.wizard_step]['id']

if current_step_id == 'welcome':
    step_welcome()
elif current_step_id == 'basics':
    step_basics()
elif current_step_id == 'allocation':
    step_allocation()
elif current_step_id == 'market':
    step_market()
elif current_step_id == 'taxes':
    step_taxes()
elif current_step_id == 'social_security':
    step_social_security()
elif current_step_id == 'guardrails':
    step_guardrails()
elif current_step_id == 'cash_flows':
    step_cash_flows()
elif current_step_id == 'ai_setup':
    step_ai_setup()
elif current_step_id == 'advanced':
    step_advanced()
elif current_step_id == 'review':
    step_review()
# Steps under construction
else:
    st.info(f"Step '{current_step_id}' is under construction!")
    st.markdown("Coming soon: Interactive parameter setup with beautiful visualizations")

st.markdown("---")

# Navigation
create_navigation_buttons()

# Add multipage navigation after wizard completion
if st.session_state.wizard_step == len(WIZARD_STEPS) - 1:  # On review step
    st.markdown("---")
    st.markdown("### 🚀 Ready for Analysis!")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📊 Continue to Monte Carlo Analysis", type="primary"):
            # Sync current widget values to wizard_params before completion
            sync_widget_values_to_wizard_params()
            # Mark wizard as completed and transfer parameters
            st.session_state.wizard_completed = True
            st.session_state.parameters_loaded = False  # Force re-transfer on Monte Carlo page
            st.switch_page("pages/monte_carlo.py")