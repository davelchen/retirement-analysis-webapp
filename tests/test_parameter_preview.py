#!/usr/bin/env python3
"""
Tests for parameter preview functionality and validation.

Tests the new parameter transparency features including preview display,
validation warnings, and change detection.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation import SimulationParams
from pages.monte_carlo import (
    validate_simulation_parameters,
    get_parameter_changes,
    display_parameter_preview
)


class TestParameterPreviewValidation:
    """Test parameter preview validation logic thoroughly"""

    def test_validation_comprehensive_coverage(self):
        """Test that validation covers all major parameter categories"""

        # Create params with issues in every category
        problematic_params = SimulationParams(
            # Portfolio issues
            start_capital=50_000,         # Too low

            # Age/horizon issues
            retirement_age=70,
            horizon_years=5,              # Ends at 75 - too short

            # Allocation issues
            w_equity=0.6,
            w_bonds=0.3,
            w_real_estate=0.15,           # Total = 1.05 - bad sum
            w_cash=0.0,

            # Guardrail issues
            lower_wr=0.025,               # Backwards guardrails
            upper_wr=0.055,

            # Social Security issues
            social_security_enabled=True,
            ss_start_age=61,              # Too early

            # Simulation issues
            num_sims=200                  # Too few
        )

        warnings = validate_simulation_parameters(problematic_params)

        # Should detect all categories of issues
        assert len(warnings) >= 6, f"Should detect multiple issues: {warnings}"

        warning_text = " ".join(warnings).lower()

        # Check each category is detected
        assert any("low" in w and "capital" in w for w in warnings), "Should detect low capital"
        assert any("age" in w for w in warnings), "Should detect age/horizon issue"
        assert any("sums to" in w for w in warnings), "Should detect allocation sum issue"
        assert any("guardrail" in w for w in warnings), "Should detect guardrail issue"
        assert any("62" in w or "social security" in w.lower() for w in warnings), "Should detect SS issue"
        assert any("simulation count" in w.lower() for w in warnings), "Should detect sim count issue"

    def test_validation_edge_case_values(self):
        """Test validation at exact boundary values"""

        # Test at exact validation boundaries
        boundary_cases = [
            # Capital boundaries
            ({"start_capital": 100_000}, 0),     # Exactly at low threshold
            ({"start_capital": 99_999}, 1),      # Just below threshold
            ({"start_capital": 50_000_000}, 0),  # Exactly at high threshold
            ({"start_capital": 50_000_001}, 1),  # Just above threshold

            # Age boundaries (ending at exactly age 80)
            ({"retirement_age": 65, "horizon_years": 15}, 0),  # Exactly 80
            ({"retirement_age": 65, "horizon_years": 14}, 1),  # Age 79 - too short
            ({"retirement_age": 40, "horizon_years": 80}, 0),  # Exactly 120
            ({"retirement_age": 40, "horizon_years": 81}, 1),  # Age 121 - too long

            # SS age boundaries
            ({"social_security_enabled": True, "ss_start_age": 62}, 0),  # Exactly at minimum
            ({"social_security_enabled": True, "ss_start_age": 61}, 1),  # Just below
            ({"social_security_enabled": True, "ss_start_age": 70}, 0),  # Exactly at maximum
            ({"social_security_enabled": True, "ss_start_age": 71}, 1),  # Just above

            # Simulation count boundaries
            ({"num_sims": 1000}, 0),    # Exactly at low threshold
            ({"num_sims": 999}, 1),     # Just below
            ({"num_sims": 50000}, 0),   # Exactly at high threshold
            ({"num_sims": 50001}, 1),   # Just above
        ]

        for params_override, expected_warnings in boundary_cases:
            # Create base valid params and override specific values
            base_params = SimulationParams(
                start_capital=2_000_000,
                retirement_age=65,
                horizon_years=30,
                lower_wr=0.05,  # Correct order
                upper_wr=0.03,
                social_security_enabled=False,  # Avoid SS warnings unless testing
                num_sims=10_000
            )

            # Apply override
            for key, value in params_override.items():
                setattr(base_params, key, value)

            warnings = validate_simulation_parameters(base_params)

            assert len(warnings) == expected_warnings, \
                f"Boundary case {params_override} should have {expected_warnings} warnings, got {len(warnings)}: {warnings}"

    def test_validation_interaction_effects(self):
        """Test validation when multiple parameters interact"""

        # Test retirement age + horizon interaction
        cases = [
            # Young retirement, long horizon (OK)
            (45, 50, False),  # Age 45 + 50 years = 95 (reasonable)

            # Old retirement, short horizon (warning about short planning)
            (70, 5, True),   # Age 70 + 5 years = 75 (too short)

            # Young retirement, extremely long horizon (warning about too long)
            (30, 95, True),  # Age 30 + 95 years = 125 (too long)

            # Normal retirement, normal horizon (OK)
            (65, 25, False), # Age 65 + 25 years = 90 (good)
        ]

        for retirement_age, horizon_years, should_warn in cases:
            params = SimulationParams(
                retirement_age=retirement_age,
                horizon_years=horizon_years,
                lower_wr=0.05,  # Correct order
                upper_wr=0.03
            )

            warnings = validate_simulation_parameters(params)
            age_warnings = [w for w in warnings if "age" in w.lower()]

            if should_warn:
                assert len(age_warnings) > 0, f"Should warn about retirement age {retirement_age} + horizon {horizon_years}"
            else:
                assert len(age_warnings) == 0, f"Should not warn about retirement age {retirement_age} + horizon {horizon_years}: {age_warnings}"

    def test_validation_performance_with_large_inputs(self):
        """Test that validation performs well with extreme input values"""

        # Very large numbers
        extreme_params = SimulationParams(
            start_capital=999_999_999_999,  # Trillion dollars
            horizon_years=200,              # 200 years
            num_sims=1_000_000,            # Million simulations
            w_equity=0.999999,             # Near 100%
            lower_wr=0.999,                # 99.9%
            upper_wr=0.000001              # Near zero
        )

        # Should complete quickly without errors
        import time
        start_time = time.time()
        warnings = validate_simulation_parameters(extreme_params)
        end_time = time.time()

        # Should be very fast (< 100ms)
        assert end_time - start_time < 0.1, "Validation should be fast even with extreme values"

        # Should detect the obvious issues
        assert len(warnings) > 0, "Should detect issues with extreme values"


class TestParameterChangeDetection:
    """Test parameter change detection and formatting"""

    def test_change_detection_precision(self):
        """Test that changes are detected with proper precision"""

        old_params = SimulationParams(
            start_capital=1_000_000,
            w_equity=0.650000,    # Test floating point precision
            lower_wr=0.045000,
            retirement_age=65
        )

        # Test tiny changes (should be detected)
        new_params_tiny = SimulationParams(
            start_capital=1_000_001,  # $1 difference
            w_equity=0.650001,        # 0.0001% difference
            lower_wr=0.045001,        # 0.001% difference
            retirement_age=65         # No change
        )

        changes = get_parameter_changes(old_params, new_params_tiny)

        # Should detect even tiny changes
        assert len(changes) >= 3, f"Should detect tiny changes: {changes}"

        # Test no changes (identical values)
        changes_none = get_parameter_changes(old_params, old_params)
        assert len(changes_none) == 0, "Identical params should show no changes"

    def test_change_formatting_edge_cases(self):
        """Test change formatting with edge case values"""

        old_params = SimulationParams(
            start_capital=0,           # Zero capital
            w_equity=0.0,             # Zero allocation
            ss_annual_benefit=0,      # Zero SS
            retirement_age=30         # Young retirement
        )

        new_params = SimulationParams(
            start_capital=999_999_999, # Very large capital
            w_equity=1.0,             # 100% allocation
            ss_annual_benefit=200_000, # Large SS benefit
            retirement_age=75         # Late retirement
        )

        changes = get_parameter_changes(old_params, new_params)

        # Check formatting handles edge cases
        change_text = " ".join(changes)

        # Large number formatting
        assert "$999,999,999" in change_text, "Should format large numbers with commas"

        # Zero formatting
        assert "$0" in change_text, "Should handle zero values"

        # Percentage formatting (0% to 100%)
        assert "0.0% → 100.0%" in change_text, "Should handle extreme percentage ranges"

    def test_change_detection_all_parameter_types(self):
        """Test that all tracked parameter types are detected"""

        # Create params with different types of values
        old_params = SimulationParams(
            start_capital=1_000_000,     # Currency
            retirement_age=65,           # Integer
            horizon_years=30,            # Integer with "years" unit
            num_sims=10_000,            # Integer with comma formatting
            w_equity=0.60,              # Percentage
            w_bonds=0.25,               # Percentage
            ss_annual_benefit=35_000,   # Currency
            ss_start_age=67,            # Integer
            lower_wr=0.045,             # Percentage
            upper_wr=0.028              # Percentage
        )

        # Change every tracked parameter
        new_params = SimulationParams(
            start_capital=2_500_000,
            retirement_age=62,
            horizon_years=40,
            num_sims=25_000,
            w_equity=0.70,
            w_bonds=0.20,
            ss_annual_benefit=45_000,
            ss_start_age=70,
            lower_wr=0.050,
            upper_wr=0.030
        )

        changes = get_parameter_changes(old_params, new_params)

        # Should detect all 10 changes
        assert len(changes) == 10, f"Should detect all parameter changes: {changes}"

        # Verify specific formatting for each type
        change_text = " ".join(changes)

        # Currency formatting
        assert "$1,000,000 → $2,500,000" in change_text, "Should format start capital"
        assert "$35,000 → $45,000" in change_text, "Should format SS benefit"

        # Integer formatting
        assert "65 → 62" in change_text, "Should format retirement age"
        assert "67 → 70" in change_text, "Should format SS start age"

        # Years formatting
        assert "30 years → 40 years" in change_text, "Should format horizon"

        # Comma formatting for large numbers
        assert "10,000 → 25,000" in change_text, "Should format simulation count"

        # Percentage formatting
        assert "60.0% → 70.0%" in change_text, "Should format equity percentage"
        assert "4.5% → 5.0%" in change_text, "Should format lower guardrail"

    def test_parameter_change_with_partial_attributes(self):
        """Test change detection with objects that have only some attributes"""

        # Create objects with only specific attributes (like real use case)
        class PartialParams:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        old_params = PartialParams(start_capital=1_000_000, retirement_age=65)
        new_params = PartialParams(start_capital=2_000_000, retirement_age=67)

        # Should handle missing attributes gracefully
        changes = get_parameter_changes(old_params, new_params)

        # Should only detect changes for existing attributes
        assert len(changes) == 2, f"Should handle partial attributes: {changes}"

        change_text = " ".join(changes)
        assert "$1,000,000 → $2,000,000" in change_text
        assert "65 → 67" in change_text


class TestParameterPreviewFunctionality:
    """Test parameter preview core functionality without complex mocking"""

    def test_parameter_preview_functions_exist(self):
        """Test that parameter preview functions are properly defined"""

        # Test that functions exist and are callable
        assert callable(display_parameter_preview), "display_parameter_preview should be callable"
        assert callable(validate_simulation_parameters), "validate_simulation_parameters should be callable"
        assert callable(get_parameter_changes), "get_parameter_changes should be callable"

    def test_parameter_preview_error_handling(self):
        """Test parameter preview handles errors gracefully"""

        # Test that validation function doesn't crash with None
        try:
            warnings = validate_simulation_parameters(None)
            # Should return empty list or handle gracefully
            assert isinstance(warnings, list), "Should return list even with None input"
        except Exception as e:
            # If it raises an exception, it should be a specific known type
            assert isinstance(e, (TypeError, AttributeError)), f"Should handle None gracefully, got {type(e)}"

    def test_parameter_preview_components_work_individually(self):
        """Test that individual components work correctly"""

        # Test validation with simple valid params
        simple_params = SimulationParams(start_capital=1_000_000)
        warnings = validate_simulation_parameters(simple_params)
        assert isinstance(warnings, list), "Validation should return a list"

        # Test change detection with simple params
        params1 = SimulationParams(start_capital=1_000_000)
        params2 = SimulationParams(start_capital=2_000_000)
        changes = get_parameter_changes(params1, params2)
        assert isinstance(changes, list), "Change detection should return a list"
        assert len(changes) > 0, "Should detect the capital change"


class TestParameterPreviewIntegration:
    """Integration tests for parameter preview functionality"""

    def test_validation_with_real_simulation_params(self):
        """Test validation works with actual SimulationParams from different scenarios"""

        # Test scenarios from real use cases
        scenarios = [
            # Conservative retiree
            SimulationParams(
                start_capital=1_500_000,
                retirement_age=67,
                horizon_years=25,
                w_equity=0.40,
                w_bonds=0.50,
                w_real_estate=0.05,
                w_cash=0.05,
                lower_wr=0.04,
                upper_wr=0.025,
                social_security_enabled=True,
                ss_annual_benefit=30_000,
                ss_start_age=67
            ),

            # Aggressive FIRE scenario
            SimulationParams(
                start_capital=3_000_000,
                retirement_age=45,
                horizon_years=45,
                w_equity=0.90,
                w_bonds=0.10,
                w_real_estate=0.0,
                w_cash=0.0,
                lower_wr=0.05,
                upper_wr=0.02,
                social_security_enabled=True,
                ss_annual_benefit=25_000,
                ss_start_age=62
            ),

            # High net worth scenario
            SimulationParams(
                start_capital=10_000_000,
                retirement_age=62,
                horizon_years=35,
                w_equity=0.65,
                w_bonds=0.25,
                w_real_estate=0.10,
                w_cash=0.0,
                lower_wr=0.045,
                upper_wr=0.035,
                social_security_enabled=True,
                ss_annual_benefit=50_000,
                ss_start_age=70
            )
        ]

        for i, params in enumerate(scenarios):
            warnings = validate_simulation_parameters(params)

            # These realistic scenarios should have minimal warnings
            major_warnings = [w for w in warnings if any(term in w.lower()
                             for term in ['very', 'too', 'must', 'should'])]

            assert len(major_warnings) <= 1, f"Scenario {i+1} should be mostly valid: {major_warnings}"

    def test_change_detection_workflow(self):
        """Test full workflow of parameter changes over time"""

        # Start with initial params
        initial_params = SimulationParams(
            start_capital=2_000_000,
            retirement_age=65,
            w_equity=0.60
        )

        # Series of changes
        changes_sequence = [
            # Change 1: Increase capital
            {"start_capital": 2_500_000},

            # Change 2: Adjust allocation
            {"w_equity": 0.70, "w_bonds": 0.15},

            # Change 3: Change retirement age
            {"retirement_age": 62},

            # Change 4: Multiple changes
            {"start_capital": 3_000_000, "w_equity": 0.80, "retirement_age": 60}
        ]

        current_params = initial_params

        for i, change_dict in enumerate(changes_sequence):
            # Apply changes
            new_params = SimulationParams(**{**current_params.__dict__, **change_dict})

            # Detect changes
            changes = get_parameter_changes(current_params, new_params)

            # Should detect the expected number of changes
            expected_change_count = len(change_dict)
            assert len(changes) == expected_change_count, \
                f"Step {i+1}: Expected {expected_change_count} changes, got {len(changes)}: {changes}"

            # Move to next iteration
            current_params = new_params

    def test_validation_covers_all_simulation_params_fields(self):
        """Test that validation considers all important SimulationParams fields"""

        # Get all fields from SimulationParams
        sample_params = SimulationParams()
        all_fields = set(sample_params.__dict__.keys())

        # Fields that validation should check (critical ones)
        should_validate = {
            'start_capital', 'retirement_age', 'horizon_years',
            'lower_wr', 'upper_wr', 'w_equity', 'w_bonds', 'w_real_estate', 'w_cash',
            'social_security_enabled', 'ss_start_age', 'num_sims'
        }

        # Create params with issues in all these fields
        test_params = SimulationParams(
            start_capital=10_000,        # Too low
            retirement_age=75,           # Short horizon
            horizon_years=3,             # Too short (age 78)
            lower_wr=0.02,              # Backwards
            upper_wr=0.06,              # Backwards
            w_equity=0.5,
            w_bonds=0.3,
            w_real_estate=0.3,          # Sum > 1.0
            w_cash=0.0,
            social_security_enabled=True,
            ss_start_age=61,            # Too early
            num_sims=100                # Too few
        )

        warnings = validate_simulation_parameters(test_params)

        # Should detect issues in most categories
        assert len(warnings) >= 5, f"Should validate major fields: {warnings}"

        # Verify coverage by checking warning content
        warning_text = " ".join(warnings).lower()
        coverage_checks = [
            ("capital", ["low", "capital"]),
            ("allocation", ["sums to", "allocation"]),
            ("horizon", ["age", "horizon", "short", "long"]),
            ("guardrails", ["guardrail", "lower", "upper"]),
            ("social security", ["62", "social security", "start age"]),
            ("simulations", ["simulation count", "low"])
        ]

        covered_categories = 0
        for category, keywords in coverage_checks:
            if any(keyword in warning_text for keyword in keywords):
                covered_categories += 1

        assert covered_categories >= 4, f"Should cover most validation categories. Got {covered_categories}/6"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])