"""
Unit tests for wizard-to-Monte Carlo transition functionality

These tests ensure that the parameter handoff between the wizard and Monte Carlo
analysis pages works correctly, maintaining data integrity and completeness.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules
from pages.wizard import convert_wizard_to_json
from io_utils import convert_wizard_json_to_simulation_params, dict_to_params
from simulation import SimulationParams


class TestWizardToMonteCarloTransition:
    """Test the complete transition from wizard to Monte Carlo analysis"""

    def test_complete_parameter_transition_flow(self):
        """Test the complete flow from wizard params to Monte Carlo session state"""

        # Create comprehensive wizard parameters
        wizard_params = {
            'start_capital': 3000000,
            'annual_spending': 150000,
            'retirement_age': 62,
            'start_year': 2026,
            'horizon_years': 40,
            'equity_pct': 0.70,
            'bonds_pct': 0.20,
            'real_estate_pct': 0.08,
            'cash_pct': 0.02,
            'glide_path': True,
            'equity_reduction_per_year': 0.005,
            'equity_return': 0.08,
            'bonds_return': 0.03,
            'real_estate_return': 0.06,
            'cash_return': 0.02,
            'equity_vol': 0.18,
            'bonds_vol': 0.04,
            'real_estate_vol': 0.15,
            'inflation_rate': 0.03,
            'state': 'NY',
            'filing_status': 'Single',
            'standard_deduction': 14600,
            'ss_primary_benefit': 35000,
            'ss_primary_start_age': 67,
            'ss_spousal_benefit': 0,
            'ss_spousal_start_age': 67,
            'ss_funding_scenario': 'conservative',
            'lower_guardrail': 0.035,
            'upper_guardrail': 0.025,
            'spending_adjustment': 0.10,
            'max_spending_increase': 0.05,
            'max_spending_decrease': 0.10,
            'spending_floor_real': 120000,
            'spending_ceiling_real': 200000,
            'floor_end_year': 2045,
            'income_streams': [
                {'amount': 50000, 'start_year': 2026, 'years': 10, 'description': 'Consulting'}
            ],
            'expense_streams': [
                {'amount': 25000, 'start_year': 2030, 'years': 4, 'description': 'College'}
            ],
            'college_enabled': True,
            'college_amount': 70000,
            'college_years': 8,
            'college_start_year': 2032,
            'inheritance_amount': 500000,
            'inheritance_year': 2040,
            'market_regime': 'baseline',
            'num_simulations': 10000,
            'cape_now': 25,
            'enable_ai': False,
            'gemini_api_key': '',
            'gemini_model': 'gemini-2.5-pro'
        }

        # Step 1: Convert wizard params to JSON
        wizard_json = convert_wizard_to_json(wizard_params)

        # Verify JSON structure
        assert isinstance(wizard_json, dict)
        assert 'basic_params' in wizard_json
        assert 'allocation' in wizard_json
        assert 'market_assumptions' in wizard_json
        assert 'taxes' in wizard_json
        assert 'social_security' in wizard_json
        assert 'guardrails' in wizard_json

        # Step 2: Convert to flat simulation parameters
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)

        # Verify key parameters are mapped correctly
        assert flat_params['start_capital'] == 3000000
        assert flat_params['w_equity'] == 0.70
        assert flat_params['w_bonds'] == 0.20
        assert flat_params['equity_mean'] == 0.08
        assert flat_params['filing_status'] == 'Single'
        assert flat_params['ss_annual_benefit'] == 35000
        assert flat_params['lower_wr'] == 0.035

        # Step 3: Create SimulationParams object
        params = dict_to_params(flat_params)

        # Verify SimulationParams object
        assert isinstance(params, SimulationParams)
        assert params.start_capital == 3000000
        assert params.w_equity == 0.70
        assert params.equity_mean == 0.08
        assert params.ss_annual_benefit == 35000

        # Step 4: Verify all critical parameters are preserved
        critical_params = [
            'start_capital', 'w_equity', 'w_bonds', 'w_real_estate', 'w_cash',
            'equity_mean', 'bonds_mean', 'real_estate_mean', 'cash_mean',
            'equity_vol', 'bonds_vol', 'real_estate_vol', 'cash_vol',
            'lower_wr', 'upper_wr', 'adjustment_pct',
            'spending_floor_real', 'spending_ceiling_real', 'floor_end_year',
            'ss_annual_benefit', 'ss_start_age',
            'filing_status', 'standard_deduction',
            'num_sims', 'cape_now'
        ]

        for param in critical_params:
            assert hasattr(params, param), f"Parameter {param} missing from SimulationParams"

    def test_parameter_type_preservation(self):
        """Test that parameter types are preserved correctly during conversion"""

        wizard_params = {
            'start_capital': 2500000,  # int
            'equity_pct': 0.65,        # float
            'glide_path': True,        # bool
            'state': 'CA',             # str
            'income_streams': [{'amount': 50000}],  # list
            'enable_ai': False         # bool
        }

        # Convert through the pipeline
        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Verify types
        assert isinstance(params.start_capital, (int, float))
        assert isinstance(params.w_equity, float)
        assert isinstance(params.glide_path_enabled, bool)
        assert isinstance(params.num_sims, int)

    def test_default_parameter_application(self):
        """Test that default parameters are applied for missing wizard values"""

        # Minimal wizard parameters
        minimal_params = {
            'start_capital': 1000000,
            'annual_spending': 50000
        }

        # Convert through pipeline
        wizard_json = convert_wizard_to_json(minimal_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Verify defaults are applied
        assert params.start_capital == 1000000  # Preserved
        assert params.w_equity == 0.65          # Default
        assert params.w_bonds == 0.25           # Default
        assert params.equity_mean == 0.0742     # Default
        assert params.num_sims == 10000         # Default
        assert params.cape_now == 28.0          # Default

    def test_session_state_population_simulation(self):
        """Test simulation of session state population (since we can't test actual Streamlit)"""

        wizard_params = {
            'start_capital': 2000000,
            'equity_pct': 0.80,
            'bonds_pct': 0.15,
            'real_estate_pct': 0.05,
            'cash_pct': 0.00,
            'num_simulations': 5000,
            'cape_now': 30
        }

        # Convert to simulation parameters
        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Simulate session state updates (this is what the Monte Carlo page does)
        mock_session_state = {}

        # Key parameters that Monte Carlo page sets
        session_mappings = {
            'start_year': params.start_year,
            'horizon_years': params.horizon_years,
            'num_sims': params.num_sims,
            'random_seed': params.random_seed,
            'custom_capital': params.start_capital,
            'use_custom_capital': True,
            'w_equity': params.w_equity,
            'w_bonds': params.w_bonds,
            'w_real_estate': params.w_real_estate,
            'w_cash': params.w_cash,
            'equity_mean': params.equity_mean,
            'bonds_mean': params.bonds_mean,
            'cape_now': params.cape_now,
            'lower_wr': params.lower_wr,
            'upper_wr': params.upper_wr,
            'filing_status': params.filing_status,
            'parameters_loaded': True
        }

        mock_session_state.update(session_mappings)

        # Verify session state would be populated correctly
        assert mock_session_state['custom_capital'] == 2000000
        assert mock_session_state['w_equity'] == 0.80
        assert mock_session_state['num_sims'] == 5000
        assert mock_session_state['cape_now'] == 30
        assert mock_session_state['parameters_loaded'] is True

    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling in the transition"""

        # Test empty wizard parameters
        empty_params = {}
        wizard_json = convert_wizard_to_json(empty_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Should still create valid SimulationParams with defaults
        assert isinstance(params, SimulationParams)
        assert params.start_capital > 0
        assert params.w_equity > 0
        assert params.num_sims > 0

        # Test invalid allocation (should still work due to defaults)
        invalid_params = {
            'equity_pct': 1.5,    # Over 100%
            'bonds_pct': -0.1,    # Negative
        }

        wizard_json = convert_wizard_to_json(invalid_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Should create params (validation happens in UI, not conversion)
        assert isinstance(params, SimulationParams)

    def test_complex_data_structures_preservation(self):
        """Test that complex data structures (lists, nested objects) are preserved"""

        wizard_params = {
            'income_streams': [
                {'amount': 50000, 'start_year': 2026, 'years': 5, 'description': 'Consulting'},
            ],
            'expense_streams': [
                {'amount': 80000, 'start_year': 2032, 'years': 4, 'description': 'College tuition'},
                {'amount': 25000, 'start_year': 2035, 'years': 2, 'description': 'Home renovation'}
            ]
        }

        # Convert through pipeline
        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Verify complex structures are preserved
        # Income streams get aggregated into other_income_* parameters
        assert params.other_income_amount > 0  # Should have aggregated income
        assert len(params.expense_streams) == 2  # Expense streams are preserved as list
        assert params.expense_streams[0]['amount'] == 80000
        assert params.expense_streams[0]['description'] == 'College tuition'

    def test_state_tax_integration_preservation(self):
        """Test that state tax settings are preserved correctly"""

        test_states = ['CA', 'NY', 'TX', 'FL']

        for state in test_states:
            wizard_params = {
                'state': state,
                'filing_status': 'MFJ',
                'standard_deduction': 29200
            }

            wizard_json = convert_wizard_to_json(wizard_params)
            flat_params = convert_wizard_json_to_simulation_params(wizard_json)
            params = dict_to_params(flat_params)

            # Verify state-specific tax parameters are set
            assert len(params.tax_brackets) >= 3  # Should have tax brackets
            assert params.filing_status == 'MFJ'
            assert params.standard_deduction == 29200

    def test_social_security_integration_preservation(self):
        """Test that Social Security parameters are preserved correctly"""

        wizard_params = {
            'ss_primary_benefit': 42000,
            'ss_primary_start_age': 70,  # Delayed claiming
            'ss_spousal_benefit': 18000,
            'ss_spousal_start_age': 67,
            'ss_funding_scenario': 'optimistic',
            'ss_custom_reduction': 0.15,
            'ss_reduction_start_year': 2035
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Verify Social Security parameters
        assert params.ss_annual_benefit == 42000
        assert params.ss_start_age == 70
        assert params.spouse_ss_annual_benefit == 18000
        assert params.ss_benefit_scenario == 'optimistic'

    def test_market_regime_and_simulation_settings(self):
        """Test that market regime and simulation settings are preserved"""

        wizard_params = {
            'market_regime': 'recession_recover',
            'num_simulations': 25000,
            'cape_now': 15,  # Low valuation
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Verify market settings
        assert params.regime == 'recession_recover'
        assert params.num_sims == 25000
        assert params.cape_now == 15

    def test_parameter_count_completeness(self):
        """Test that the conversion produces all expected parameters"""

        # Full wizard parameters
        full_wizard_params = {
            'start_capital': 3000000, 'annual_spending': 120000,
            'retirement_age': 65, 'start_year': 2025, 'horizon_years': 50,
            'equity_pct': 0.70, 'bonds_pct': 0.25, 'real_estate_pct': 0.05,
            'equity_return': 0.075, 'bonds_return': 0.035,
            'state': 'CA', 'filing_status': 'MFJ',
            'ss_primary_benefit': 35000, 'lower_guardrail': 0.05,
            'num_simulations': 10000, 'market_regime': 'baseline'
        }

        wizard_json = convert_wizard_to_json(full_wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)

        # Should produce comprehensive parameter set
        assert len(flat_params) >= 50  # Should have 50+ parameters

        # Key parameter categories should be present
        financial_params = ['start_capital', 'w_equity', 'w_bonds', 'equity_mean']
        tax_params = ['filing_status', 'standard_deduction', 'tax_brackets']
        ss_params = ['ss_annual_benefit', 'ss_start_age']
        guardrail_params = ['lower_wr', 'upper_wr', 'adjustment_pct']
        simulation_params = ['num_sims', 'cape_now', 'regime']

        all_expected_params = financial_params + tax_params + ss_params + guardrail_params + simulation_params

        for param in all_expected_params:
            if param != 'tax_brackets':  # tax_brackets is handled specially
                assert param in flat_params, f"Expected parameter {param} not found"


class TestParameterValidationInTransition:
    """Test parameter validation during the transition"""

    def test_allocation_sum_validation(self):
        """Test that allocation sums are reasonable after conversion"""

        wizard_params = {
            'equity_pct': 0.60,
            'bonds_pct': 0.30,
            'real_estate_pct': 0.08,
            'cash_pct': 0.02
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Check allocation sums to 1.0
        total_allocation = params.w_equity + params.w_bonds + params.w_real_estate + params.w_cash
        assert abs(total_allocation - 1.0) < 0.001, f"Allocation sum {total_allocation} != 1.0"

    def test_parameter_ranges_are_reasonable(self):
        """Test that converted parameters are in reasonable ranges"""

        wizard_params = {
            'start_capital': 2500000,
            'equity_return': 0.08,
            'equity_vol': 0.18,
            'inflation_rate': 0.025,
            'lower_guardrail': 0.05,
            'upper_guardrail': 0.04
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Verify reasonable ranges
        assert params.start_capital > 0
        assert 0 < params.equity_mean < 0.20  # 0-20% returns
        assert 0 < params.equity_vol < 1.0    # 0-100% volatility
        assert 0 < params.lower_wr < 0.20     # 0-20% withdrawal rate
        assert params.upper_wr < params.lower_wr  # Upper < Lower for guardrails


if __name__ == '__main__':
    pytest.main([__file__, '-v'])