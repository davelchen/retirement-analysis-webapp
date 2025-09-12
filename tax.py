"""
Simplified AGI-based tax model with progressive brackets.
Includes gross-up solver to determine withdrawal amounts that meet spending needs after taxes.
"""
from typing import List, Tuple
import numpy as np


def calculate_tax(taxable_income: float, tax_brackets: List[Tuple[float, float]]) -> float:
    """
    Calculate tax using progressive brackets.
    
    Args:
        taxable_income: Income subject to tax (AGI - standard deduction)
        tax_brackets: List of (threshold, rate) tuples where threshold is the START of each bracket
        
    Returns:
        Total tax owed
    """
    if taxable_income <= 0:
        return 0.0
    
    if not tax_brackets:
        return 0.0
    
    tax = 0.0
    
    # Sort brackets by threshold to ensure proper order
    sorted_brackets = sorted(tax_brackets, key=lambda x: x[0])
    
    for i, (threshold, rate) in enumerate(sorted_brackets):
        # Calculate the upper limit of this bracket
        if i + 1 < len(sorted_brackets):
            upper_limit = sorted_brackets[i + 1][0]
        else:
            upper_limit = float('inf')  # No upper limit for highest bracket
        
        # Calculate income taxed in this bracket
        income_in_bracket = max(0, min(taxable_income, upper_limit) - threshold)
        
        if income_in_bracket > 0:
            tax += income_in_bracket * rate
    
    return max(0.0, tax)


def solve_gross_withdrawal(net_need: float, 
                          other_taxable_income: float,
                          standard_deduction: float,
                          tax_brackets: List[Tuple[float, float]],
                          tolerance: float = 1e-6,
                          max_iterations: int = 100) -> Tuple[float, float]:
    """
    Solve for gross withdrawal W such that W - tax(W + other_taxable - std_deduction) = net_need.
    
    Uses bisection method for robust convergence.
    
    Args:
        net_need: After-tax spending requirement
        other_taxable_income: Other taxable income to include in AGI
        standard_deduction: Standard deduction amount
        tax_brackets: Progressive tax brackets
        tolerance: Convergence tolerance
        max_iterations: Maximum iterations
        
    Returns:
        (gross_withdrawal, taxes_paid)
    """
    if net_need <= 0:
        return 0.0, 0.0
    
    def tax_function(W: float) -> float:
        """Calculate taxes on total AGI"""
        agi = W + other_taxable_income
        taxable_income = max(0.0, agi - standard_deduction)
        return calculate_tax(taxable_income, tax_brackets)
    
    def net_function(W: float) -> float:
        """Calculate net amount after taxes"""
        return W - tax_function(W)
    
    def residual(W: float) -> float:
        """Residual function for bisection: net_function(W) - net_need"""
        return net_function(W) - net_need
    
    # Initial bounds for bisection
    # Lower bound: net_need (assumes zero tax)
    W_low = net_need
    
    # Upper bound: generous estimate assuming high tax rate
    max_tax_rate = tax_brackets[-1][1] if tax_brackets else 0.5
    W_high = net_need / (1 - max_tax_rate * 1.2)  # 20% buffer
    
    # Ensure bounds bracket the solution
    if residual(W_low) > 0:
        # Net need is already satisfied at lower bound
        taxes = tax_function(W_low)
        return W_low, taxes
    
    # Expand upper bound if needed
    iteration = 0
    while residual(W_high) < 0 and iteration < 20:
        W_high *= 2
        iteration += 1
    
    if residual(W_high) < 0:
        # Fallback: use high estimate
        taxes = tax_function(W_high)
        return W_high, taxes
    
    # Bisection method
    for _ in range(max_iterations):
        W_mid = (W_low + W_high) / 2
        residual_mid = residual(W_mid)
        
        if abs(residual_mid) < tolerance:
            taxes = tax_function(W_mid)
            return W_mid, taxes
        
        if residual_mid < 0:
            W_low = W_mid
        else:
            W_high = W_mid
    
    # Return best estimate
    W_final = (W_low + W_high) / 2
    taxes = tax_function(W_final)
    return W_final, taxes


def gross_up_withdrawal(net_need: float,
                       filing_status: str = "MFJ",
                       standard_deduction: float = 29_200,
                       custom_brackets: List[Tuple[float, float]] = None) -> Tuple[float, float]:
    """
    Convenience function to gross up a net spending need.
    
    Args:
        net_need: After-tax spending requirement
        filing_status: "MFJ" or "Single"
        standard_deduction: Standard deduction amount
        custom_brackets: Custom tax brackets, or None for defaults
        
    Returns:
        (gross_withdrawal, taxes_paid)
    """
    if custom_brackets is None:
        if filing_status == "MFJ":
            tax_brackets = [(0, 0.10), (94_300, 0.22), (201_000, 0.24)]
        else:  # Single
            tax_brackets = [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
    else:
        tax_brackets = custom_brackets
    
    return solve_gross_withdrawal(
        net_need=net_need,
        other_taxable_income=0.0,
        standard_deduction=standard_deduction,
        tax_brackets=tax_brackets
    )


def effective_tax_rate(gross_income: float,
                      standard_deduction: float,
                      tax_brackets: List[Tuple[float, float]]) -> float:
    """
    Calculate effective tax rate on gross income.
    
    Args:
        gross_income: Total gross income
        standard_deduction: Standard deduction amount  
        tax_brackets: Progressive tax brackets
        
    Returns:
        Effective tax rate (taxes / gross_income)
    """
    if gross_income <= 0:
        return 0.0
    
    taxable_income = max(0.0, gross_income - standard_deduction)
    taxes = calculate_tax(taxable_income, tax_brackets)
    return taxes / gross_income


def marginal_tax_rate(gross_income: float,
                     standard_deduction: float,
                     tax_brackets: List[Tuple[float, float]]) -> float:
    """
    Calculate marginal tax rate at given income level.
    
    Args:
        gross_income: Total gross income
        standard_deduction: Standard deduction amount
        tax_brackets: Progressive tax brackets
        
    Returns:
        Marginal tax rate for next dollar of income
    """
    taxable_income = max(0.0, gross_income - standard_deduction)
    
    if taxable_income <= 0:
        return 0.0
    
    if not tax_brackets:
        return 0.0
    
    # Sort brackets by threshold
    sorted_brackets = sorted(tax_brackets, key=lambda x: x[0])
    
    # Find which bracket we're in - we want the rate for the bracket that contains our income
    current_rate = 0.0
    
    for threshold, rate in sorted_brackets:
        if taxable_income >= threshold:
            current_rate = rate
        else:
            break
    
    return current_rate