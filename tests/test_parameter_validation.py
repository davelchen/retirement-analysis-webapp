"""
Unit tests for parameter validation and error handling

These tests focus on catching the types of errors we've encountered:
- AttributeError on missing SimulationParams fields
- Parameter conversion issues between wizard and Monte Carlo
- Missing parameter mappings
- Type conversion errors (decimal/percentage)
- Default value consistency
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pages.wizard import convert_wizard_to_json, initialize_wizard_state
from io_utils import convert_wizard_json_to_simulation_params, dict_to_params
from simulation import SimulationParams


class TestParameterValidation:
    """Test parameter validation and error handling"""

    def test_simulation_params_has_all_expected_attributes(self):
        """Test that SimulationParams has all attributes we try to access"""

        # Create default SimulationParams
        params = SimulationParams()

        # Critical attributes that caused AttributeError in the past
        critical_attributes = [
            'start_capital', 'w_equity', 'w_bonds', 'w_real_estate', 'w_cash',
            'equity_mean', 'bonds_mean', 'real_estate_mean', 'cash_mean',
            'equity_vol', 'bonds_vol', 'real_estate_vol', 'cash_vol',
            'ss_annual_benefit', 'ss_start_age', 'ss_benefit_scenario',
            'spouse_ss_annual_benefit', 'spouse_ss_start_age', 'spouse_ss_enabled',
            'lower_wr', 'upper_wr', 'adjustment_pct',
            'cape_now', 'regime', 'num_sims',
            'glide_path_enabled', 'equity_reduction_per_year',
            'spending_floor_real', 'spending_ceiling_real', 'floor_end_year',
            'college_enabled', 'college_base_amount', 'college_start_year', 'college_end_year',
            'inherit_amount', 'inherit_year',
            'filing_status', 'standard_deduction', 'tax_brackets'
        ]

        for attr in critical_attributes:
            assert hasattr(params, attr), f"SimulationParams missing critical attribute: {attr}"

    def test_inflation_rate_not_in_simulation_params(self):
        """Test that inflation_rate is NOT in SimulationParams (to catch our AttributeError)"""

        params = SimulationParams()

        # This should fail - inflation_rate is not a SimulationParams attribute
        assert not hasattr(params, 'inflation_rate'), "inflation_rate should not be in SimulationParams"

    def test_wizard_json_conversion_completeness(self):
        """Test that wizard JSON conversion includes all collected parameters"""

        # Full wizard parameters from all steps
        full_wizard_params = {
            # Basic parameters
            'start_capital': 3000000,
            'annual_spending': 150000,
            'retirement_age': 62,
            'start_year': 2026,
            'horizon_years': 40,

            # Asset allocation
            'equity_pct': 0.70,
            'bonds_pct': 0.20,
            'real_estate_pct': 0.08,
            'cash_pct': 0.02,
            'glide_path': True,
            'equity_reduction_per_year': 0.005,

            # Market assumptions
            'equity_return': 0.08,
            'bonds_return': 0.03,
            'real_estate_return': 0.06,
            'cash_return': 0.02,
            'equity_vol': 0.18,
            'bonds_vol': 0.04,
            'real_estate_vol': 0.15,
            'inflation_rate': 0.03,

            # Taxes
            'state': 'NY',
            'filing_status': 'Single',
            'standard_deduction': 14600,

            # Social Security
            'ss_primary_benefit': 35000,
            'ss_primary_start_age': 67,
            'ss_spousal_benefit': 15000,
            'ss_spousal_start_age': 67,
            'ss_funding_scenario': 'conservative',

            # Guardrails
            'lower_guardrail': 0.03,
            'upper_guardrail': 0.05,
            'spending_adjustment': 0.10,
            'max_spending_increase': 0.10,
            'max_spending_decrease': 0.10,
            'spending_floor_real': 120000,
            'spending_ceiling_real': 200000,
            'floor_end_year': 2045,

            # Cash flows
            'income_streams': [
                {'amount': 50000, 'start_year': 2026, 'years': 10, 'description': 'Consulting'}
            ],
            'expense_streams': [
                {'amount': 25000, 'start_year': 2030, 'years': 4, 'description': 'College'}
            ],

            # College and inheritance (these were missing!)
            'college_enabled': True,
            'college_amount': 70000,
            'college_years': 8,
            'college_start_year': 2032,
            'inheritance_amount': 500000,
            'inheritance_year': 2040,

            # Advanced
            'market_regime': 'baseline',
            'num_simulations': 10000,
            'cape_now': 25,

            # AI
            'enable_ai': False,
            'gemini_api_key': '',
            'gemini_model': 'gemini-2.5-pro'
        }

        # Convert to JSON
        wizard_json = convert_wizard_to_json(full_wizard_params)

        # Verify all major sections exist
        required_sections = [
            'basic_params', 'allocation', 'market_assumptions', 'taxes',
            'social_security', 'guardrails', 'simulation', 'ai_config',
            'cash_flows', 'advanced_options', 'metadata'
        ]

        for section in required_sections:
            assert section in wizard_json, f"Missing required section: {section}"

        # Verify critical parameters are included
        assert wizard_json['advanced_options']['college_enabled'] == True
        assert wizard_json['advanced_options']['college_amount'] == 70000
        assert wizard_json['advanced_options']['inheritance_amount'] == 500000
        assert wizard_json['advanced_options']['spending_floor_real'] == 120000

    def test_parameter_conversion_pipeline_integrity(self):
        """Test the complete wizard -> JSON -> SimulationParams -> dict pipeline"""

        wizard_params = {
            'start_capital': 2500000,
            'equity_pct': 0.65,
            'ss_primary_benefit': 40000,
            'ss_spousal_benefit': 20000,  # Should enable spouse SS
            'college_enabled': True,
            'college_amount': 75000,
            'inheritance_amount': 300000,
            'inflation_rate': 0.025,  # Critical: this is NOT in SimulationParams
            'lower_guardrail': 0.03,
            'upper_guardrail': 0.05
        }

        # Step 1: Wizard -> JSON
        wizard_json = convert_wizard_to_json(wizard_params)

        # Step 2: JSON -> flat parameters
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)

        # Verify inflation_rate is in flat_params (not SimulationParams)
        assert 'inflation_rate' in flat_params
        assert flat_params['inflation_rate'] == 0.025

        # Step 3: flat -> SimulationParams
        params = dict_to_params(flat_params)

        # Verify conversion worked
        assert params.start_capital == 2500000
        assert params.w_equity == 0.65
        assert params.ss_annual_benefit == 40000
        assert params.spouse_ss_annual_benefit == 20000
        assert params.spouse_ss_enabled == True  # Should be auto-enabled
        assert params.college_enabled == True
        assert params.inherit_amount == 300000

        # Verify inflation_rate is NOT in SimulationParams (this was our bug)
        assert not hasattr(params, 'inflation_rate')

    def test_decimal_percentage_conversion_consistency(self):
        """Test that decimal/percentage conversions are consistent"""

        wizard_params = {
            'lower_guardrail': 0.03,  # 3% as decimal
            'upper_guardrail': 0.05,  # 5% as decimal
            'spending_adjustment': 0.10,  # 10% as decimal
            'equity_pct': 0.70,  # 70% as decimal
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # All these should remain as decimals in SimulationParams
        assert params.lower_wr == 0.03
        assert params.upper_wr == 0.05
        assert params.adjustment_pct == 0.10
        assert params.w_equity == 0.70

    def test_social_security_parameter_mapping(self):
        """Test Social Security parameter name mapping (this caused issues)"""

        wizard_params = {
            'ss_primary_benefit': 45000,
            'ss_primary_start_age': 70,
            'ss_spousal_benefit': 22000,
            'ss_spousal_start_age': 67,
            'ss_funding_scenario': 'optimistic'
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)

        # Verify parameter name mapping
        assert flat_params['ss_annual_benefit'] == 45000  # primary -> annual
        assert flat_params['ss_start_age'] == 70
        assert flat_params['spouse_ss_annual_benefit'] == 22000
        assert flat_params['spouse_ss_start_age'] == 67
        assert flat_params['spouse_ss_enabled'] == True  # Auto-enabled
        assert flat_params['ss_benefit_scenario'] == 'optimistic'

    def test_missing_parameter_defaults(self):
        """Test that missing parameters get reasonable defaults"""

        # Minimal wizard parameters
        minimal_params = {
            'start_capital': 1000000
        }

        wizard_json = convert_wizard_to_json(minimal_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Should have reasonable defaults
        assert params.start_capital == 1000000  # Preserved
        assert 0.5 <= params.w_equity <= 0.8    # Reasonable equity allocation
        assert params.ss_annual_benefit >= 0    # Non-negative
        assert params.lower_wr > 0              # Positive withdrawal rate
        assert params.upper_wr > params.lower_wr  # Upper > Lower
        assert params.num_sims >= 1000          # Reasonable simulation count

    def test_guardrail_logic_validation(self):
        """Test guardrail parameter logic is correct"""

        wizard_params = {
            'lower_guardrail': 0.035,  # 3.5% - increase spending below this
            'upper_guardrail': 0.055,  # 5.5% - decrease spending above this
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Upper WR should be higher than lower WR (for spending cuts)
        assert params.upper_wr > params.lower_wr, f"Guardrail logic error: upper_wr ({params.upper_wr}) should be > lower_wr ({params.lower_wr})"

    def test_parameter_type_preservation(self):
        """Test that parameter types are preserved correctly"""

        wizard_params = {
            'start_capital': 2500000,       # int
            'equity_pct': 0.65,            # float
            'glide_path': True,            # bool
            'state': 'CA',                 # str
            'num_simulations': 10000,      # int
            'ss_primary_benefit': 40000.0, # float
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Verify types are correct
        assert isinstance(params.start_capital, (int, float))
        assert isinstance(params.w_equity, float)
        assert isinstance(params.glide_path_enabled, bool)
        assert isinstance(params.num_sims, int)
        assert isinstance(params.ss_annual_benefit, (int, float))


class TestParameterErrorHandling:
    """Test error handling for invalid parameters"""

    def test_invalid_parameter_values_handled_gracefully(self):
        """Test that invalid values don't crash the conversion pipeline"""

        invalid_params = {
            'start_capital': -100000,      # Negative
            'equity_pct': 1.5,            # Over 100%
            'retirement_age': 25,         # Too young
            'horizon_years': -10,         # Negative
            'ss_primary_benefit': 'invalid', # Wrong type
        }

        # Should not raise exceptions during conversion
        try:
            wizard_json = convert_wizard_to_json(invalid_params)
            flat_params = convert_wizard_json_to_simulation_params(wizard_json)
            params = dict_to_params(flat_params)

            # Should create SimulationParams instance (even with invalid values)
            assert isinstance(params, SimulationParams)

            # Invalid values should be preserved (not sanitized) - this is correct behavior
            # The parameter conversion pipeline shouldn't silently "fix" bad data
            assert params.start_capital == -100000  # Negative value preserved
            assert params.w_equity == 1.5  # Over 100% preserved
            assert params.horizon_years == -10  # Negative value preserved

            # Note: Validation should happen elsewhere (in UI or simulation),
            # not during parameter conversion

        except Exception as e:
            pytest.fail(f"Invalid parameters caused crash in conversion pipeline: {e}")

    def test_empty_wizard_params_handled(self):
        """Test that completely empty wizard params don't crash"""

        empty_params = {}

        # Should not raise exceptions
        wizard_json = convert_wizard_to_json(empty_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Should create valid SimulationParams with all defaults
        assert isinstance(params, SimulationParams)
        assert params.start_capital > 0
        assert params.w_equity > 0
        assert params.num_sims > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])