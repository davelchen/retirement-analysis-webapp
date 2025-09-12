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

from simulation import SimulationParams, SimulationResults


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
    # Handle tax_brackets which might be None or list of tuples
    if 'tax_brackets' in param_dict and param_dict['tax_brackets'] is not None:
        # Convert list of lists back to list of tuples
        param_dict['tax_brackets'] = [tuple(bracket) for bracket in param_dict['tax_brackets']]
    
    return SimulationParams(**param_dict)


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
    return dict_to_params(param_dict)


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