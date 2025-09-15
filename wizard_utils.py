"""
Wizard Parameter Conversion Utilities
Parameter conversion functions for the retirement planning wizard interface.
Extracted from wizard.py to improve code organization and maintainability.
"""

from typing import Dict, Any


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
        'lower_guardrail': guardrails.get('lower_guardrail', 0.05),
        'upper_guardrail': guardrails.get('upper_guardrail', 0.032),
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
        'lower_guardrail': flat_params.get('lower_wr', 0.05),
        'upper_guardrail': flat_params.get('upper_wr', 0.032),
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