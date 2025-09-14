"""
Unit tests for tax_utils.py helper functions (state tax and Social Security).
"""
import pytest
from tax_utils import get_state_tax_rates, calculate_social_security_benefit


class TestStateTaxRates:
    """Test state tax rate functionality"""

    def test_get_state_tax_rates_ca_mfj(self):
        """Test California MFJ tax rates"""
        rates = get_state_tax_rates('CA', 'MFJ')
        expected = [(0, 0.13), (94_300, 0.31), (201_000, 0.36)]
        assert rates == expected

    def test_get_state_tax_rates_ca_single(self):
        """Test California Single tax rates"""
        rates = get_state_tax_rates('CA', 'Single')
        expected = [(0, 0.13), (47_150, 0.31), (100_500, 0.36)]
        assert rates == expected

    def test_get_state_tax_rates_tx_no_state_tax(self):
        """Test Texas (no state tax) rates"""
        rates = get_state_tax_rates('TX', 'MFJ')
        expected = [(0, 0.10), (94_300, 0.22), (201_000, 0.24)]
        assert rates == expected

    def test_get_state_tax_rates_fl_no_state_tax(self):
        """Test Florida (no state tax) rates"""
        rates = get_state_tax_rates('FL', 'Single')
        expected = [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        assert rates == expected

    def test_get_state_tax_rates_ny_high_tax(self):
        """Test New York high tax rates"""
        rates = get_state_tax_rates('NY', 'MFJ')
        expected = [(0, 0.14), (94_300, 0.30), (201_000, 0.35)]
        assert rates == expected

    def test_get_state_tax_rates_pa_moderate(self):
        """Test Pennsylvania moderate tax rates"""
        rates = get_state_tax_rates('PA', 'Single')
        expected = [(0, 0.13), (47_150, 0.25), (100_500, 0.27)]
        assert rates == expected

    def test_get_state_tax_rates_unknown_state_defaults_to_federal(self):
        """Test unknown state defaults to federal only"""
        rates = get_state_tax_rates('UNKNOWN', 'MFJ')
        expected = [(0, 0.10), (94_300, 0.22), (201_000, 0.24)]
        assert rates == expected

    def test_all_states_have_both_filing_statuses(self):
        """Test all defined states have both MFJ and Single rates"""
        states = ['Federal Only', 'CA', 'NY', 'TX', 'FL', 'WA', 'NV', 'PA', 'OH', 'IL']
        for state in states:
            mfj_rates = get_state_tax_rates(state, 'MFJ')
            single_rates = get_state_tax_rates(state, 'Single')

            # Should have 3 brackets each
            assert len(mfj_rates) == 3
            assert len(single_rates) == 3

            # Each bracket should be (threshold, rate) tuple
            for threshold, rate in mfj_rates:
                assert isinstance(threshold, (int, float))
                assert isinstance(rate, float)
                assert 0 <= rate <= 0.5  # Reasonable tax rate range

            for threshold, rate in single_rates:
                assert isinstance(threshold, (int, float))
                assert isinstance(rate, float)
                assert 0 <= rate <= 0.5


class TestSocialSecurityBenefit:
    """Test Social Security benefit calculation"""

    def test_ss_benefit_before_start_age(self):
        """Test no benefit before start age"""
        benefit = calculate_social_security_benefit(
            year=2030, start_year=2026, annual_benefit=40000,
            scenario='moderate', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        # Age 69 in 2030 (65 + 4), should get benefit
        assert benefit == 40000

        benefit = calculate_social_security_benefit(
            year=2028, start_year=2026, annual_benefit=40000,
            scenario='moderate', custom_reduction=0.1,
            reduction_start_year=2034, start_age=69  # Start at 69
        )
        # Age 67 in 2028 (65 + 2), before start age 69, should get nothing
        assert benefit == 0

        benefit = calculate_social_security_benefit(
            year=2030, start_year=2026, annual_benefit=40000,
            scenario='moderate', custom_reduction=0.1,
            reduction_start_year=2034, start_age=69  # Start at 69
        )
        # Age 69 in 2030 (65 + 4), exactly at start age 69, should get benefit
        assert benefit == 40000

    def test_ss_benefit_conservative_scenario(self):
        """Test conservative scenario with 19% cut"""
        # Before cuts
        benefit = calculate_social_security_benefit(
            year=2033, start_year=2026, annual_benefit=40000,
            scenario='conservative', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        assert benefit == 40000

        # After cuts start
        benefit = calculate_social_security_benefit(
            year=2035, start_year=2026, annual_benefit=40000,
            scenario='conservative', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        expected = 40000 * (1 - 0.19)  # 19% cut
        assert abs(benefit - expected) < 0.01

    def test_ss_benefit_moderate_scenario(self):
        """Test moderate scenario with gradual cuts"""
        # Before cuts
        benefit = calculate_social_security_benefit(
            year=2033, start_year=2026, annual_benefit=40000,
            scenario='moderate', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        assert benefit == 40000

        # First year of cuts (2034) - should be 5% + 0% = 5%
        benefit = calculate_social_security_benefit(
            year=2034, start_year=2026, annual_benefit=40000,
            scenario='moderate', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        expected = 40000 * (1 - 0.05)  # 5% cut in first year
        assert abs(benefit - expected) < 0.01

        # Second year of cuts (2035) - should be 5% + 1% = 6%
        benefit = calculate_social_security_benefit(
            year=2035, start_year=2026, annual_benefit=40000,
            scenario='moderate', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        expected = 40000 * (1 - 0.06)  # 6% cut
        assert abs(benefit - expected) < 0.01

        # Many years later - should cap at 10%
        benefit = calculate_social_security_benefit(
            year=2050, start_year=2026, annual_benefit=40000,
            scenario='moderate', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        expected = 40000 * (1 - 0.10)  # 10% cap
        assert abs(benefit - expected) < 0.01

    def test_ss_benefit_optimistic_scenario(self):
        """Test optimistic scenario with no cuts"""
        # Before cuts
        benefit = calculate_social_security_benefit(
            year=2033, start_year=2026, annual_benefit=40000,
            scenario='optimistic', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        assert benefit == 40000

        # After cuts would start - no reduction
        benefit = calculate_social_security_benefit(
            year=2040, start_year=2026, annual_benefit=40000,
            scenario='optimistic', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        assert benefit == 40000

    def test_ss_benefit_custom_scenario(self):
        """Test custom scenario with user-defined reduction"""
        custom_reduction = 0.15  # 15% custom cut

        # Before cuts
        benefit = calculate_social_security_benefit(
            year=2033, start_year=2026, annual_benefit=50000,
            scenario='custom', custom_reduction=custom_reduction,
            reduction_start_year=2034, start_age=67
        )
        assert benefit == 50000

        # After cuts start
        benefit = calculate_social_security_benefit(
            year=2035, start_year=2026, annual_benefit=50000,
            scenario='custom', custom_reduction=custom_reduction,
            reduction_start_year=2034, start_age=67
        )
        expected = 50000 * (1 - 0.15)  # 15% custom cut
        assert abs(benefit - expected) < 0.01

    def test_ss_benefit_different_start_years(self):
        """Test different retirement start years"""
        # Start retirement in 2030
        benefit = calculate_social_security_benefit(
            year=2037, start_year=2030, annual_benefit=35000,
            scenario='moderate', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        # Age 74 in 2037, after cuts started in 2034
        # 3 years since cuts: 5% + 3*1% = 8%
        expected = 35000 * (1 - 0.08)
        assert abs(benefit - expected) < 0.01

    def test_ss_benefit_edge_cases(self):
        """Test edge cases and boundary conditions"""
        # Zero benefit amount
        benefit = calculate_social_security_benefit(
            year=2035, start_year=2026, annual_benefit=0,
            scenario='conservative', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        assert benefit == 0

        # Very high benefit amount
        benefit = calculate_social_security_benefit(
            year=2030, start_year=2026, annual_benefit=100000,
            scenario='optimistic', custom_reduction=0.1,
            reduction_start_year=2034, start_age=67
        )
        assert benefit == 100000

        # Custom reduction of 0 (no cuts)
        benefit = calculate_social_security_benefit(
            year=2040, start_year=2026, annual_benefit=40000,
            scenario='custom', custom_reduction=0.0,
            reduction_start_year=2034, start_age=67
        )
        assert benefit == 40000

        # Maximum custom reduction
        benefit = calculate_social_security_benefit(
            year=2040, start_year=2026, annual_benefit=40000,
            scenario='custom', custom_reduction=0.5,  # 50% cut
            reduction_start_year=2034, start_age=67
        )
        expected = 40000 * (1 - 0.5)
        assert abs(benefit - expected) < 0.01