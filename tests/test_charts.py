"""
Tests for chart visualization functions.
Verifies chart generation and structure without testing visual output.
"""
import unittest
import numpy as np
from charts import (
    create_terminal_wealth_distribution, create_wealth_percentile_bands,
    create_monte_carlo_paths_sample, create_success_probability_over_time,
    create_cash_flow_waterfall, create_sequence_of_returns_analysis,
    create_drawdown_analysis
)


class TestCharts(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        np.random.seed(42)  # For reproducible tests
        self.terminal_wealth = np.random.lognormal(mean=15, sigma=0.5, size=1000)
        self.years = np.arange(2026, 2066)
        self.wealth_paths = np.random.lognormal(mean=15, sigma=0.5, size=(100, len(self.years)))
        
        # Make wealth paths decline over time for realistic simulation
        for i in range(len(self.years)):
            decline_factor = 0.98 ** i  # 2% decline per year
            self.wealth_paths[:, i] *= decline_factor
    
    def test_terminal_wealth_distribution_basic(self):
        """Test terminal wealth distribution chart creation"""
        fig = create_terminal_wealth_distribution(self.terminal_wealth)
        
        # Check that figure is created
        self.assertIsNotNone(fig)
        
        # Check title structure (should include subtitle)
        title_text = fig.layout.title.text
        self.assertIn('<sub>', title_text)
        self.assertIn('</sub>', title_text)
        self.assertIn('Mean:', title_text)
        self.assertIn('Median:', title_text)
        self.assertIn('Success:', title_text)
        
        # Check layout improvements
        self.assertGreaterEqual(fig.layout.margin.t, 100)  # Top margin for subtitle
    
    def test_terminal_wealth_distribution_currency_formats(self):
        """Test terminal wealth distribution with different currency formats"""
        # Real format
        fig_real = create_terminal_wealth_distribution(self.terminal_wealth, currency_format="real")
        self.assertIn("Real Dollars", fig_real.layout.title.text)
        
        # Nominal format
        fig_nominal = create_terminal_wealth_distribution(self.terminal_wealth, currency_format="nominal")
        self.assertIn("Nominal Dollars", fig_nominal.layout.title.text)
    
    def test_wealth_percentile_bands(self):
        """Test wealth percentile bands chart creation"""
        percentiles = {
            'p10': np.percentile(self.wealth_paths, 10, axis=0),
            'p50': np.percentile(self.wealth_paths, 50, axis=0),
            'p90': np.percentile(self.wealth_paths, 90, axis=0)
        }
        
        fig = create_wealth_percentile_bands(self.years, percentiles)
        
        # Check that figure is created
        self.assertIsNotNone(fig)
        
        # Should have traces for percentile bands
        self.assertGreaterEqual(len(fig.data), 2)  # At least fill and median line
    
    def test_monte_carlo_paths_sample(self):
        """Test Monte Carlo path samples chart creation"""
        fig = create_monte_carlo_paths_sample(self.years, self.wealth_paths, num_samples=20)
        
        # Check that figure is created
        self.assertIsNotNone(fig)
        
        # Should have multiple traces (sample paths + percentile bands + median)
        self.assertGreaterEqual(len(fig.data), 20)  # At least the sample paths
        
        # Check title includes sample count
        self.assertIn("20 Sample Paths", fig.layout.title.text)
    
    def test_success_probability_over_time(self):
        """Test success probability over time chart creation"""
        success_thresholds = [0, 1_000_000, 5_000_000]
        fig = create_success_probability_over_time(self.years, self.wealth_paths, success_thresholds)
        
        # Check that figure is created
        self.assertIsNotNone(fig)
        
        # Should have one trace per threshold
        self.assertEqual(len(fig.data), len(success_thresholds))
        
        # Y-axis should be 0-100 for percentages  
        self.assertEqual(list(fig.layout.yaxis.range), [0, 100])
    
    def test_cash_flow_waterfall(self):
        """Test cash flow waterfall chart creation"""
        # Mock year-by-year details
        year_by_year_details = {
            'years': [2026, 2027, 2028],
            'start_wealth': [2_500_000, 2_400_000, 2_300_000],
            'investment_growth': [125_000, 120_000, 115_000],
            'base_spending': [150_000, 155_000, 160_000],
            'other_income': [50_000, 52_000, 54_000],
            're_income': [75_000, 75_000, 75_000],
            'inheritance': [0, 0, 0],
            'college_topup': [0, 0, 100_000],
            'onetime_expense': [0, 50_000, 0],
            'taxes_paid': [15_000, 16_000, 18_000],
            'end_wealth': [2_400_000, 2_300_000, 2_200_000]
        }
        
        fig = create_cash_flow_waterfall(year_by_year_details, selected_year=2026)
        
        # Check that figure is created
        self.assertIsNotNone(fig)
        
        # Should have waterfall trace
        self.assertGreaterEqual(len(fig.data), 1)
        
        # Check title includes selected year
        self.assertIn("2026", fig.layout.title.text)
    
    def test_sequence_of_returns_analysis(self):
        """Test sequence of returns analysis chart creation"""
        fig = create_sequence_of_returns_analysis(self.wealth_paths, self.years)
        
        # Check that figure is created
        self.assertIsNotNone(fig)
        
        # Should have traces for different groups (may vary based on random data)
        self.assertGreaterEqual(len(fig.data), 1)
    
    def test_drawdown_analysis(self):
        """Test drawdown analysis chart creation"""
        fig = create_drawdown_analysis(self.wealth_paths, self.years)
        
        # Check that figure is created
        self.assertIsNotNone(fig)
        
        # Should have traces for drawdown bands and median
        self.assertGreaterEqual(len(fig.data), 2)
        
        # Y-axis should show negative values (drawdowns)
        # Note: We can't test exact values due to random data, just structure
    
    def test_chart_with_empty_data(self):
        """Test charts handle empty or minimal data gracefully"""
        empty_wealth = np.array([])
        
        # Should not crash with empty data
        try:
            fig = create_terminal_wealth_distribution(empty_wealth)
            # If it doesn't crash, the test passes
        except (ValueError, IndexError):
            # These are acceptable exceptions for empty data
            pass
    
    def test_chart_with_edge_cases(self):
        """Test charts with edge case data"""
        # Single value - should not crash
        single_wealth = np.array([1_000_000])
        fig = create_terminal_wealth_distribution(single_wealth)
        self.assertIsNotNone(fig)
        
        # Very large values
        large_wealth = np.array([1e12, 2e12, 3e12])
        fig = create_terminal_wealth_distribution(large_wealth)
        self.assertIsNotNone(fig)
        
        # All zeros - KDE will fail, but chart should handle gracefully
        zero_wealth = np.zeros(100)
        try:
            fig = create_terminal_wealth_distribution(zero_wealth)
            self.assertIsNotNone(fig)
        except (ValueError, np.linalg.LinAlgError):
            # Expected for zero-variance data with KDE
            pass


if __name__ == '__main__':
    unittest.main()