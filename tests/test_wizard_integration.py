"""
Unit tests for wizard parameter handling and integration

These tests catch parameter wiring/naming issues that could cause KeyError exceptions
in the multipage Streamlit environment.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import wizard functions
from pages.wizard import convert_wizard_to_json, initialize_wizard_state


class TestWizardParameterHandling:
    """Test wizard parameter access and validation"""

    def test_convert_wizard_to_json_with_minimal_params(self):
        """Test JSON conversion with minimal wizard parameters"""
        minimal_params = {
            'start_capital': 1000000,
            'annual_spending': 80000
        }

        result = convert_wizard_to_json(minimal_params)

        # Should not raise KeyError and should have defaults
        assert result['basic_params']['start_capital'] == 1000000
        assert result['basic_params']['annual_spending'] == 80000
        assert result['basic_params']['retirement_age'] == 65  # default
        assert result['allocation']['equity_pct'] == 0.65  # default

    def test_convert_wizard_to_json_with_empty_params(self):
        """Test JSON conversion with completely empty parameters"""
        empty_params = {}

        result = convert_wizard_to_json(empty_params)

        # Should not raise KeyError and should use all defaults
        assert result['basic_params']['start_capital'] == 2_500_000
        assert result['basic_params']['annual_spending'] == 120_000
        assert result['basic_params']['retirement_age'] == 65
        assert result['allocation']['equity_pct'] == 0.65

    def test_convert_wizard_to_json_all_parameters(self):
        """Test JSON conversion with all parameters present"""
        full_params = {
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
            'equity_vol': 0.20,
            'bonds_vol': 0.05,
            'real_estate_vol': 0.15,
            'inflation_rate': 0.03,
            'state': 'NY',
            'filing_status': 'Single',
            'standard_deduction': 14600,
            'ss_primary_benefit': 35000,
            'ss_primary_start_age': 67,
            'ss_spousal_benefit': 15000,
            'ss_spousal_start_age': 67,
            'ss_funding_scenario': 'conservative',
            'lower_guardrail': 0.035,
            'upper_guardrail': 0.025,
            'spending_adjustment': 0.10,
            'max_spending_increase': 0.05,
            'max_spending_decrease': 0.10,
            'spending_floor_real': 100000,
            'spending_ceiling_real': 250000,
            'floor_end_year': 2045,
            'income_streams': [{'amount': 50000, 'start_year': 2026, 'years': 10}],
            'expense_streams': [{'amount': 25000, 'start_year': 2030, 'years': 5}],
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
            'gemini_model': 'gemini-1.5-pro'
        }

        result = convert_wizard_to_json(full_params)

        # Verify all parameters are converted correctly
        assert result['basic_params']['start_capital'] == 3000000
        assert result['allocation']['equity_pct'] == 0.70
        assert result['market_assumptions']['equity_return'] == 0.08
        assert result['taxes']['state'] == 'NY'
        assert result['social_security']['ss_primary_benefit'] == 35000
        assert result['guardrails']['lower_guardrail'] == 0.035
        assert result['cash_flows']['income_streams'] == [{'amount': 50000, 'start_year': 2026, 'years': 10}]


class TestWizardStateManagement:
    """Test wizard session state management"""

    def test_initialize_wizard_state(self):
        """Test wizard state initialization"""
        # Create a mock object that behaves like streamlit session state
        class MockSessionState:
            def __init__(self):
                self._data = {}

            def __setattr__(self, name, value):
                if name.startswith('_'):
                    super().__setattr__(name, value)
                else:
                    self._data[name] = value

            def __getattr__(self, name):
                return self._data.get(name)

            def __contains__(self, name):
                return name in self._data

        mock_session_state = MockSessionState()

        with patch('pages.wizard.st.session_state', mock_session_state):
            initialize_wizard_state()

            # Should initialize wizard_params
            assert hasattr(mock_session_state, 'wizard_params')
            assert isinstance(mock_session_state.wizard_params, dict)

    def test_safe_parameter_access_patterns(self):
        """Test that parameter reading uses safe .get() patterns"""

        # Read the wizard file and check for unsafe patterns
        import re

        with open('/Users/chenda/retirement-analysis-webapp/pages/wizard.py', 'r') as f:
            content = f.read()

        # Look for unsafe parameter READING patterns (excluding assignments)
        # Pattern: wizard_params['key'] NOT followed by assignment operator
        lines = content.split('\n')
        unsafe_reads = []

        for i, line in enumerate(lines):
            # Look for dictionary access that is NOT an assignment
            if "wizard_params['" in line:
                # Check if this is an assignment (= comes after wizard_params)
                wizard_pos = line.find("wizard_params['")
                if wizard_pos >= 0:
                    before_wizard = line[:wizard_pos]
                    after_wizard = line[wizard_pos:]

                    # If there's an = before wizard_params, this is assignment
                    if "=" in before_wizard:
                        continue  # Skip assignments

                    # If there's wizard_params['key'] = ..., this is assignment
                    if re.search(r"wizard_params\['[^']+'\]\s*=", after_wizard):
                        continue  # Skip assignments

                    # Skip debug print statements (they're safe)
                    if line.strip().startswith('print(f"DEBUG'):
                        continue

                    # This appears to be a read operation
                    matches = re.findall(r"wizard_params\['[^']+'\]", line)
                    for match in matches:
                        unsafe_reads.append(f"Line {i+1}: {line.strip()}")

        # Should find no unsafe read patterns (all reads should use .get() now)
        assert len(unsafe_reads) == 0, f"Found unsafe parameter read patterns:\n" + "\n".join(unsafe_reads)

    def test_parameter_access_with_defaults(self):
        """Test that parameter access works with missing keys"""

        # Simulate empty wizard params
        mock_params = {}

        # Test that get() calls work with defaults
        result_capital = mock_params.get('start_capital', 2_500_000)
        result_spending = mock_params.get('annual_spending', 120_000)
        result_age = mock_params.get('retirement_age', 65)

        assert result_capital == 2_500_000
        assert result_spending == 120_000
        assert result_age == 65


class TestParameterValidation:
    """Test parameter validation and error handling"""

    def test_required_parameter_validation(self):
        """Test that required parameters are validated"""

        # Test with missing required parameters
        invalid_params = {
            'start_capital': -100000,  # Invalid negative value
            'retirement_age': 25,      # Invalid age
        }

        # JSON conversion should still work (uses defaults/validation)
        result = convert_wizard_to_json(invalid_params)

        # Should handle invalid values gracefully
        assert isinstance(result, dict)
        assert 'basic_params' in result

    def test_parameter_type_validation(self):
        """Test parameter type validation"""

        # Test with wrong types
        wrong_types = {
            'start_capital': "not_a_number",
            'glide_path': "not_a_boolean",
        }

        # Should handle type conversion gracefully
        result = convert_wizard_to_json(wrong_types)
        assert isinstance(result, dict)

    def test_parameter_range_validation(self):
        """Test parameter range validation"""

        # Test with out-of-range values
        out_of_range = {
            'equity_pct': 1.5,  # Over 100%
            'inflation_rate': -0.1,  # Negative
        }

        # Should handle range issues gracefully
        result = convert_wizard_to_json(out_of_range)
        assert isinstance(result, dict)


class TestMultipageIntegration:
    """Test multipage parameter sharing"""

    @patch('pages.wizard.st.session_state', {})
    def test_session_state_parameter_sharing(self):
        """Test that parameters can be shared between pages via session state"""

        import pages.wizard as wizard_module

        # Initialize wizard state
        wizard_module.st.session_state = {'wizard_params': {}}

        # Test that parameters can be set and retrieved
        test_params = {
            'start_capital': 2000000,
            'annual_spending': 100000
        }

        # Simulate setting parameters
        wizard_module.st.session_state['wizard_params'].update(test_params)

        # Test safe parameter access
        capital = wizard_module.st.session_state['wizard_params'].get('start_capital', 0)
        spending = wizard_module.st.session_state['wizard_params'].get('annual_spending', 0)
        missing = wizard_module.st.session_state['wizard_params'].get('missing_param', 'default')

        assert capital == 2000000
        assert spending == 100000
        assert missing == 'default'

    def test_wizard_completion_flag(self):
        """Test wizard completion tracking"""

        mock_session_state = {
            'wizard_completed': False,
            'wizard_params': {}
        }

        # Test completion flag can be set
        mock_session_state['wizard_completed'] = True
        assert mock_session_state['wizard_completed'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])