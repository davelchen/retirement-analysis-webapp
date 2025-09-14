"""
Unit tests for IO utilities (save/load parameters, exports).
"""
import pytest
import json
import numpy as np
import pandas as pd
from io import StringIO
from simulation import SimulationParams, SimulationResults
from io_utils import (
    params_to_dict, dict_to_params, create_parameters_download_json,
    parse_parameters_upload_json, export_terminal_wealth_csv,
    export_percentile_bands_csv, export_year_by_year_csv,
    validate_parameters_json, format_currency
)


class TestParameterSerialization:
    """Test parameter save/load functionality"""
    
    def test_params_to_dict_basic(self):
        """Test converting params to dictionary"""
        params = SimulationParams(
            start_capital=1_000_000,
            w_equity=0.6,
            w_bonds=0.2,
            w_real_estate=0.15,
            w_cash=0.05,
            filing_status="Single"
        )
        
        param_dict = params_to_dict(params)
        
        assert param_dict['start_capital'] == 1_000_000
        assert param_dict['w_equity'] == 0.6
        assert param_dict['filing_status'] == "Single"
        assert isinstance(param_dict, dict)
    
    def test_dict_to_params_basic(self):
        """Test converting dictionary to params"""
        param_dict = {
            'start_capital': 2_000_000,
            'w_equity': 0.7,
            'w_bonds': 0.2,
            'w_real_estate': 0.1,
            'w_cash': 0.0,
            'filing_status': 'MFJ',
            'tax_brackets': [[0, 0.10], [50000, 0.22]]
        }
        
        params = dict_to_params(param_dict)
        
        assert params.start_capital == 2_000_000
        assert params.w_equity == 0.7
        assert params.filing_status == 'MFJ'
        assert params.tax_brackets == [(0, 0.10), (50000, 0.22)]
    
    def test_round_trip_conversion(self):
        """Test that params->dict->params preserves values"""
        original_params = SimulationParams(
            start_capital=5_000_000,
            w_equity=0.8,
            w_bonds=0.1,
            w_real_estate=0.1,
            w_cash=0.0,
            horizon_years=30,
            num_sims=1000,
            cape_now=32.5,
            other_income_amount=25_000,
            other_income_start_year=2030,
            other_income_years=10
        )
        
        # Round trip conversion
        param_dict = params_to_dict(original_params)
        restored_params = dict_to_params(param_dict)
        
        # Check key fields
        assert restored_params.start_capital == original_params.start_capital
        assert restored_params.w_equity == original_params.w_equity
        assert restored_params.horizon_years == original_params.horizon_years
        assert restored_params.cape_now == original_params.cape_now
        assert restored_params.other_income_amount == original_params.other_income_amount
    
    def test_json_serialization(self):
        """Test JSON serialization and parsing"""
        params = SimulationParams(start_capital=3_000_000)
        
        # Create JSON string
        json_str = create_parameters_download_json(params)
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed['start_capital'] == 3_000_000
        
        # Parse back to params
        restored_params = parse_parameters_upload_json(json_str)
        assert restored_params.start_capital == 3_000_000
    
    def test_tax_brackets_json_handling(self):
        """Test tax brackets are properly handled in JSON"""
        params = SimulationParams(
            filing_status="Single",
            tax_brackets=[(0, 0.10), (47150, 0.22), (100500, 0.24)]
        )
        
        json_str = create_parameters_download_json(params)
        parsed = json.loads(json_str)
        
        # Should be converted to lists for JSON
        assert parsed['tax_brackets'] == [[0, 0.10], [47150, 0.22], [100500, 0.24]]
        
        # Should convert back to tuples
        restored_params = parse_parameters_upload_json(json_str)
        assert restored_params.tax_brackets == [(0, 0.10), (47150, 0.22), (100500, 0.24)]

    def test_social_security_json_handling(self):
        """Test Social Security parameters are properly handled in JSON"""
        params = SimulationParams(
            social_security_enabled=True,
            ss_annual_benefit=50_000,
            ss_start_age=70,
            ss_benefit_scenario="conservative",
            ss_custom_reduction=0.15,
            ss_reduction_start_year=2035
        )

        json_str = create_parameters_download_json(params)
        parsed = json.loads(json_str)

        # Verify all Social Security fields are serialized
        assert parsed['social_security_enabled'] == True
        assert parsed['ss_annual_benefit'] == 50_000
        assert parsed['ss_start_age'] == 70
        assert parsed['ss_benefit_scenario'] == "conservative"
        assert parsed['ss_custom_reduction'] == 0.15
        assert parsed['ss_reduction_start_year'] == 2035

        # Should properly deserialize
        restored_params = parse_parameters_upload_json(json_str)
        assert restored_params.social_security_enabled == True
        assert restored_params.ss_annual_benefit == 50_000
        assert restored_params.ss_start_age == 70
        assert restored_params.ss_benefit_scenario == "conservative"
        assert restored_params.ss_custom_reduction == 0.15
        assert restored_params.ss_reduction_start_year == 2035

    def test_social_security_json_round_trip_with_defaults(self):
        """Test Social Security JSON serialization with default values"""
        params = SimulationParams()  # Use defaults

        json_str = create_parameters_download_json(params)
        restored_params = parse_parameters_upload_json(json_str)

        # Verify defaults are preserved
        assert restored_params.social_security_enabled == True
        assert restored_params.ss_annual_benefit == 40_000
        assert restored_params.ss_start_age == 67
        assert restored_params.ss_benefit_scenario == "moderate"
        assert restored_params.ss_custom_reduction == 0.10
        assert restored_params.ss_reduction_start_year == 2034


class TestCSVExports:
    """Test CSV export functionality"""
    
    def test_terminal_wealth_csv(self):
        """Test terminal wealth CSV export"""
        terminal_wealth = np.array([1_000_000, 2_000_000, 3_000_000])
        csv_str = export_terminal_wealth_csv(terminal_wealth)
        
        # Parse CSV to verify format
        df = pd.read_csv(StringIO(csv_str))
        
        assert list(df.columns) == ['simulation', 'terminal_wealth']
        assert len(df) == 3
        assert df['simulation'].tolist() == [1, 2, 3]
        assert df['terminal_wealth'].tolist() == [1_000_000, 2_000_000, 3_000_000]
    
    def test_percentile_bands_csv_real(self):
        """Test percentile bands CSV export (real)"""
        years = np.array([2026, 2027, 2028])
        percentiles = {
            'p10': np.array([1_000_000, 1_100_000, 1_200_000]),
            'p50': np.array([1_500_000, 1_650_000, 1_800_000]),
            'p90': np.array([2_000_000, 2_200_000, 2_400_000])
        }
        
        csv_str = export_percentile_bands_csv(years, percentiles, "real")
        df = pd.read_csv(StringIO(csv_str))
        
        expected_cols = ['year', 'p10_wealth_real', 'p50_wealth_real', 'p90_wealth_real']
        assert list(df.columns) == expected_cols
        assert df['year'].tolist() == [2026, 2027, 2028]
        assert df['p50_wealth_real'].tolist() == [1_500_000, 1_650_000, 1_800_000]
    
    def test_percentile_bands_csv_nominal(self):
        """Test percentile bands CSV export (nominal)"""
        years = np.array([2026, 2027])
        percentiles = {
            'p10': np.array([1_000_000, 1_100_000]),
            'p50': np.array([1_500_000, 1_650_000]),
            'p90': np.array([2_000_000, 2_200_000])
        }
        
        csv_str = export_percentile_bands_csv(years, percentiles, "nominal")
        df = pd.read_csv(StringIO(csv_str))
        
        expected_cols = ['year', 'p10_wealth_nominal', 'p50_wealth_nominal', 'p90_wealth_nominal']
        assert list(df.columns) == expected_cols
    
    def test_year_by_year_csv(self):
        """Test year-by-year details CSV export"""
        details = {
            'years': [2026, 2027],
            'start_assets': [8_000_000, 7_500_000],
            'gross_withdrawal': [300_000, 320_000],
            'taxes': [50_000, 55_000],
            'end_assets': [7_500_000, 7_200_000],
            'floor_applied': [False, False],
            'guardrail_action': ['none', 'up']
        }
        
        csv_str = export_year_by_year_csv(details, "real")
        df = pd.read_csv(StringIO(csv_str))
        
        # Check that currency columns are renamed
        assert 'start_assets_real' in df.columns
        assert 'gross_withdrawal_real' in df.columns
        assert 'taxes_real' in df.columns
        
        # Check non-currency columns unchanged
        assert 'years' in df.columns
        assert 'floor_applied' in df.columns
        assert 'guardrail_action' in df.columns
        
        assert len(df) == 2
        assert df['years'].tolist() == [2026, 2027]


class TestParameterValidation:
    """Test parameter validation"""
    
    def test_valid_parameters(self):
        """Test validation of valid parameters"""
        valid_params = {
            'start_capital': 5_000_000,
            'w_equity': 0.6,
            'w_bonds': 0.2,
            'w_real_estate': 0.15,
            'w_cash': 0.05,
            'horizon_years': 30,
            'num_sims': 1000
        }
        
        json_str = json.dumps(valid_params)
        is_valid, error = validate_parameters_json(json_str)
        
        assert is_valid == True
        assert error == ""
    
    def test_invalid_json(self):
        """Test validation of invalid JSON"""
        invalid_json = '{"start_capital": 5000000, "w_equity": 0.6,'  # Missing closing brace
        
        is_valid, error = validate_parameters_json(invalid_json)
        
        assert is_valid == False
        assert "Invalid JSON" in error
    
    def test_missing_required_field(self):
        """Test validation with missing required field"""
        incomplete_params = {
            'start_capital': 5_000_000,
            'w_equity': 0.6,
            'w_bonds': 0.2,
            # Missing w_real_estate and w_cash
        }
        
        json_str = json.dumps(incomplete_params)
        is_valid, error = validate_parameters_json(json_str)
        
        assert is_valid == False
        assert "Missing required field" in error
    
    def test_invalid_allocation_weights(self):
        """Test validation with invalid allocation weights"""
        invalid_params = {
            'start_capital': 5_000_000,
            'w_equity': 0.6,
            'w_bonds': 0.3,  # Sum = 1.1 > 1.0
            'w_real_estate': 0.15,
            'w_cash': 0.05,
            'horizon_years': 30,
            'num_sims': 1000
        }
        
        json_str = json.dumps(invalid_params)
        is_valid, error = validate_parameters_json(json_str)
        
        assert is_valid == False
        assert "Allocation weights must sum to 1.0" in error
    
    def test_negative_start_capital(self):
        """Test validation with negative start capital"""
        invalid_params = {
            'start_capital': -1_000_000,  # Negative
            'w_equity': 0.6,
            'w_bonds': 0.2,
            'w_real_estate': 0.15,
            'w_cash': 0.05,
            'horizon_years': 30,
            'num_sims': 1000
        }
        
        json_str = json.dumps(invalid_params)
        is_valid, error = validate_parameters_json(json_str)
        
        assert is_valid == False
        assert "Start capital must be positive" in error
    
    def test_invalid_horizon_years(self):
        """Test validation with invalid horizon years"""
        invalid_params = {
            'start_capital': 5_000_000,
            'w_equity': 0.6,
            'w_bonds': 0.2,
            'w_real_estate': 0.15,
            'w_cash': 0.05,
            'horizon_years': 0,  # Invalid
            'num_sims': 1000
        }

        json_str = json.dumps(invalid_params)
        is_valid, error = validate_parameters_json(json_str)

        assert is_valid == False
        assert "Horizon years must be positive" in error

    def test_percentile_bands_csv_array_length_mismatch(self):
        """Test that percentile bands CSV export fails gracefully with mismatched array lengths"""
        # This test reproduces the bug we fixed where years array (40) didn't match percentiles (41)
        # This happens because wealth_paths includes initial wealth + horizon years

        # Scenario: 40 horizon years but 41 wealth data points (includes t=0)
        years_40 = np.arange(2026, 2066)  # 40 years: 2026-2065
        percentiles_41 = {
            'p10': np.random.random(41) * 1_000_000,  # 41 data points (t=0 to t=40)
            'p50': np.random.random(41) * 2_000_000,
            'p90': np.random.random(41) * 3_000_000
        }

        # This should raise a ValueError due to length mismatch
        with pytest.raises(ValueError, match="All arrays must be of the same length"):
            export_percentile_bands_csv(years_40, percentiles_41, "real")

    def test_percentile_bands_csv_correct_array_sizing(self):
        """Test that percentile bands CSV export works with correctly sized arrays"""
        # Corrected scenario: Match years array to actual data points
        # This represents the fix where we use results.wealth_paths.shape[1] for sizing

        # Simulate 40 horizon years with 41 wealth data points (includes t=0)
        start_year = 2026
        num_wealth_points = 41  # This is what wealth_paths.shape[1] would return

        # Generate years array that matches the wealth data points
        years = np.arange(start_year, start_year + num_wealth_points)  # 41 years: 2026-2066
        percentiles = {
            'p10': np.random.random(num_wealth_points) * 1_000_000,  # 41 data points
            'p50': np.random.random(num_wealth_points) * 2_000_000,
            'p90': np.random.random(num_wealth_points) * 3_000_000
        }

        # This should work without errors
        csv_str = export_percentile_bands_csv(years, percentiles, "real")
        df = pd.read_csv(StringIO(csv_str))

        # Verify the DataFrame structure
        expected_cols = ['year', 'p10_wealth_real', 'p50_wealth_real', 'p90_wealth_real']
        assert list(df.columns) == expected_cols
        assert len(df) == num_wealth_points
        assert df['year'].tolist() == years.tolist()

        # Verify all arrays have the same length
        assert len(df['p10_wealth_real']) == len(df['p50_wealth_real']) == len(df['p90_wealth_real'])
        assert len(df) == len(years)


class TestCurrencyFormatting:
    """Test currency formatting utility"""
    
    def test_format_millions(self):
        """Test formatting values in millions"""
        assert format_currency(5_000_000, "real", 1) == "$5.0M (real)"
        assert format_currency(12_500_000, "nominal", 2) == "$12.50M (nominal)"
    
    def test_format_thousands(self):
        """Test formatting values in thousands"""
        assert format_currency(250_000, "real", 0) == "$250K (real)"
        assert format_currency(75_500, "nominal", 1) == "$75.5K (nominal)"
    
    def test_format_small_values(self):
        """Test formatting small values"""
        assert format_currency(500, "real", 0) == "$500 (real)"
        assert format_currency(1_50, "nominal", 2) == "$150.00 (nominal)"
    
    def test_format_negative_values(self):
        """Test formatting negative values"""
        assert format_currency(-2_000_000, "real", 1) == "$-2.0M (real)"
        assert format_currency(-50_000, "nominal", 0) == "$-50K (nominal)"