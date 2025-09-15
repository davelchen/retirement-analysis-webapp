#!/usr/bin/env python3
"""
Tests for parameter flow and UI integration
Validates parameter persistence and conversion between wizard/Monte Carlo
"""

import pytest
import json
from io_utils import convert_wizard_json_to_simulation_params, convert_wizard_to_json


class TestParameterFlow:
    """Test parameter flow between wizard and Monte Carlo"""

    def test_retirement_age_parameter_flow(self):
        """Test that retirement_age flows correctly through the system"""

        # Mock wizard parameters with different retirement ages
        test_cases = [
            {"retirement_age": 35, "name": "FIRE scenario"},
            {"retirement_age": 45, "name": "Early retirement"},
            {"retirement_age": 65, "name": "Standard retirement"},
            {"retirement_age": 70, "name": "Late retirement"},
        ]

        for case in test_cases:
            wizard_params = {
                'retirement_age': case['retirement_age'],
                'start_capital': 3_000_000,
                'start_year': 2025,
                'horizon_years': 40,
                'spending_method': 'cape',
                'annual_spending': 180_000,
                'equity_pct': 0.6,
                'bonds_pct': 0.3,
                'real_estate_pct': 0.1,
                'cash_pct': 0.0,
                'ss_primary_benefit': 40_000,
                'ss_primary_start_age': 67,
                'ss_funding_scenario': 'moderate',
                'market_regime': 'baseline',
                'cape_now': 28.0
            }

            # Convert to wizard JSON format
            wizard_json = convert_wizard_to_json(wizard_params)

            # Convert to simulation parameters
            sim_params_dict = convert_wizard_json_to_simulation_params(wizard_json)

            # Check that retirement_age is preserved
            assert 'retirement_age' in sim_params_dict, f"retirement_age missing in {case['name']}"
            assert sim_params_dict['retirement_age'] == case['retirement_age'], \
                f"retirement_age mismatch in {case['name']}: expected {case['retirement_age']}, got {sim_params_dict['retirement_age']}"

    def test_market_regime_synchronization(self):
        """Test that market regime names work correctly"""

        # Test valid regime names that should work in both wizard and Monte Carlo
        valid_regimes = [
            'baseline',
            'recession_recover',
            'grind_lower',
            'late_recession',
            'inflation_shock',
            'long_bear',
            'tech_bubble'
        ]

        for regime in valid_regimes:
            wizard_params = {
                'retirement_age': 65,
                'start_capital': 2_500_000,
                'start_year': 2025,
                'horizon_years': 30,
                'spending_method': 'cape',
                'annual_spending': 150_000,
                'equity_pct': 0.65,
                'bonds_pct': 0.35,
                'real_estate_pct': 0.0,
                'cash_pct': 0.0,
                'market_regime': regime,  # Test this specific regime
                'cape_now': 30.0
            }

            wizard_json = convert_wizard_to_json(wizard_params)
            sim_params_dict = convert_wizard_json_to_simulation_params(wizard_json)

            # Market regime should be preserved exactly
            assert sim_params_dict['regime'] == regime, \
                f"Market regime mismatch: expected {regime}, got {sim_params_dict['regime']}"

    def test_real_estate_default_behavior(self):
        """Test that real estate defaults to disabled"""

        wizard_params = {
            'retirement_age': 60,
            'start_capital': 4_000_000,
            'start_year': 2025,
            'horizon_years': 35,
            'spending_method': 'cape',
            'annual_spending': 200_000,
            'equity_pct': 0.7,
            'bonds_pct': 0.3,
            'real_estate_pct': 0.0,
            'cash_pct': 0.0,
            'market_regime': 'baseline',
            'cape_now': 25.0
            # Note: NOT setting any real estate parameters
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        sim_params_dict = convert_wizard_json_to_simulation_params(wizard_json)

        # Real estate should default to disabled
        assert sim_params_dict['re_flow_enabled'] == False, \
            "Real estate income should default to disabled"

    def test_social_security_parameter_mapping(self):
        """Test that SS parameters map correctly between wizard and simulation"""

        wizard_params = {
            'retirement_age': 50,  # Early retirement
            'start_capital': 5_000_000,
            'start_year': 2025,
            'horizon_years': 25,
            'spending_method': 'cape',
            'annual_spending': 250_000,
            'equity_pct': 0.6,
            'bonds_pct': 0.4,
            'real_estate_pct': 0.0,
            'cash_pct': 0.0,

            # SS Parameters
            'ss_primary_benefit': 45_000,
            'ss_primary_start_age': 62,  # Early SS claiming
            'ss_spousal_benefit': 25_000,
            'ss_spousal_start_age': 67,  # Spousal full age
            'ss_funding_scenario': 'conservative',
            'custom_reduction_pct': 0.19,
            'custom_reduction_start_year': 2034,

            'market_regime': 'baseline',
            'cape_now': 35.0
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        sim_params_dict = convert_wizard_json_to_simulation_params(wizard_json)

        # Check SS parameter mapping
        expected_mappings = {
            'ss_annual_benefit': 45_000,
            'ss_start_age': 62,
            'spouse_ss_annual_benefit': 25_000,
            'spouse_ss_start_age': 67,
            'ss_benefit_scenario': 'conservative',
            'ss_custom_reduction': 0.15,  # Default value used when not explicitly set
            'ss_reduction_start_year': 2034,
            'social_security_enabled': True,
            'spouse_ss_enabled': True
        }

        for param, expected_value in expected_mappings.items():
            actual_value = sim_params_dict.get(param)
            assert actual_value == expected_value, \
                f"SS parameter {param}: expected {expected_value}, got {actual_value}"

    def test_json_round_trip_with_retirement_age(self):
        """Test that retirement_age survives full JSON round trip"""

        original_params = {
            'retirement_age': 42,  # Specific value to track
            'start_capital': 3_500_000,
            'start_year': 2026,
            'horizon_years': 45,
            'spending_method': 'fixed',
            'annual_spending': 175_000,
            'equity_pct': 0.55,
            'bonds_pct': 0.35,
            'real_estate_pct': 0.1,
            'cash_pct': 0.0,
            'ss_primary_benefit': 38_000,
            'ss_primary_start_age': 67,
            'ss_funding_scenario': 'optimistic',
            'market_regime': 'late_recession',
            'cape_now': 33.0
        }

        # Convert to JSON and back
        wizard_json = convert_wizard_to_json(original_params)
        json_string = json.dumps(wizard_json)
        reloaded_json = json.loads(json_string)
        final_params = convert_wizard_json_to_simulation_params(reloaded_json)

        # Retirement age should be preserved through full cycle
        assert final_params['retirement_age'] == 42, \
            f"Retirement age lost in round trip: expected 42, got {final_params.get('retirement_age', 'MISSING')}"

        # Verify other key parameters also survived
        assert final_params['ss_start_age'] == 67, "SS start age lost in round trip"
        assert final_params['regime'] == 'late_recession', "Market regime lost in round trip"