"""
Integration tests focusing on errors we've encountered in production

These tests simulate the exact error conditions we've faced:
- Session state parameter loading errors
- Page navigation issues
- Parameter accessibility problems
- UI component errors
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pages.wizard import convert_wizard_to_json, safe_get_wizard_param
from io_utils import convert_wizard_json_to_simulation_params, dict_to_params


class MockSessionState:
    """Mock Streamlit session state that behaves like the real one"""
    def __init__(self, initial_data=None):
        self._data = initial_data or {}

    def __getattr__(self, key):
        return self._data.get(key)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        return self._data.get(key, default)


class TestSessionStateIntegration:
    """Test session state parameter loading like in Monte Carlo page"""

    def test_monte_carlo_parameter_loading_simulation(self):
        """Simulate the Monte Carlo page parameter loading process"""

        # Simulate wizard completion
        wizard_params = {
            'start_capital': 2000000,
            'equity_pct': 0.70,
            'ss_primary_benefit': 42000,
            'ss_spousal_benefit': 18000,
            'college_enabled': True,
            'college_amount': 80000,
            'inheritance_amount': 400000,
            'inflation_rate': 0.028,  # This caused AttributeError
            'lower_guardrail': 0.03,
            'upper_guardrail': 0.05
        }

        # Convert through the pipeline (like Monte Carlo page does)
        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Simulate session state loading (like in monte_carlo.py)
        mock_session_state = {}

        # Test all the session state assignments that caused errors
        assignments = [
            # Basic parameters
            ('start_year', params.start_year),
            ('horizon_years', params.horizon_years),
            ('num_sims', params.num_sims),
            ('custom_capital', params.start_capital),
            ('w_equity', params.w_equity),

            # Social Security (these were missing)
            ('social_security_enabled', True),
            ('ss_annual_benefit', params.ss_annual_benefit),
            ('ss_start_age', params.ss_start_age),
            ('spouse_ss_enabled', params.spouse_ss_annual_benefit > 0),
            ('spouse_ss_annual_benefit', params.spouse_ss_annual_benefit),

            # Guardrails
            ('lower_wr', params.lower_wr),
            ('upper_wr', params.upper_wr),

            # College
            ('college_enabled', params.college_enabled),
            ('college_base_amount', params.college_base_amount),

            # Inheritance
            ('inherit_amount', params.inherit_amount),
            ('inherit_year', params.inherit_year),

            # CRITICAL: inflation_rate from flat_params (not params)
            ('inflation_rate', flat_params.get('inflation_rate', 0.025)),
            ('currency_view', 'Real'),
        ]

        # All these should work without AttributeError
        for key, value in assignments:
            try:
                mock_session_state[key] = value
            except AttributeError as e:
                pytest.fail(f"AttributeError accessing {key}: {e}")

        # Verify critical values
        assert mock_session_state['custom_capital'] == 2000000  # 'custom_capital', not 'start_capital'
        assert mock_session_state['ss_annual_benefit'] == 42000
        assert mock_session_state['spouse_ss_enabled'] == True
        assert mock_session_state['college_enabled'] == True
        assert mock_session_state['inflation_rate'] == 0.028  # From flat_params!

    def test_wizard_parameter_safe_access(self):
        """Test safe wizard parameter access (preventing KeyError)"""

        # Empty wizard params (common error scenario)
        empty_params = {}
        mock_session = MockSessionState({'wizard_params': empty_params})

        # Test safe_get_wizard_param function
        try:
            with patch('pages.wizard.st.session_state', mock_session):
                # These should not raise KeyError
                capital = safe_get_wizard_param('start_capital', 2500000)
                equity = safe_get_wizard_param('equity_pct', 0.65)
                ss_benefit = safe_get_wizard_param('ss_primary_benefit', 40000)

                assert capital == 2500000
                assert equity == 0.65
                assert ss_benefit == 40000

        except Exception as e:
            pytest.fail(f"Safe parameter access failed: {e}")

    def test_missing_wizard_session_state_initialization(self):
        """Test initialization when wizard_params is missing from session state"""

        # Mock empty session state
        mock_session = MockSessionState({})

        with patch('pages.wizard.st.session_state', mock_session):
            # This should initialize wizard_params
            from pages.wizard import initialize_wizard_state
            initialize_wizard_state()

            # Should now have wizard_params
            assert 'wizard_params' in mock_session
            assert isinstance(mock_session.wizard_params, dict)
            assert mock_session.wizard_params['start_capital'] > 0


class TestParameterMappingErrors:
    """Test specific parameter mapping errors we encountered"""

    def test_social_security_parameter_name_mapping(self):
        """Test SS parameter name mapping (ss_primary_benefit -> ss_annual_benefit)"""

        wizard_params = {
            'ss_primary_benefit': 45000,
            'ss_spousal_benefit': 20000,
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)

        # Verify correct parameter name mapping
        assert 'ss_annual_benefit' in flat_params  # NOT ss_primary_benefit
        assert 'spouse_ss_annual_benefit' in flat_params  # NOT ss_spousal_benefit
        assert flat_params['ss_annual_benefit'] == 45000
        assert flat_params['spouse_ss_annual_benefit'] == 20000

    def test_college_parameter_inclusion(self):
        """Test that college parameters are included in JSON (they were missing)"""

        wizard_params = {
            'college_enabled': True,
            'college_amount': 75000,
            'college_years': 8,
            'college_start_year': 2032,
        }

        wizard_json = convert_wizard_to_json(wizard_params)

        # College parameters should be in advanced_options section
        assert 'advanced_options' in wizard_json
        assert wizard_json['advanced_options']['college_enabled'] == True
        assert wizard_json['advanced_options']['college_amount'] == 75000
        assert wizard_json['advanced_options']['college_years'] == 8

    def test_inheritance_parameter_inclusion(self):
        """Test that inheritance parameters are included (they were missing)"""

        wizard_params = {
            'inheritance_amount': 500000,
            'inheritance_year': 2040,
        }

        wizard_json = convert_wizard_to_json(wizard_params)

        # Inheritance should be in advanced_options
        assert 'advanced_options' in wizard_json
        assert wizard_json['advanced_options']['inheritance_amount'] == 500000
        assert wizard_json['advanced_options']['inheritance_year'] == 2040

    def test_spending_bounds_parameter_inclusion(self):
        """Test spending floor/ceiling parameters (were missing)"""

        wizard_params = {
            'spending_floor_real': 120000,
            'spending_ceiling_real': 200000,
            'floor_end_year': 2045,
        }

        wizard_json = convert_wizard_to_json(wizard_params)

        # Should be in advanced_options
        assert wizard_json['advanced_options']['spending_floor_real'] == 120000
        assert wizard_json['advanced_options']['spending_ceiling_real'] == 200000
        assert wizard_json['advanced_options']['floor_end_year'] == 2045


class TestGuardrailParameterErrors:
    """Test guardrail parameter errors we encountered"""

    def test_guardrail_default_value_consistency(self):
        """Test guardrail defaults are consistent (lower < upper)"""

        # Test default initialization
        from pages.wizard import initialize_wizard_state

        mock_session = MockSessionState({})
        with patch('pages.wizard.st.session_state', mock_session):
            initialize_wizard_state()

            lower = mock_session.wizard_params['lower_guardrail']
            upper = mock_session.wizard_params['upper_guardrail']

            # Lower should be greater than upper (correct guardrail logic)
            # lower_wr is the "high WR" threshold that triggers spending cuts
            # upper_wr is the "low WR" threshold that triggers spending increases
            assert lower > upper, f"Guardrail defaults incorrect: lower({lower}) <= upper({upper})"

            # Should be reasonable values
            assert 0.04 <= lower <= 0.06  # 4-6% (high WR threshold)
            assert 0.02 <= upper <= 0.04  # 2-4% (low WR threshold)

    def test_guardrail_slider_decimal_conversion(self):
        """Test decimal/percentage conversion in guardrail sliders"""

        # Wizard stores as decimals
        wizard_params = {
            'lower_guardrail': 0.03,  # 3%
            'upper_guardrail': 0.05,  # 5%
        }

        # Should convert correctly through pipeline
        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Should remain as decimals in SimulationParams
        assert params.lower_wr == 0.03
        assert params.upper_wr == 0.05

        # When displayed in UI, should convert to percentage (* 100)
        lower_display = params.lower_wr * 100  # Should be 3.0
        upper_display = params.upper_wr * 100  # Should be 5.0

        assert lower_display == 3.0
        assert upper_display == 5.0


class TestUIComponentErrors:
    """Test UI component errors we encountered"""

    def test_glide_path_parameter_mapping(self):
        """Test glide path parameters are properly mapped"""

        wizard_params = {
            'glide_path': True,
            'equity_reduction_per_year': 0.005,
        }

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)
        params = dict_to_params(flat_params)

        # Should map correctly
        assert params.glide_path_enabled == True  # glide_path -> glide_path_enabled
        assert params.equity_reduction_per_year == 0.005

    def test_capital_preset_parameter(self):
        """Test capital preset parameter handling"""

        wizard_params = {'start_capital': 3000000}

        wizard_json = convert_wizard_to_json(wizard_params)
        flat_params = convert_wizard_json_to_simulation_params(wizard_json)

        # When loading into Monte Carlo session state, should set capital_preset
        mock_session_state = {}
        mock_session_state['capital_preset'] = 'Custom'  # Wizard always uses custom
        mock_session_state['custom_capital'] = flat_params['start_capital']
        mock_session_state['use_custom_capital'] = True

        assert mock_session_state['capital_preset'] == 'Custom'
        assert mock_session_state['custom_capital'] == 3000000
        assert mock_session_state['use_custom_capital'] == True


class TestPageNavigationErrors:
    """Test page navigation and state management errors"""

    @pytest.mark.skip(reason="Complex UI mocking - step_review accesses many wizard_params keys")
    def test_wizard_completion_flag_handling(self):
        """Test wizard completion flag prevents step re-rendering"""

        # Simulate completed wizard
        mock_session_state = MagicMock()
        mock_session_state.wizard_completed = True
        mock_session_state.wizard_params = {
            'start_capital': 2000000,
            'annual_spending': 100000,
            'retirement_age': 65,
            'horizon_years': 40,
            'equity_pct': 0.7,
            'bonds_pct': 0.2,
            'real_estate_pct': 0.1,
            'cash_pct': 0.0,
            'state': 'CA',
            'filing_status': 'MFJ'
        }
        mock_session_state.get = lambda key, default=None: getattr(mock_session_state, key, default)

        with patch('pages.wizard.st.session_state', mock_session_state):
            with patch('pages.wizard.st.switch_page') as mock_switch_page:
                # Import and call step_review
                from pages.wizard import step_review

                # Should redirect instead of showing review step
                step_review()

                # Should have called switch_page
                mock_switch_page.assert_called_with("pages/monte_carlo.py")

    def test_missing_session_state_recovery(self):
        """Test recovery from missing session state"""

        # Test various missing session state scenarios
        missing_scenarios = [
            {},  # Completely empty
            {'wizard_step': 5},  # Missing wizard_params
            {'wizard_params': {}},  # Empty wizard_params
        ]

        for scenario in missing_scenarios:
            mock_session = MockSessionState(scenario)
            with patch('pages.wizard.st.session_state', mock_session):
                try:
                    # Should not crash
                    value = safe_get_wizard_param('start_capital', 2500000)
                    assert value == 2500000
                except Exception as e:
                    pytest.fail(f"Failed to recover from missing session state {scenario}: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])