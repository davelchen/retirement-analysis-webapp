"""
Unit tests for tax calculation and gross-up solver.
"""
import pytest
import numpy as np
from tax import (
    calculate_tax, solve_gross_withdrawal, gross_up_withdrawal,
    effective_tax_rate, marginal_tax_rate
)


class TestCalculateTax:
    """Test progressive tax calculation"""
    
    def test_no_tax_on_zero_income(self):
        """Test that zero taxable income yields zero tax"""
        brackets = [(0, 0.10), (50_000, 0.22), (100_000, 0.24)]
        tax = calculate_tax(0, brackets)
        assert tax == 0
    
    def test_negative_income_yields_zero_tax(self):
        """Test that negative taxable income yields zero tax"""
        brackets = [(0, 0.10), (50_000, 0.22), (100_000, 0.24)]
        tax = calculate_tax(-1000, brackets)
        assert tax == 0
    
    def test_single_bracket_tax(self):
        """Test tax calculation within first bracket"""
        brackets = [(0, 0.10), (50_000, 0.22), (100_000, 0.24)]
        tax = calculate_tax(30_000, brackets)
        expected = 30_000 * 0.10
        assert abs(tax - expected) < 1e-6
    
    def test_two_bracket_tax(self):
        """Test tax calculation spanning two brackets"""
        brackets = [(0, 0.10), (50_000, 0.22), (100_000, 0.24)]
        taxable_income = 75_000
        
        # First bracket: 50,000 * 0.10 = 5,000
        # Second bracket: (75,000 - 50,000) * 0.22 = 5,500
        # Total: 10,500
        expected = 50_000 * 0.10 + 25_000 * 0.22
        tax = calculate_tax(taxable_income, brackets)
        
        assert abs(tax - expected) < 1e-6
        assert abs(tax - 10_500) < 1e-6
    
    def test_three_bracket_tax(self):
        """Test tax calculation spanning three brackets"""
        brackets = [(0, 0.10), (50_000, 0.22), (100_000, 0.24)]
        taxable_income = 150_000
        
        # First bracket: 50,000 * 0.10 = 5,000
        # Second bracket: 50,000 * 0.22 = 11,000  
        # Third bracket: 50,000 * 0.24 = 12,000
        # Total: 28,000
        expected = 50_000 * 0.10 + 50_000 * 0.22 + 50_000 * 0.24
        tax = calculate_tax(taxable_income, brackets)
        
        assert abs(tax - expected) < 1e-6
        assert abs(tax - 28_000) < 1e-6
    
    def test_income_exceeds_all_brackets(self):
        """Test tax calculation when income exceeds all brackets"""
        brackets = [(0, 0.10), (50_000, 0.22), (100_000, 0.24)]
        taxable_income = 200_000
        
        # All brackets plus highest rate on remainder
        # First: 50,000 * 0.10 = 5,000
        # Second: 50,000 * 0.22 = 11,000
        # Remainder: 100,000 * 0.24 = 24,000
        # Total: 40,000
        expected = 50_000 * 0.10 + 50_000 * 0.22 + 100_000 * 0.24
        tax = calculate_tax(taxable_income, brackets)
        
        assert abs(tax - expected) < 1e-6
        assert abs(tax - 40_000) < 1e-6
    
    def test_empty_brackets(self):
        """Test behavior with empty tax brackets"""
        tax = calculate_tax(50_000, [])
        assert tax == 0
    
    def test_single_bracket_only(self):
        """Test with only one tax bracket"""
        brackets = [(0, 0.15)]
        tax = calculate_tax(100_000, brackets)
        expected = 100_000 * 0.15
        assert abs(tax - expected) < 1e-6


class TestSolveGrossWithdrawal:
    """Test gross withdrawal solver"""
    
    def test_zero_net_need(self):
        """Test that zero net need yields zero withdrawal and tax"""
        brackets = [(0, 0.10), (50_000, 0.22)]
        gross, taxes = solve_gross_withdrawal(0, 0, 25_000, brackets)
        
        assert gross == 0
        assert taxes == 0
    
    def test_negative_net_need(self):
        """Test that negative net need yields zero withdrawal and tax"""
        brackets = [(0, 0.10), (50_000, 0.22)]
        gross, taxes = solve_gross_withdrawal(-5000, 0, 25_000, brackets)
        
        assert gross == 0
        assert taxes == 0
    
    def test_simple_gross_up_no_tax(self):
        """Test gross-up when standard deduction covers all income"""
        brackets = [(0, 0.10), (50_000, 0.22)]
        standard_deduction = 50_000
        net_need = 40_000
        
        gross, taxes = solve_gross_withdrawal(net_need, 0, standard_deduction, brackets)
        
        # Since gross withdrawal (40k) < standard deduction (50k), no tax
        assert abs(gross - 40_000) < 100  # Allow small tolerance for solver
        assert taxes < 100  # Should be near zero
    
    def test_gross_up_with_tax(self):
        """Test gross-up when withdrawal exceeds standard deduction"""
        brackets = [(0, 0.10), (50_000, 0.22)]
        standard_deduction = 25_000
        net_need = 40_000
        
        gross, taxes = solve_gross_withdrawal(net_need, 0, standard_deduction, brackets)
        
        # Verify the constraint: gross - taxes = net_need
        net_received = gross - taxes
        assert abs(net_received - net_need) < 1  # Within $1 tolerance
        
        # Should have positive taxes since gross > standard deduction
        assert taxes > 0
        assert gross > net_need  # Gross should exceed net due to taxes
    
    def test_gross_up_with_other_income(self):
        """Test gross-up solver with other taxable income"""
        brackets = [(0, 0.10), (50_000, 0.22)]
        standard_deduction = 25_000
        net_need = 30_000
        other_taxable = 20_000
        
        gross, taxes = solve_gross_withdrawal(net_need, other_taxable, standard_deduction, brackets)
        
        # Verify constraint
        net_received = gross - taxes
        assert abs(net_received - net_need) < 1
        
        # Taxes should be based on total AGI (gross + other_taxable)
        total_agi = gross + other_taxable
        taxable_income = max(0, total_agi - standard_deduction)
        expected_tax = calculate_tax(taxable_income, brackets)
        assert abs(taxes - expected_tax) < 1
    
    def test_high_tax_scenario(self):
        """Test gross-up in high tax scenario"""
        brackets = [(0, 0.10), (50_000, 0.22), (100_000, 0.32)]
        standard_deduction = 25_000
        net_need = 100_000
        
        gross, taxes = solve_gross_withdrawal(net_need, 0, standard_deduction, brackets)
        
        # Verify constraint
        net_received = gross - taxes
        assert abs(net_received - net_need) < 1
        
        # In high tax scenario, gross should be higher than net
        assert gross > net_need  # Should be higher due to taxes
        assert taxes > 10_000   # Should have substantial taxes
        assert gross < 150_000  # But not unreasonably high
    
    def test_solver_convergence(self):
        """Test that solver converges within tolerance"""
        brackets = [(0, 0.12), (40_000, 0.24), (80_000, 0.32)]
        standard_deduction = 30_000
        net_need = 75_000
        
        gross, taxes = solve_gross_withdrawal(
            net_need, 0, standard_deduction, brackets, 
            tolerance=1e-4, max_iterations=50
        )
        
        # Verify tight convergence
        net_received = gross - taxes
        assert abs(net_received - net_need) < 1e-3


class TestGrossUpWithdrawal:
    """Test convenience wrapper function"""
    
    def test_default_mfj_brackets(self):
        """Test gross-up with default MFJ brackets"""
        net_need = 50_000
        gross, taxes = gross_up_withdrawal(net_need, filing_status="MFJ")
        
        net_received = gross - taxes
        assert abs(net_received - net_need) < 1
        assert gross >= net_need  # Should be at least as much due to taxes
    
    def test_default_single_brackets(self):
        """Test gross-up with default Single brackets"""
        net_need = 50_000
        gross, taxes = gross_up_withdrawal(net_need, filing_status="Single")
        
        net_received = gross - taxes
        assert abs(net_received - net_need) < 1
        assert gross >= net_need
    
    def test_custom_brackets(self):
        """Test gross-up with custom tax brackets"""
        net_need = 40_000
        custom_brackets = [(0, 0.15), (60_000, 0.25)]
        
        gross, taxes = gross_up_withdrawal(
            net_need, 
            custom_brackets=custom_brackets,
            standard_deduction=20_000
        )
        
        net_received = gross - taxes
        assert abs(net_received - net_need) < 1


class TestTaxRates:
    """Test effective and marginal tax rate calculations"""
    
    def test_effective_tax_rate(self):
        """Test effective tax rate calculation"""
        brackets = [(0, 0.10), (50_000, 0.22)]
        standard_deduction = 25_000
        gross_income = 100_000
        
        # Taxable income = 100,000 - 25,000 = 75,000
        # Tax = 50,000 * 0.10 + 25,000 * 0.22 = 5,000 + 5,500 = 10,500
        # Effective rate = 10,500 / 100,000 = 10.5%
        
        rate = effective_tax_rate(gross_income, standard_deduction, brackets)
        expected_rate = 10_500 / 100_000
        assert abs(rate - expected_rate) < 1e-6
        assert abs(rate - 0.105) < 1e-6
    
    def test_effective_rate_no_tax(self):
        """Test effective rate when income below standard deduction"""
        brackets = [(0, 0.10), (50_000, 0.22)]
        standard_deduction = 50_000
        gross_income = 30_000
        
        rate = effective_tax_rate(gross_income, standard_deduction, brackets)
        assert rate == 0
    
    def test_effective_rate_zero_income(self):
        """Test effective rate on zero income"""
        brackets = [(0, 0.10)]
        rate = effective_tax_rate(0, 25_000, brackets)
        assert rate == 0
    
    def test_marginal_tax_rate(self):
        """Test marginal tax rate calculation"""
        brackets = [(0, 0.10), (50_000, 0.22), (100_000, 0.32)]
        standard_deduction = 25_000
        
        # Income below standard deduction
        rate = marginal_tax_rate(20_000, standard_deduction, brackets)
        assert rate == 0
        
        # Income in first bracket (taxable income = 40,000 - 25,000 = 15,000)
        rate = marginal_tax_rate(40_000, standard_deduction, brackets)
        assert rate == 0.10
        
        # Income in second bracket (taxable income = 80,000 - 25,000 = 55,000)
        rate = marginal_tax_rate(80_000, standard_deduction, brackets)
        assert rate == 0.22
        
        # Income in third bracket (taxable income = 150,000 - 25,000 = 125,000)
        rate = marginal_tax_rate(150_000, standard_deduction, brackets)
        assert rate == 0.32
    
    def test_marginal_rate_above_all_brackets(self):
        """Test marginal rate when income exceeds all brackets"""
        brackets = [(0, 0.10), (50_000, 0.22)]
        standard_deduction = 25_000
        gross_income = 200_000  # Taxable = 175,000, above all brackets
        
        rate = marginal_tax_rate(gross_income, standard_deduction, brackets)
        assert rate == 0.22  # Highest bracket rate
    
    def test_marginal_rate_empty_brackets(self):
        """Test marginal rate with empty brackets"""
        rate = marginal_tax_rate(50_000, 25_000, [])
        assert rate == 0