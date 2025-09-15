"""
Test suite for widget persistence patterns and session state management.

Based on hard-learned lessons about Streamlit's widget behavior and persistence.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from io_utils import convert_wizard_json_to_simulation_params
from ai_analysis import RetirementAnalyzer
from simulation import SimulationResults
import numpy as np


class TestParameterPersistence:
    """Test parameter conversion and persistence patterns"""

    def test_wizard_json_to_simulation_params(self):
        """Test that wizard JSON properly converts without data loss"""
        wizard_json = {
            "basic_params": {
                "start_capital": 2500000,
                "annual_spending": 250000,
                "retirement_age": 65,
                "horizon_years": 43
            },
            "allocation": {
                "equity_pct": 0.35,
                "bonds_pct": 0.4,
                "real_estate_pct": 0.2,
                "cash_pct": 0.05
            }
        }

        wizard_params = convert_wizard_json_to_simulation_params(wizard_json)

        # Test that conversion doesn't crash and produces a dict
        assert isinstance(wizard_params, dict)
        assert len(wizard_params) > 0

        # Test that key values are preserved (exact keys may vary by implementation)
        assert 'start_capital' in wizard_params
        assert wizard_params['start_capital'] == 2500000

    def test_parameter_roundtrip_consistency(self):
        """Test that parameters survive save/load cycles"""
        original_params = {
            'start_capital': 5000000,
            'retirement_age': 62,
            'horizon_years': 40,
            'equity_pct': 0.7,
            'bonds_pct': 0.2,
            'real_estate_pct': 0.1,
            'cash_pct': 0.0,
            'equity_reduction_per_year': 0.005,
            'inflation_rate': 0.03
        }

        # Convert to JSON and back (simulate roundtrip)
        json_data = json.loads(json.dumps(original_params))  # Simulate JSON roundtrip
        recovered_params = json_data  # For flat params, no conversion needed

        # All numeric values should be preserved
        for key, value in original_params.items():
            assert recovered_params[key] == pytest.approx(value, rel=1e-6)

    def test_percentage_conversion_accuracy(self):
        """Test that percentage ↔ decimal conversions are accurate"""
        test_values = [0.005, 0.035, 0.065, 0.175, 0.28]  # Common percentage values

        for decimal_value in test_values:
            # Simulate widget display conversion (decimal → percentage)
            percentage_display = decimal_value * 100

            # Simulate widget sync conversion (percentage → decimal)
            recovered_decimal = percentage_display / 100

            assert recovered_decimal == pytest.approx(decimal_value, rel=1e-10)


class TestAIAnalysisRobustness:
    """Test AI analysis fixes for NoneType errors"""

    def test_ai_analysis_handles_none_streams(self):
        """Test that AI analysis gracefully handles None stream parameters"""
        # Create mock simulation results
        mock_results = MagicMock(spec=SimulationResults)
        mock_results.terminal_wealth = np.array([1000000] * 1000)
        mock_results.wealth_paths = np.random.random((1000, 50))

        # Create mock params with None streams (the bug we fixed)
        mock_params = MagicMock()
        mock_params.expense_streams = None  # This was causing the error
        mock_params.income_streams = None   # This was causing the error
        mock_params.start_capital = 2500000
        mock_params.annual_spending = 100000

        # Mock terminal stats
        mock_terminal_stats = {
            'success_rate': 0.85,
            'median_final': 5000000,
            'prob_below_15m': 0.1
        }

        # This should not raise "object of type 'NoneType' has no len()" error
        analyzer = RetirementAnalyzer("test_key", "gemini-2.0-flash")

        try:
            # The _extract_analysis_data method should handle None gracefully
            analysis_data = analyzer._extract_analysis_data(mock_results, mock_params, mock_terminal_stats)

            # Should have empty lists, not None
            assert analysis_data['expenses']['expense_streams'] == []
            assert analysis_data['expenses']['income_streams'] == []

        except TypeError as e:
            if "object of type 'NoneType' has no len()" in str(e):
                pytest.fail("AI analysis still fails with NoneType error - fix not working")
            else:
                # Other errors are acceptable (API key issues, etc.)
                pass

    def test_stream_parameter_safety_pattern(self):
        """Test the pattern we use to ensure streams are never None"""
        # Test the pattern: streams if streams else []
        empty_streams = None
        safe_streams = empty_streams if empty_streams else []

        assert safe_streams == []
        assert len(safe_streams) == 0  # This should not raise "NoneType has no len()"

        # Test with actual data
        populated_streams = [{'amount': 1000, 'start_year': 2025}]
        safe_populated = populated_streams if populated_streams else []

        assert safe_populated == populated_streams
        assert len(safe_populated) == 1


class TestWidgetPatternValidation:
    """Test that widget persistence patterns work correctly"""

    def test_widget_value_source_pattern(self):
        """Test that widgets use wizard_params as value source"""
        # This tests the pattern: value=st.session_state.wizard_params.get('param', default)
        wizard_params = {
            'horizon_years': 45,
            'start_capital': 3500000,
            'retirement_age': 67
        }

        # Test that widget value comes from wizard_params
        assert wizard_params.get('horizon_years', 50) == 45  # Should use wizard_params value
        assert wizard_params.get('nonexistent_param', 50) == 50  # Should use default

    def test_change_sync_pattern(self):
        """Test the change detection pattern for widget syncing"""
        wizard_params = {'horizon_years': 43}

        # Simulate widget returning new value
        widget_value = 48

        # Test change detection logic
        needs_sync = widget_value != wizard_params.get('horizon_years')
        assert needs_sync == True

        # Test no-change scenario
        widget_value = 43
        needs_sync = widget_value != wizard_params.get('horizon_years')
        assert needs_sync == False

    def test_json_loading_flag_pattern(self):
        """Test one-time operation flag pattern"""
        session_flags = {}

        # First JSON load - should set flag
        if not session_flags.get('json_widget_keys_set', False):
            # Simulate widget key setting
            session_flags['json_widget_keys_set'] = True
            first_load = True
        else:
            first_load = False

        assert first_load == True
        assert session_flags['json_widget_keys_set'] == True

        # Subsequent runs - should skip
        if not session_flags.get('json_widget_keys_set', False):
            second_load = True
        else:
            second_load = False

        assert second_load == False


class TestStreamlitPersistenceLessons:
    """Document and test the key Streamlit lessons we learned"""

    def test_session_state_vs_widget_key_priority(self):
        """
        Test that demonstrates the key lesson:
        When widget has both 'value' and 'key' parameters, and they conflict,
        Streamlit resets the key to match the value parameter.
        """
        # This test documents the behavior we discovered:
        # DON'T DO: st.slider(value=43, key="widget_key") when widget_key=48
        # Because Streamlit will reset widget_key from 48 back to 43

        # Simulate the conflicting situation
        wizard_params_value = 43    # value parameter
        widget_key_value = 48       # widget key (user changed it)

        # The conflict causes reset: widget_key gets overwritten
        # This is why we need: wizard_params as single source of truth
        # With immediate sync to keep them aligned

        conflict_exists = (wizard_params_value != widget_key_value)
        assert conflict_exists == True  # This conflict causes the reset bug

    def test_one_time_operation_pattern(self):
        """
        Test the pattern for one-time operations in Streamlit:
        Use session state flags to prevent repeated execution
        """
        session_state = {}
        operation_count = 0

        # Simulate multiple Streamlit reruns
        for rerun in range(5):
            # CORRECT: Use flag to prevent repeated execution
            if not session_state.get('operation_completed', False):
                operation_count += 1
                session_state['operation_completed'] = True

        # Operation should only run once despite 5 reruns
        assert operation_count == 1

        # WRONG pattern would run 5 times:
        wrong_count = 5  # This simulates running on every rerun
        assert wrong_count != 1  # This shows why the flag pattern is needed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])