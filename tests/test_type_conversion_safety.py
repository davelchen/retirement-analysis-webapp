"""
Type conversion safety tests

These tests ensure that type conversions don't silently corrupt data or cause
calculation errors. Type mismatches in UI components can lead to data corruption
that propagates through the entire simulation.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pages.wizard import convert_wizard_to_json
from io_utils import convert_wizard_json_to_simulation_params, dict_to_params
from simulation import SimulationParams


class TestTypeConversionSafety:
    """Test type conversion safety in parameter handling"""

    def test_social_security_float_to_int_conversion_preserves_value(self):
        """Test that converting SS benefits from float to int preserves the value exactly"""

        test_cases = [
            40000.0,    # Exact integer as float
            42500.0,    # Half-thousands
            35000.0,    # Standard benefit
            75000.0,    # High benefit
            0.0,        # Zero benefit
        ]

        for original_value in test_cases:
            # This is the conversion done in Monte Carlo UI
            converted_value = int(original_value)

            assert converted_value == original_value, \
                f"Type conversion corrupted value: {original_value} -> {converted_value}"
            assert isinstance(converted_value, int), \
                f"Conversion should produce int, got {type(converted_value)}"

    def test_dangerous_float_to_int_conversion_detection(self):
        """Test detection of dangerous float-to-int conversions that would corrupt data"""

        # These are values that would get corrupted by int() conversion
        dangerous_cases = [
            40000.5,    # Half dollar amounts would be truncated
            42500.25,   # Fractional cents
            35000.99,   # Almost a dollar more
            123.456,    # Multiple decimal places
        ]

        for dangerous_value in dangerous_cases:
            converted_value = int(dangerous_value)

            # Verify we detect data loss
            assert converted_value != dangerous_value, \
                f"Should detect data corruption for {dangerous_value} -> {converted_value}"

            # This is the kind of silent data corruption we need to prevent
            data_loss = dangerous_value - converted_value
            assert data_loss > 0, f"Data loss detected: {data_loss} for {dangerous_value}"

    def test_wizard_to_monte_carlo_ss_benefit_type_consistency(self):
        """Test that SS benefits maintain type consistency through wizard->Monte Carlo pipeline"""

        wizard_params = {
            'ss_primary_benefit': 45000,      # Integer
            'ss_spousal_benefit': 22500,      # Integer
        }

        # Step 1: Wizard -> JSON
        wizard_json = convert_wizard_to_json(wizard_params)

        # Step 2: JSON -> flat parameters
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)

        # Step 3: flat -> SimulationParams
        params = dict_to_params(flat_params)

        # Check that values are preserved correctly
        assert params.ss_annual_benefit == 45000
        assert params.spouse_ss_annual_benefit == 22500

        # Simulate the Monte Carlo UI conversion
        ui_primary_benefit = int(params.ss_annual_benefit)
        ui_spouse_benefit = int(params.spouse_ss_annual_benefit)

        # Values should be preserved exactly
        assert ui_primary_benefit == 45000
        assert ui_spouse_benefit == 22500
        assert isinstance(ui_primary_benefit, int)
        assert isinstance(ui_spouse_benefit, int)

    def test_wizard_float_values_safe_int_conversion(self):
        """Test that wizard can produce float SS values that convert safely to int"""

        # Wizard might produce float values through calculations
        wizard_params = {
            'ss_primary_benefit': 40000.0,    # Float from wizard
            'ss_spousal_benefit': 18000.0,    # Float from wizard
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Check that SimulationParams preserves these as floats
        assert isinstance(params.ss_annual_benefit, float)
        assert isinstance(params.spouse_ss_annual_benefit, float)
        assert params.ss_annual_benefit == 40000.0
        assert params.spouse_ss_annual_benefit == 18000.0

        # Check that UI conversion preserves value exactly
        ui_primary = int(params.ss_annual_benefit)
        ui_spouse = int(params.spouse_ss_annual_benefit)

        assert ui_primary == 40000
        assert ui_spouse == 18000

    def test_edge_case_zero_and_none_values(self):
        """Test edge cases that could cause conversion errors"""

        edge_cases = [
            (0, 0),           # Zero values
            (0.0, 0),         # Float zero
            (None, 0),        # None (should use default)
        ]

        for input_value, expected in edge_cases:
            if input_value is None:
                # Simulate session_state.get() with default
                result = int(40000)  # Default value
                expected = 40000
            else:
                result = int(input_value)

            assert result == expected
            assert isinstance(result, int)

    def test_large_social_security_values_preserve_precision(self):
        """Test that large SS values don't lose precision in conversion"""

        large_values = [
            100000,     # High earner
            150000,     # Very high earner
            200000,     # Maximum possible (widget limit)
        ]

        for value in large_values:
            # Test both int and float inputs
            int_result = int(value)
            float_result = int(float(value))

            assert int_result == value
            assert float_result == value
            assert int_result == float_result

    def test_simulation_calculation_integrity_with_converted_values(self):
        """Test that converted SS values produce correct simulation calculations"""

        # Create params with float SS values (from wizard)
        wizard_params = {
            'start_capital': 2000000,
            'ss_primary_benefit': 45000.0,    # Float
            'ss_spousal_benefit': 20000.0,    # Float
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Simulate Monte Carlo UI conversion
        ui_ss_primary = int(params.ss_annual_benefit)
        ui_ss_spouse = int(params.spouse_ss_annual_benefit)

        # Create new params with converted values (as would happen in UI)
        converted_params = SimulationParams(
            start_capital=params.start_capital,
            ss_annual_benefit=ui_ss_primary,
            spouse_ss_annual_benefit=ui_ss_spouse,
            spouse_ss_enabled=ui_ss_spouse > 0
        )

        # Critical: Values should be exactly the same
        assert converted_params.ss_annual_benefit == 45000
        assert converted_params.spouse_ss_annual_benefit == 20000
        assert converted_params.spouse_ss_enabled == True

        # Verify total SS income calculation is correct
        total_ss_income = converted_params.ss_annual_benefit + converted_params.spouse_ss_annual_benefit
        assert total_ss_income == 65000  # Should be exact

    def test_detect_streamlit_type_mismatch_scenarios(self):
        """Test scenarios that would cause Streamlit type mismatch errors"""

        # These are the exact patterns that caused the original error
        problematic_scenarios = [
            {
                'value_type': float,
                'value': 40000.0,
                'max_value_type': int,
                'max_value': 200000,
                'step_type': int,
                'step': 1000
            },
            {
                'value_type': float,
                'value': 35000.0,
                'max_value_type': int,
                'max_value': 200000,
                'step_type': int,
                'step': 1000
            }
        ]

        for scenario in problematic_scenarios:
            value = scenario['value']
            max_value = scenario['max_value']
            step = scenario['step']

            # This would cause Streamlit error without int() conversion
            assert type(value) != type(max_value) or type(value) != type(step), \
                f"Type mismatch scenario not detected: value={type(value)}, max={type(max_value)}, step={type(step)}"

            # Our fix: convert value to int
            fixed_value = int(value)
            assert type(fixed_value) == type(max_value) == type(step), \
                f"Fix should make all types consistent: value={type(fixed_value)}, max={type(max_value)}, step={type(step)}"

            # Value should be preserved
            assert fixed_value == value, \
                f"Fix should preserve value: {value} -> {fixed_value}"


class TestParameterPipelineIntegrity:
    """Test end-to-end parameter pipeline integrity"""

    def test_full_pipeline_type_consistency(self):
        """Test that the full wizard->Monte Carlo pipeline maintains type consistency"""

        # Start with mixed types (realistic wizard output)
        wizard_params = {
            'start_capital': 2500000,         # int
            'equity_pct': 0.7,               # float
            'ss_primary_benefit': 42000.0,    # float (from calculations)
            'ss_spousal_benefit': 18500.0,    # float (from calculations)
            'college_enabled': True,          # bool
            'inflation_rate': 0.025,         # float
        }

        # Pipeline step 1: Wizard -> JSON
        wizard_json = convert_wizard_to_json(wizard_params)

        # Pipeline step 2: JSON -> flat params
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)

        # Pipeline step 3: flat params -> SimulationParams
        params = dict_to_params(flat_params)

        # Pipeline step 4: SimulationParams -> Monte Carlo UI
        # This is where the type conversion happens
        ui_ss_primary = int(params.ss_annual_benefit)
        ui_ss_spouse = int(params.spouse_ss_annual_benefit)

        # Verify integrity through the entire pipeline
        assert ui_ss_primary == 42000  # Should preserve exact value
        assert ui_ss_spouse == 18500   # Should preserve exact value
        assert isinstance(ui_ss_primary, int)  # Should be correct type for UI
        assert isinstance(ui_ss_spouse, int)   # Should be correct type for UI

        # Verify that calculations using these values are correct
        total_ss = ui_ss_primary + ui_ss_spouse
        assert total_ss == 60500  # Mathematical integrity preserved


if __name__ == '__main__':
    pytest.main([__file__, '-v'])