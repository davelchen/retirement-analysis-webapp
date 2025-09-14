"""
IO utilities for saving/loading parameters and exporting simulation results.
Handles JSON serialization of parameters and CSV exports of results.
"""
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import asdict
import io
from datetime import datetime

from simulation import SimulationParams, SimulationResults


def _safe_numeric_convert(value: Any, default: float) -> float:
    """Safely convert a value to a numeric type, using default if invalid"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _safe_ss_benefit_check(value: Any) -> bool:
    """Safely check if SS benefit value is positive (handles invalid types)"""
    try:
        return bool(float(value) > 0) if value is not None else False
    except (ValueError, TypeError):
        return False


def params_to_dict(params: SimulationParams) -> Dict[str, Any]:
    """
    Convert SimulationParams to dictionary for JSON serialization.
    
    Args:
        params: SimulationParams object
        
    Returns:
        Dictionary representation
    """
    return asdict(params)


def dict_to_params(param_dict: Dict[str, Any]) -> SimulationParams:
    """
    Convert dictionary to SimulationParams object.

    Args:
        param_dict: Dictionary with parameter values

    Returns:
        SimulationParams object
    """
    # Create a copy to avoid modifying the original
    filtered_dict = param_dict.copy()

    # Filter out UI-only parameters that don't belong in SimulationParams
    ui_only_params = {
        'inflation_rate',  # Used for display calculations only
        'currency_view',   # UI display preference (Real/Nominal)
        'capital_preset',  # UI dropdown selection
        'use_custom_capital',  # UI toggle
        'state'  # State tax selection (handled separately in tax calculations)
    }

    for param in ui_only_params:
        filtered_dict.pop(param, None)

    # Handle tax_brackets which might be None or list of tuples
    if 'tax_brackets' in filtered_dict and filtered_dict['tax_brackets'] is not None:
        # Convert list of lists back to list of tuples
        filtered_dict['tax_brackets'] = [tuple(bracket) for bracket in filtered_dict['tax_brackets']]

    return SimulationParams(**filtered_dict)


def save_parameters_json(params: SimulationParams, filepath: str) -> None:
    """
    Save simulation parameters to JSON file.
    
    Args:
        params: SimulationParams object to save
        filepath: Path to save JSON file
    """
    param_dict = params_to_dict(params)
    
    # Convert tuples to lists for JSON serialization
    if param_dict.get('tax_brackets'):
        param_dict['tax_brackets'] = [list(bracket) for bracket in param_dict['tax_brackets']]
    
    with open(filepath, 'w') as f:
        json.dump(param_dict, f, indent=2)


def load_parameters_json(filepath: str) -> SimulationParams:
    """
    Load simulation parameters from JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        SimulationParams object
    """
    with open(filepath, 'r') as f:
        param_dict = json.load(f)
    
    return dict_to_params(param_dict)


def create_parameters_download_json(params: SimulationParams) -> str:
    """
    Create JSON string for downloading parameters.
    
    Args:
        params: SimulationParams object
        
    Returns:
        JSON string
    """
    param_dict = params_to_dict(params)
    
    # Convert tuples to lists for JSON serialization
    if param_dict.get('tax_brackets'):
        param_dict['tax_brackets'] = [list(bracket) for bracket in param_dict['tax_brackets']]
    
    return json.dumps(param_dict, indent=2)


def parse_parameters_upload_json(json_string: str) -> SimulationParams:
    """
    Parse uploaded JSON string to SimulationParams.

    Args:
        json_string: JSON string with parameters

    Returns:
        SimulationParams object
    """
    param_dict = json.loads(json_string)

    # Check if this is wizard-generated JSON (has nested structure)
    if 'basic_params' in param_dict and 'allocation' in param_dict:
        param_dict = convert_wizard_json_to_simulation_params(param_dict)

    return dict_to_params(param_dict)


def convert_wizard_to_json(wizard_params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert wizard parameters to JSON format compatible with Monte Carlo analysis"""

    # Basic financial parameters
    json_config = {
        "basic_params": {
            "start_capital": wizard_params.get('start_capital', 2_500_000),
            "annual_spending": wizard_params.get('annual_spending', 120_000),
            "spending_method": wizard_params.get('spending_method', 'cape'),
            "retirement_age": wizard_params.get('retirement_age', 65),
            "start_year": wizard_params.get('start_year', 2025),
            "horizon_years": wizard_params.get('horizon_years', 50)
        },
        "allocation": {
            "equity_pct": wizard_params.get('equity_pct', 0.65),
            "bonds_pct": wizard_params.get('bonds_pct', 0.25),
            "real_estate_pct": wizard_params.get('real_estate_pct', 0.08),
            "cash_pct": wizard_params.get('cash_pct', 0.02),
            "glide_path": wizard_params.get('glide_path', False),
            "equity_reduction_per_year": wizard_params.get('equity_reduction_per_year', 0.01)
        },
        "market_assumptions": {
            "equity_return": wizard_params.get('equity_return', 0.0742),
            "bonds_return": wizard_params.get('bonds_return', 0.0318),
            "real_estate_return": wizard_params.get('real_estate_return', 0.0563),
            "cash_return": wizard_params.get('cash_return', 0.0225),
            "equity_vol": wizard_params.get('equity_vol', 0.1734),
            "bonds_vol": wizard_params.get('bonds_vol', 0.0576),
            "real_estate_vol": wizard_params.get('real_estate_vol', 0.1612),
            "cash_vol": 0.0096,  # Default cash volatility
            "inflation_rate": wizard_params.get('inflation_rate', 0.025)
        },
        "taxes": {
            "state": wizard_params.get('state', 'CA'),
            "filing_status": wizard_params.get('filing_status', 'MFJ'),
            "standard_deduction": wizard_params.get('standard_deduction', 29200)
        },
        "social_security": {
            "ss_primary_benefit": wizard_params.get('ss_primary_benefit', 40000),
            "ss_primary_start_age": wizard_params.get('ss_primary_start_age', 67),
            "ss_spousal_benefit": wizard_params.get('ss_spousal_benefit', 0),
            "ss_spousal_start_age": wizard_params.get('ss_spousal_start_age', 67),
            "ss_funding_scenario": wizard_params.get('ss_funding_scenario', 'moderate')
        },
        "guardrails": {
            "lower_guardrail": wizard_params.get('lower_guardrail', 0.03),
            "upper_guardrail": wizard_params.get('upper_guardrail', 0.05),
            "spending_adjustment": wizard_params.get('spending_adjustment', 0.1),
            "max_spending_increase": wizard_params.get('max_spending_increase', 0.05),
            "max_spending_decrease": wizard_params.get('max_spending_decrease', 0.2)
        },
        "simulation": {
            "num_simulations": wizard_params.get('num_simulations', 10000),
            "market_regime": wizard_params.get('market_regime', 'baseline'),
            "cape_now": wizard_params.get('cape_now', 28.0)
        },
        "ai_config": {
            "enable_ai_analysis": wizard_params.get('enable_ai', False),
            "gemini_api_key": wizard_params.get('gemini_api_key', ''),
            "gemini_model": wizard_params.get('gemini_model', 'gemini-2.5-pro')
        },
        "cash_flows": {
            "income_streams": wizard_params.get('income_streams', []),
            "expense_streams": wizard_params.get('expense_streams', [])
        },
        "advanced_options": {
            "college_enabled": wizard_params.get('college_enabled', False),
            "college_amount": wizard_params.get('college_amount', 75000),
            "college_years": wizard_params.get('college_years', 8),
            "college_start_year": wizard_params.get('college_start_year', 2032),
            "inheritance_amount": wizard_params.get('inheritance_amount', 0),
            "inheritance_year": wizard_params.get('inheritance_year', 2040),
            "spending_floor_real": wizard_params.get('spending_floor_real', 120000),
            "spending_ceiling_real": wizard_params.get('spending_ceiling_real', 200000),
            "floor_end_year": wizard_params.get('floor_end_year', 2045)
        },
        "metadata": {
            "created_by": "Retirement Planning Wizard",
            "created_date": datetime.now().isoformat(),
            "wizard_version": "1.0"
        }
    }

    return json_config


def convert_wizard_json_to_simulation_params(wizard_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert wizard-generated nested JSON to flat SimulationParams format.

    Args:
        wizard_json: Nested JSON structure from wizard

    Returns:
        Flat parameter dictionary compatible with SimulationParams
    """
    basic = wizard_json.get('basic_params', {})
    allocation = wizard_json.get('allocation', {})
    market = wizard_json.get('market_assumptions', {})
    taxes = wizard_json.get('taxes', {})
    ss = wizard_json.get('social_security', {})
    guardrails = wizard_json.get('guardrails', {})
    simulation = wizard_json.get('simulation', {})
    cash_flows = wizard_json.get('cash_flows', {})

    # Core parameters
    params = {
        'start_capital': basic.get('start_capital', 2_500_000),
        'horizon_years': basic.get('horizon_years', 50),
        'start_year': basic.get('start_year', 2025),

        # Asset allocation - convert from wizard names to simulation names
        'w_equity': allocation.get('equity_pct', 0.65),
        'w_bonds': allocation.get('bonds_pct', 0.25),
        'w_real_estate': allocation.get('real_estate_pct', 0.08),
        'w_cash': allocation.get('cash_pct', 0.02),

        # Glide path
        'glide_path_enabled': allocation.get('glide_path', False),
        'equity_reduction_per_year': allocation.get('equity_reduction_per_year', 0.005),

        # Market assumptions - convert from wizard names to simulation names
        'equity_mean': market.get('equity_return', 0.0742),
        'bonds_mean': market.get('bonds_return', 0.0318),
        'real_estate_mean': market.get('real_estate_return', 0.0563),
        'cash_mean': market.get('cash_return', 0.0225),
        'equity_vol': market.get('equity_vol', 0.1734),
        'bonds_vol': market.get('bonds_vol', 0.0576),
        'real_estate_vol': market.get('real_estate_vol', 0.1612),
        'cash_vol': market.get('cash_vol', 0.0096),

        # Inflation rate (critical parameter that's not in SimulationParams)
        'inflation_rate': market.get('inflation_rate', 0.025),

        # Taxes
        'filing_status': taxes.get('filing_status', 'MFJ'),
        'tax_brackets': taxes.get('brackets', [(0, 0.10), (94_300, 0.22), (201_000, 0.24)]),
        'standard_deduction': taxes.get('standard_deduction', 29_200),

        # Social Security - convert parameter names (with type safety)
        'social_security_enabled': _safe_ss_benefit_check(ss.get('ss_primary_benefit', 0)),
        'ss_annual_benefit': _safe_numeric_convert(ss.get('ss_primary_benefit', 40000), 40000),
        'ss_start_age': ss.get('ss_primary_start_age', 67),
        'ss_benefit_scenario': ss.get('ss_funding_scenario', 'moderate'),
        'spouse_ss_enabled': _safe_ss_benefit_check(ss.get('ss_spousal_benefit', 0)),
        'spouse_ss_annual_benefit': _safe_numeric_convert(ss.get('ss_spousal_benefit', 0), 0),
        'spouse_ss_start_age': ss.get('ss_spousal_start_age', 67),

        # Custom Social Security scenario parameters
        'ss_custom_reduction': ss.get('custom_reduction_pct', 0.15),
        'ss_reduction_start_year': ss.get('custom_reduction_start_year', 2034),

        # Spending bounds
        'spending_floor_real': guardrails.get('spending_floor_real', 160_000),
        'spending_ceiling_real': guardrails.get('spending_ceiling_real', 275_000),
        'floor_end_year': guardrails.get('floor_end_year', 2041),

        # Guardrails - convert parameter names (fixed defaults: lower < upper)
        'lower_wr': guardrails.get('lower_guardrail', 0.03),
        'upper_wr': guardrails.get('upper_guardrail', 0.05),
        'adjustment_pct': guardrails.get('spending_adjustment', 0.10),

        # Simulation parameters
        'num_sims': simulation.get('num_simulations', 10_000),
        'regime': simulation.get('market_regime', 'baseline'),
        'cape_now': simulation.get('cape_now', 28.0),
        'random_seed': simulation.get('random_seed', None),

        # Initial spending configuration
        'initial_base_spending': _get_wizard_initial_spending(basic),
        'fixed_annual_spending': _get_wizard_fixed_spending(basic),

        # Handle cash flows - convert from wizard structure
        'expense_streams': _convert_wizard_expense_streams(cash_flows.get('expense_streams', [])),
    }

    # Handle other income streams - convert to individual parameters
    income_streams = cash_flows.get('income_streams', [])
    params['other_income_amount'] = 0.0
    params['other_income_start_year'] = 2025
    params['other_income_years'] = 0

    # Use first income stream if available
    if income_streams:
        first_income = income_streams[0]
        params['other_income_amount'] = first_income.get('amount', 0.0)
        params['other_income_start_year'] = first_income.get('start_year', 2025)
        params['other_income_years'] = first_income.get('duration', 0)

    # Handle inheritance - look for inheritance in expense streams
    params['inherit_amount'] = 0
    params['inherit_year'] = 2025

    for expense in cash_flows.get('expense_streams', []):
        if 'inheritance' in expense.get('description', '').lower():
            # Inheritance is negative expense
            params['inherit_amount'] = abs(expense.get('amount', 0))
            params['inherit_year'] = expense.get('start_year', 2025)
            break

    # College and real estate - extract from advanced options if present
    advanced = wizard_json.get('advanced_options', {})
    params['college_enabled'] = advanced.get('college_enabled', True)
    params['college_base_amount'] = advanced.get('college_amount', 100_000)
    params['college_start_year'] = advanced.get('college_start_year', 2032)
    params['college_end_year'] = advanced.get('college_start_year', 2032) + advanced.get('college_years', 4) - 1
    params['college_growth_real'] = advanced.get('college_inflation', 0.013)

    params['re_flow_enabled'] = advanced.get('re_flow_enabled', True)
    params['re_flow_preset'] = advanced.get('re_flow_preset', 'ramp')
    params['re_flow_start_year'] = advanced.get('re_income_start_year', 2026)
    params['re_flow_year1_amount'] = 50_000
    params['re_flow_year2_amount'] = 60_000
    params['re_flow_steady_amount'] = 75_000
    params['re_flow_delay_years'] = 0

    # Override inheritance if specified in advanced_options (takes precedence over expense streams)
    if 'inheritance_amount' in advanced and advanced['inheritance_amount'] > 0:
        params['inherit_amount'] = advanced['inheritance_amount']
        params['inherit_year'] = advanced.get('inheritance_year', 2040)

    # Custom regime parameters
    params['custom_equity_shock_year'] = 0
    params['custom_equity_shock_return'] = -0.20
    params['custom_shock_duration'] = 1
    params['custom_recovery_years'] = 2
    params['custom_recovery_equity_return'] = 0.02

    return params


def _convert_wizard_expense_streams(wizard_expense_streams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert wizard expense stream format to simulation format.

    Args:
        wizard_expense_streams: List of expense streams from wizard

    Returns:
        List of expense streams compatible with SimulationParams
    """
    converted_streams = []

    for stream in wizard_expense_streams:
        # Skip inheritance entries (handled separately)
        if 'inheritance' in stream.get('description', '').lower():
            continue

        converted_stream = {
            'amount': stream.get('amount', 0),
            'start_year': stream.get('start_year', 2025),
            'duration': stream.get('duration', 1),
            'description': stream.get('description', 'Expense')
        }
        converted_streams.append(converted_stream)

    return converted_streams


def export_terminal_wealth_csv(terminal_wealth: np.ndarray) -> str:
    """
    Export terminal wealth results to CSV string.
    
    Args:
        terminal_wealth: Array of terminal wealth values
        
    Returns:
        CSV string
    """
    df = pd.DataFrame({
        'simulation': range(1, len(terminal_wealth) + 1),
        'terminal_wealth': terminal_wealth
    })
    
    return df.to_csv(index=False)


def export_percentile_bands_csv(years: np.ndarray, 
                               percentiles: Dict[str, np.ndarray],
                               currency_format: str = "real") -> str:
    """
    Export wealth percentile bands to CSV string.
    
    Args:
        years: Array of years
        percentiles: Dictionary with 'p10', 'p50', 'p90' arrays
        currency_format: "real" or "nominal" for column naming
        
    Returns:
        CSV string
    """
    df = pd.DataFrame({
        'year': years,
        f'p10_wealth_{currency_format}': percentiles['p10'],
        f'p50_wealth_{currency_format}': percentiles['p50'],
        f'p90_wealth_{currency_format}': percentiles['p90']
    })
    
    return df.to_csv(index=False)


def export_year_by_year_csv(details: Dict[str, List], 
                           currency_format: str = "real") -> str:
    """
    Export year-by-year details table to CSV string.
    
    Args:
        details: Dictionary with year-by-year details
        currency_format: "real" or "nominal" for column naming
        
    Returns:
        CSV string
    """
    # Create DataFrame from details dictionary
    df = pd.DataFrame(details)
    
    # Rename columns to include currency format
    currency_columns = [
        'start_assets', 'base_spending', 'adjusted_base_spending',
        'college_topup', 'one_times', 're_income', 'other_income',
        'taxable_income', 'taxes', 'net_need', 'gross_withdrawal',
        'growth', 'inheritance', 'end_assets'
    ]
    
    rename_dict = {}
    for col in currency_columns:
        if col in df.columns:
            rename_dict[col] = f'{col}_{currency_format}'
    
    df = df.rename(columns=rename_dict)
    
    return df.to_csv(index=False)


def create_summary_report(params: SimulationParams,
                         results: SimulationResults,
                         currency_format: str = "real") -> Dict[str, Any]:
    """
    Create comprehensive summary report of simulation.
    
    Args:
        params: Simulation parameters
        results: Simulation results
        currency_format: "real" or "nominal"
        
    Returns:
        Dictionary with summary information
    """
    terminal_stats = {
        'mean': np.mean(results.terminal_wealth),
        'median': np.median(results.terminal_wealth),
        'std': np.std(results.terminal_wealth),
        'p10': np.percentile(results.terminal_wealth, 10),
        'p25': np.percentile(results.terminal_wealth, 25),
        'p75': np.percentile(results.terminal_wealth, 75),
        'p90': np.percentile(results.terminal_wealth, 90),
        'min': np.min(results.terminal_wealth),
        'max': np.max(results.terminal_wealth)
    }
    
    # Probability thresholds
    prob_thresholds = {
        'prob_below_0': np.mean(results.terminal_wealth <= 0),
        'prob_below_1m': np.mean(results.terminal_wealth < 1_000_000),
        'prob_below_5m': np.mean(results.terminal_wealth < 5_000_000),
        'prob_below_10m': np.mean(results.terminal_wealth < 10_000_000),
        'prob_below_15m': np.mean(results.terminal_wealth < 15_000_000)
    }
    
    # Guardrail statistics
    guardrail_stats = {
        'mean_hits': np.mean(results.guardrail_hits),
        'median_hits': np.median(results.guardrail_hits),
        'max_hits': np.max(results.guardrail_hits),
        'pct_with_hits': np.mean(results.guardrail_hits > 0)
    }
    
    # Depletion analysis
    depletion_stats = {
        'success_rate': results.success_rate,
        'failure_rate': 1 - results.success_rate,
        'avg_years_to_depletion': np.mean(results.years_depleted[results.years_depleted > 0]) 
                                 if np.any(results.years_depleted > 0) else None
    }
    
    report = {
        'simulation_info': {
            'num_simulations': params.num_sims,
            'horizon_years': params.horizon_years,
            'start_capital': params.start_capital,
            'regime': params.regime,
            'currency_format': currency_format
        },
        'terminal_wealth_stats': terminal_stats,
        'probability_analysis': prob_thresholds,
        'guardrail_analysis': guardrail_stats,
        'depletion_analysis': depletion_stats,
        'allocation': {
            'equity': params.w_equity,
            'bonds': params.w_bonds,
            'real_estate': params.w_real_estate,
            'cash': params.w_cash
        }
    }
    
    return report


def export_summary_report_json(report: Dict[str, Any]) -> str:
    """
    Export summary report as JSON string.
    
    Args:
        report: Summary report dictionary
        
    Returns:
        JSON string
    """
    return json.dumps(report, indent=2, default=str)


def create_batch_export_zip(params: SimulationParams,
                           results: SimulationResults,
                           percentiles: Dict[str, np.ndarray],
                           years: np.ndarray) -> io.BytesIO:
    """
    Create ZIP file containing all export files.
    
    Args:
        params: Simulation parameters
        results: Simulation results  
        percentiles: Wealth percentiles over time
        years: Array of years
        
    Returns:
        BytesIO object containing ZIP file
    """
    import zipfile
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Parameters JSON
        params_json = create_parameters_download_json(params)
        zip_file.writestr('parameters.json', params_json)
        
        # Terminal wealth CSV
        terminal_csv = export_terminal_wealth_csv(results.terminal_wealth)
        zip_file.writestr('terminal_wealth.csv', terminal_csv)
        
        # Percentile bands CSV (real)
        percentiles_csv = export_percentile_bands_csv(years, percentiles, "real")
        zip_file.writestr('percentile_bands_real.csv', percentiles_csv)
        
        # Year-by-year details CSV (real)
        details_csv = export_year_by_year_csv(results.median_path_details, "real")
        zip_file.writestr('year_by_year_real.csv', details_csv)
        
        # Summary report JSON
        report = create_summary_report(params, results, "real")
        report_json = export_summary_report_json(report)
        zip_file.writestr('summary_report.json', report_json)
    
    zip_buffer.seek(0)
    return zip_buffer


def validate_parameters_json(json_string: str) -> tuple[bool, str]:
    """
    Validate uploaded parameters JSON.
    
    Args:
        json_string: JSON string to validate
        
    Returns:
        (is_valid, error_message)
    """
    try:
        param_dict = json.loads(json_string)
        
        # Check required fields
        required_fields = ['start_capital', 'w_equity', 'w_bonds', 'w_real_estate', 'w_cash']
        for field in required_fields:
            if field not in param_dict:
                return False, f"Missing required field: {field}"
        
        # Check allocation weights sum to 1
        weights = [param_dict.get('w_equity', 0), param_dict.get('w_bonds', 0),
                  param_dict.get('w_real_estate', 0), param_dict.get('w_cash', 0)]
        if abs(sum(weights) - 1.0) > 1e-6:
            return False, f"Allocation weights must sum to 1.0, got {sum(weights):.6f}"
        
        # Validate ranges
        if param_dict.get('start_capital', 0) <= 0:
            return False, "Start capital must be positive"
        
        if param_dict.get('horizon_years', 0) <= 0:
            return False, "Horizon years must be positive"
        
        if param_dict.get('num_sims', 0) <= 0:
            return False, "Number of simulations must be positive"
        
        # Try to create SimulationParams object
        dict_to_params(param_dict)
        
        return True, ""
        
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        return False, f"Parameter validation error: {str(e)}"


def format_currency(value: float, 
                   currency_format: str = "real",
                   precision: int = 0) -> str:
    """
    Format currency values for display.
    
    Args:
        value: Numeric value to format
        currency_format: "real" or "nominal"  
        precision: Number of decimal places
        
    Returns:
        Formatted string
    """
    if abs(value) >= 1_000_000:
        formatted = f"${value/1_000_000:.{precision}f}M"
    elif abs(value) >= 1_000:
        formatted = f"${value/1_000:.{precision}f}K"
    else:
        formatted = f"${value:.{precision}f}"
    
    # Add currency format indicator
    suffix = " (real)" if currency_format == "real" else " (nominal)"
    return formatted + suffix


def unified_json_loader_ui(uploaded_file, target_format="monte_carlo"):
    """
    Unified JSON loading UI that works for both Wizard and Monte Carlo.

    Args:
        uploaded_file: Streamlit file upload object
        target_format: "wizard" or "monte_carlo" - determines output format

    Returns:
        dict: Parameters in the requested format, or None if not loaded yet
    """
    import streamlit as st
    import json
    from typing import Dict, Any, Optional

    if uploaded_file is None:
        return None

    try:
        # Read the uploaded file
        json_data = json.loads(uploaded_file.read())

        # Show preview with key parameters
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✅ Loaded configuration with {len(json_data)} parameter sections")

            # Auto-detect format and show preview
            if 'basic_params' in json_data:
                # Wizard format
                st.caption("📋 **Format:** Wizard export")
                basic = json_data['basic_params']
                capital = basic.get('start_capital', 'N/A')
                spending = basic.get('annual_spending', 'N/A')
                horizon = basic.get('horizon_years', 'N/A')
            else:
                # Flat format (Monte Carlo export)
                st.caption("📋 **Format:** Monte Carlo export")
                capital = json_data.get('start_capital', 'N/A')
                spending = json_data.get('annual_spending', 'N/A')
                horizon = json_data.get('horizon_years', 'N/A')

            # Show key parameter preview
            if isinstance(capital, (int, float)):
                st.write(f"**Starting Capital:** ${capital:,.0f}")
            else:
                st.write(f"**Starting Capital:** {capital}")

            if isinstance(spending, (int, float)):
                st.write(f"**Annual Spending:** ${spending:,.0f}")
            else:
                st.write(f"**Annual Spending:** {spending}")

            st.write(f"**Horizon:** {horizon} years")

        with col2:
            load_button_key = f"load_unified_params_{target_format}"
            if st.button("Load These Parameters", type="primary", key=load_button_key):
                # Convert to target format
                if target_format == "wizard":
                    return _convert_to_wizard_format(json_data)
                else:  # monte_carlo
                    return _convert_to_monte_carlo_format(json_data)

        return None  # No load button clicked yet

    except json.JSONDecodeError:
        st.error("Invalid JSON file. Please upload a valid parameter file.")
        return None
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None


def _convert_to_wizard_format(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert any JSON format to wizard parameters format"""
    if 'basic_params' in json_data:
        # It's already wizard format, convert back to wizard params
        return _convert_json_to_wizard_params(json_data)
    else:
        # It's flat format, convert to wizard params
        return _convert_flat_to_wizard_params(json_data)


def _convert_to_monte_carlo_format(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert any JSON format to Monte Carlo parameters format"""
    if 'basic_params' in json_data:
        # It's wizard format, convert to flat Monte Carlo format
        return convert_wizard_json_to_simulation_params(json_data)
    else:
        # It's already flat format, return as-is (with validation)
        return json_data


def _convert_json_to_wizard_params(wizard_json: Dict[str, Any]) -> Dict[str, Any]:
    """Convert wizard JSON back to wizard parameters format"""
    wizard_params = {}

    # Basic parameters
    basic = wizard_json.get('basic_params', {})
    wizard_params.update({
        'start_capital': basic.get('start_capital', 2_500_000),
        'annual_spending': basic.get('annual_spending', 150_000),
        'horizon_years': basic.get('horizon_years', 50),
        'w_equity': basic.get('w_equity', 0.65),
        'w_bonds': basic.get('w_bonds', 0.25),
        'w_real_estate': basic.get('w_real_estate', 0.08),
        'w_cash': basic.get('w_cash', 0.02),
    })

    # Tax parameters
    tax = wizard_json.get('tax_params', {})
    wizard_params.update({
        'state': tax.get('state', 'CA'),
        'filing_status': tax.get('filing_status', 'married_filing_jointly'),
    })

    # Social Security
    ss = wizard_json.get('social_security', {})
    wizard_params.update({
        'ss_benefits_enabled': ss.get('ss_benefits_enabled', True),
        'ss_annual_benefit': ss.get('ss_annual_benefit', 40000),
        'ss_start_age': ss.get('ss_start_age', 67),
        'ss_funding_scenario': ss.get('ss_funding_scenario', 'moderate'),
        'spouse_ss_benefits_enabled': ss.get('spouse_ss_benefits_enabled', False),
        'spouse_ss_annual_benefit': ss.get('spouse_ss_annual_benefit', 20000),
        'spouse_ss_start_age': ss.get('spouse_ss_start_age', 67),
    })

    # Simulation parameters
    simulation = wizard_json.get('simulation', {})
    wizard_params.update({
        'num_simulations': simulation.get('num_simulations', 10000),
        'market_regime': simulation.get('market_regime', 'baseline'),
        'cape_now': simulation.get('cape_now', 28.0)
    })

    # AI config
    ai_config = wizard_json.get('ai_config', {})
    wizard_params.update({
        'enable_ai': ai_config.get('enable_ai_analysis', False),
        'gemini_api_key': ai_config.get('gemini_api_key', ''),
        'gemini_model': ai_config.get('gemini_model', 'gemini-2.5-pro')
    })

    # Cash flows
    cash_flows = wizard_json.get('cash_flows', {})
    wizard_params['income_streams'] = cash_flows.get('income_streams', [])
    wizard_params['expense_streams'] = cash_flows.get('expense_streams', [])

    # Advanced options
    advanced = wizard_json.get('advanced_options', {})
    wizard_params.update({
        'college_enabled': advanced.get('college_enabled', False),
        'college_amount': advanced.get('college_amount', 75000),
        'college_years': advanced.get('college_years', 8),
        'college_start_year': advanced.get('college_start_year', 2032),
    })

    return wizard_params


def _convert_flat_to_wizard_params(flat_params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert flat Monte Carlo parameters to wizard parameters format"""
    wizard_params = {}

    # Direct mappings for basic parameters
    wizard_params.update({
        'start_capital': flat_params.get('start_capital', 2_500_000),
        'annual_spending': flat_params.get('annual_spending', 150_000),
        'horizon_years': flat_params.get('horizon_years', 50),
        'w_equity': flat_params.get('w_equity', 0.65),
        'w_bonds': flat_params.get('w_bonds', 0.25),
        'w_real_estate': flat_params.get('w_real_estate', 0.08),
        'w_cash': flat_params.get('w_cash', 0.02),
    })

    # Tax and state
    wizard_params.update({
        'state': flat_params.get('state', 'CA'),
        'filing_status': flat_params.get('filing_status', 'married_filing_jointly'),
    })

    # Social Security
    wizard_params.update({
        'ss_benefits_enabled': flat_params.get('ss_benefits_enabled', True),
        'ss_annual_benefit': flat_params.get('ss_annual_benefit', 40000),
        'ss_start_age': flat_params.get('ss_start_age', 67),
        'ss_funding_scenario': flat_params.get('ss_funding_scenario', 'moderate'),
        'spouse_ss_benefits_enabled': flat_params.get('spouse_ss_benefits_enabled', False),
        'spouse_ss_annual_benefit': flat_params.get('spouse_ss_annual_benefit', 20000),
        'spouse_ss_start_age': flat_params.get('spouse_ss_start_age', 67),
    })

    # Simulation
    wizard_params.update({
        'num_simulations': flat_params.get('num_sims', 10000),
        'market_regime': flat_params.get('regime', 'baseline'),
        'cape_now': flat_params.get('cape_now', 28.0)
    })

    # Convert expense streams (flat format may have different structure)
    wizard_params['income_streams'] = []  # Would need to reconstruct from flat format
    wizard_params['expense_streams'] = flat_params.get('expense_streams', [])

    # College expenses (convert from flat format)
    wizard_params.update({
        'college_enabled': flat_params.get('college_enabled', False),
        'college_amount': flat_params.get('college_base_amount', 75000),
        'college_years': flat_params.get('college_end_year', 2041) - flat_params.get('college_start_year', 2032),
        'college_start_year': flat_params.get('college_start_year', 2032),
    })

    return wizard_params


def _get_wizard_initial_spending(basic: Dict[str, Any]) -> Optional[float]:
    """Extract initial spending from wizard basic parameters based on spending method"""
    spending_method = basic.get('spending_method', 'cape')
    if spending_method == 'fixed':
        return basic.get('annual_spending', None)
    else:
        # For CAPE-based or manual, return None to use CAPE calculation
        return None


def _get_wizard_fixed_spending(basic: Dict[str, Any]) -> Optional[float]:
    """Extract fixed annual spending from wizard basic parameters"""
    spending_method = basic.get('spending_method', 'cape')
    if spending_method == 'fixed':
        return basic.get('annual_spending', None)
    else:
        return None