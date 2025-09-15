"""
Configuration Utilities for Retirement Planning Wizard
Pure utility functions for configuration management and default parameters.
Extracted from wizard.py to improve code organization and testability.
"""

import json
import os
from typing import Dict, Any, List


def load_ui_config() -> Dict[str, Any]:
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


def save_ui_config(config: Dict[str, Any]) -> None:
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


# Wizard step configuration
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


def get_default_wizard_params() -> Dict[str, Any]:
    """Get default wizard parameters configuration"""
    return {
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
        'standard_deduction': 29_200,

        # Social Security
        'ss_primary_benefit': 40000,
        'ss_primary_start_age': 67,
        'ss_spousal_benefit': 0,
        'ss_spousal_start_age': 67,
        'ss_funding_scenario': 'moderate',

        # Guardrails
        'lower_guardrail': 0.05,
        'upper_guardrail': 0.032,
        'spending_adjustment': 0.10,
        'max_spending_increase': 0.10,
        'max_spending_decrease': 0.10,

        # Advanced options
        'spending_floor_real': 120000,
        'spending_ceiling_real': 200000,
        'floor_end_year': 2045,
        'college_enabled': False,
        'college_amount': 70000,
        'college_years': 8,
        'college_start_year': 2032,
        'inheritance_amount': 0,
        'inheritance_year': 2040,

        # Simulation parameters
        'market_regime': 'baseline',
        'num_simulations': 10000,
        'cape_now': 25,

        # Income and expense streams
        'income_streams': [],
        'expense_streams': [],

        # AI configuration - loaded from UI config
        'enable_ai': False,
        'gemini_api_key': '',
        'gemini_model': 'gemini-2.5-pro',
    }


def get_wizard_widget_mappings() -> Dict[str, str]:
    """Get mapping from Streamlit widget keys to wizard parameter keys"""
    return {
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

        # Advanced Options
        'wiz_college_enabled': 'college_enabled',
        'wiz_college_amount': 'college_amount',
        'wiz_college_years': 'college_years',
        'wiz_college_start_year': 'college_start_year',
        'wiz_inheritance_amount': 'inheritance_amount',
        'wiz_inheritance_year': 'inheritance_year',

        # Simulation
        'wiz_market_regime': 'market_regime',
        'wiz_num_simulations': 'num_simulations',

        # AI Setup
        'wiz_enable_ai': 'enable_ai',
        'wiz_api_key': 'gemini_api_key',
        'wiz_selected_model': 'gemini_model',
        'wiz_gemini_api_key': 'gemini_api_key',
        'wiz_gemini_model': 'gemini_model',
        'wiz_cape_now_final': 'cape_now',
        'wiz_spending_method': 'spending_method',
    }


def get_widget_keys_for_immediate_sync() -> List[str]:
    """Get list of widget keys that should be synced immediately when changed"""
    return [
        'wiz_start_capital', 'wiz_annual_spending', 'wiz_retirement_age',
        'wiz_start_year', 'wiz_horizon_years', 'wiz_equity_pct', 'wiz_bonds_pct',
        'wiz_real_estate_pct', 'wiz_cash_pct', 'wiz_glide_path', 'wiz_equity_reduction',
        'wiz_equity_return', 'wiz_bonds_return', 'wiz_real_estate_return', 'wiz_cash_return',
        'wiz_equity_vol', 'wiz_bonds_vol', 'wiz_real_estate_vol', 'wiz_inflation_rate',
        'wiz_selected_state', 'wiz_filing_status', 'wiz_standard_deduction',
        'wiz_ss_primary_benefit', 'wiz_ss_primary_start_age', 'wiz_ss_spousal_benefit',
        'wiz_ss_spousal_start_age', 'wiz_ss_funding_scenario', 'wiz_custom_reduction',
        'wiz_reduction_start_year', 'wiz_lower_guardrail', 'wiz_upper_guardrail',
        'wiz_spending_adjustment', 'wiz_max_increase', 'wiz_max_decrease',
        'wiz_spending_floor', 'wiz_spending_ceiling', 'wiz_floor_end_year',
        'wiz_college_enabled', 'wiz_college_amount', 'wiz_college_years',
        'wiz_college_start_year', 'wiz_inheritance_amount', 'wiz_inheritance_year',
        'wiz_market_regime', 'wiz_num_simulations', 'wiz_enable_ai',
        'wiz_gemini_api_key', 'wiz_gemini_model'
    ]