"""
Deterministic retirement projection using expected returns (no randomness).
Provides baseline scenario for comparison with Monte Carlo results.
"""
import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from simulation import SimulationParams
from tax import solve_gross_withdrawal


@dataclass
class DeterministicResults:
    """Results from deterministic projection"""
    wealth_path: np.ndarray
    spending_path: np.ndarray
    withdrawal_path: np.ndarray
    tax_path: np.ndarray
    guardrail_hits: int
    year_by_year_details: Dict


class DeterministicProjector:
    """Deterministic retirement projection with expected returns"""
    
    def __init__(self, params: SimulationParams):
        self.params = params
    
    def _get_base_withdrawal_rate(self) -> float:
        """Calculate CAPE-based initial withdrawal rate"""
        return 0.0175 + 0.5 * (1.0 / self.params.cape_now)
    
    def _get_re_income(self, year: int) -> float:
        """Get real estate income for given year (real dollars)"""
        year_offset = year - self.params.start_year
        
        if self.params.re_flow_preset == "ramp":
            if year_offset == 0:
                return 50_000
            elif year_offset == 1:
                return 60_000
            elif year_offset >= 2:
                return 75_000
            else:
                return 0
        elif self.params.re_flow_preset == "delayed":
            if year_offset <= 4:  # Through 2030
                return 0
            elif year_offset == 5:  # 2031
                return 50_000
            elif year_offset == 6:  # 2032
                return 60_000
            elif year_offset >= 7:  # 2033+
                return 75_000
            else:
                return 0
        else:
            return 0
    
    def _get_college_topup(self, year: int) -> float:
        """Get college top-up for given year (real dollars)"""
        if 2032 <= year <= 2041:
            years_since_2032 = year - 2032
            return 100_000 * (1 + self.params.college_growth_real) ** years_since_2032
        return 0
    
    def _get_onetime_expense(self, year: int) -> float:
        """Get one-time expenses for given year (real dollars)"""
        if year == 2033:
            return self.params.onetime_2033
        elif year == 2040:
            return self.params.onetime_2040
        return 0
    
    def _get_other_income(self, year: int) -> float:
        """Get other income for given year (real dollars, net of tax)"""
        if self.params.other_income_years == 0:
            return 0
        
        year_offset = year - self.params.other_income_start_year
        if 0 <= year_offset < self.params.other_income_years:
            return self.params.other_income_amount
        return 0
    
    def _apply_spending_guardrails(self, current_base_spend: float, 
                                 portfolio_value: float) -> tuple[float, str]:
        """Apply Guyton-Klinger guardrails to spending"""
        current_wr = current_base_spend / portfolio_value if portfolio_value > 0 else 0
        
        if current_wr > self.params.upper_wr:
            new_spend = current_base_spend * (1 - self.params.adjustment_pct)
            return new_spend, "down"
        elif current_wr < self.params.lower_wr:
            new_spend = current_base_spend * (1 + self.params.adjustment_pct)
            return new_spend, "up"
        else:
            return current_base_spend, "none"
    
    def _apply_spending_bounds(self, spending: float, year: int) -> tuple[float, bool, bool]:
        """Apply floor and ceiling to spending"""
        floor_applied = False
        ceiling_applied = False
        
        # Apply floor only until floor_end_year
        if year <= self.params.floor_end_year:
            if spending < self.params.spending_floor_real:
                spending = self.params.spending_floor_real
                floor_applied = True
        
        # Apply ceiling always
        if spending > self.params.spending_ceiling_real:
            spending = self.params.spending_ceiling_real
            ceiling_applied = True
        
        return spending, floor_applied, ceiling_applied
    
    def _get_expected_return(self, year_offset: int) -> float:
        """Get expected portfolio return based on regime"""
        if self.params.regime == "recession_recover":
            if year_offset == 0:
                eq_mean = -0.15
            elif year_offset == 1:
                eq_mean = 0.00
            else:
                eq_mean = self.params.equity_mean
            bond_mean = self.params.bonds_mean
            re_mean = self.params.real_estate_mean
            cash_mean = self.params.cash_mean
        elif self.params.regime == "grind_lower":
            if year_offset < 10:
                eq_mean = 0.005
                bond_mean = 0.01
                re_mean = 0.005
                cash_mean = self.params.cash_mean
            else:
                eq_mean = self.params.equity_mean
                bond_mean = self.params.bonds_mean
                re_mean = self.params.real_estate_mean
                cash_mean = self.params.cash_mean
        else:  # baseline
            eq_mean = self.params.equity_mean
            bond_mean = self.params.bonds_mean
            re_mean = self.params.real_estate_mean
            cash_mean = self.params.cash_mean
        
        # Calculate weighted return
        weights = np.array([self.params.w_equity, self.params.w_bonds, 
                          self.params.w_real_estate, self.params.w_cash])
        returns = np.array([eq_mean, bond_mean, re_mean, cash_mean])
        
        return np.sum(weights * returns)
    
    def run_projection(self) -> DeterministicResults:
        """Run deterministic projection"""
        # Initialize arrays
        wealth_path = np.zeros(self.params.horizon_years + 1)
        spending_path = np.zeros(self.params.horizon_years)
        withdrawal_path = np.zeros(self.params.horizon_years)
        tax_path = np.zeros(self.params.horizon_years)
        
        # Track detailed year-by-year information
        details = {
            'years': [],
            'start_assets': [],
            'base_spending': [],
            'floor_applied': [],
            'ceiling_applied': [],
            'guardrail_action': [],
            'adjusted_base_spending': [],
            'college_topup': [],
            'one_times': [],
            're_income': [],
            'other_income': [],
            'taxable_income': [],
            'taxes': [],
            'net_need': [],
            'gross_withdrawal': [],
            'expected_return': [],
            'growth': [],
            'inheritance': [],
            'end_assets': [],
            'withdrawal_rate': []
        }
        
        # Initial conditions
        portfolio_value = self.params.start_capital
        initial_base_spend = self._get_base_withdrawal_rate() * self.params.start_capital
        current_base_spend = initial_base_spend
        guardrail_hits = 0
        
        wealth_path[0] = portfolio_value
        
        for year_idx in range(self.params.horizon_years):
            current_year = self.params.start_year + year_idx
            
            # Apply guardrails to base spending
            adjusted_base_spend, guardrail_action = self._apply_spending_guardrails(
                current_base_spend, portfolio_value)
            if guardrail_action != "none":
                guardrail_hits += 1
                current_base_spend = adjusted_base_spend
            
            # Apply floor and ceiling
            final_base_spend, floor_applied, ceiling_applied = self._apply_spending_bounds(
                adjusted_base_spend, current_year)
            
            # Add other spending components
            college_topup = self._get_college_topup(current_year)
            one_times = self._get_onetime_expense(current_year)
            total_spending_need = final_base_spend + college_topup + one_times
            
            # Subtract non-portfolio income
            re_income = self._get_re_income(current_year)
            other_income = self._get_other_income(current_year)
            net_need = total_spending_need - re_income - other_income
            
            # Calculate gross withdrawal with taxes
            gross_withdrawal, taxes = solve_gross_withdrawal(
                net_need, 
                other_taxable_income=0,  # Simplified: other_income is net-of-tax
                standard_deduction=self.params.standard_deduction,
                tax_brackets=self.params.tax_brackets
            )
            
            # Get expected return
            expected_return = self._get_expected_return(year_idx)
            
            # Apply returns
            growth = portfolio_value * expected_return
            portfolio_value *= (1 + expected_return)
            
            # Add inheritance
            inheritance = 0
            if current_year == self.params.inherit_year:
                inheritance = self.params.inherit_amount
                portfolio_value += inheritance
            
            # Withdraw
            portfolio_value = max(0, portfolio_value - gross_withdrawal)
            
            # Store results
            spending_path[year_idx] = total_spending_need
            withdrawal_path[year_idx] = gross_withdrawal
            tax_path[year_idx] = taxes
            wealth_path[year_idx + 1] = portfolio_value
            
            # Store detailed information
            withdrawal_rate = gross_withdrawal / wealth_path[year_idx] if wealth_path[year_idx] > 0 else 0
            
            details['years'].append(current_year)
            details['start_assets'].append(wealth_path[year_idx])
            details['base_spending'].append(adjusted_base_spend)
            details['floor_applied'].append(floor_applied)
            details['ceiling_applied'].append(ceiling_applied)
            details['guardrail_action'].append(guardrail_action)
            details['adjusted_base_spending'].append(final_base_spend)
            details['college_topup'].append(college_topup)
            details['one_times'].append(one_times)
            details['re_income'].append(re_income)
            details['other_income'].append(other_income)
            details['taxable_income'].append(max(0, gross_withdrawal - self.params.standard_deduction))
            details['taxes'].append(taxes)
            details['net_need'].append(net_need)
            details['gross_withdrawal'].append(gross_withdrawal)
            details['expected_return'].append(expected_return)
            details['growth'].append(growth)
            details['inheritance'].append(inheritance)
            details['end_assets'].append(portfolio_value)
            details['withdrawal_rate'].append(withdrawal_rate)
        
        return DeterministicResults(
            wealth_path=wealth_path,
            spending_path=spending_path,
            withdrawal_path=withdrawal_path,
            tax_path=tax_path,
            guardrail_hits=guardrail_hits,
            year_by_year_details=details
        )


def convert_to_nominal(real_values: np.ndarray, 
                      start_year: int, 
                      inflation_rate: float = 0.027) -> np.ndarray:
    """
    Convert real values to nominal using compound inflation.
    
    Args:
        real_values: Array of real dollar values
        start_year: Base year for inflation calculation
        inflation_rate: Annual inflation rate
        
    Returns:
        Array of nominal dollar values
    """
    years = len(real_values)
    inflation_factors = np.array([(1 + inflation_rate) ** t for t in range(years)])
    return real_values * inflation_factors


def create_nominal_table(details: Dict, 
                        start_year: int, 
                        inflation_rate: float = 0.027) -> Dict:
    """
    Create nominal version of year-by-year details table.
    
    Args:
        details: Year-by-year details dictionary in real dollars
        start_year: Base year for inflation calculation
        inflation_rate: Annual inflation rate
        
    Returns:
        Dictionary with nominal values
    """
    nominal_details = {}
    
    # Fields that need inflation adjustment
    nominal_fields = [
        'start_assets', 'base_spending', 'adjusted_base_spending',
        'college_topup', 'one_times', 're_income', 'other_income',
        'taxable_income', 'taxes', 'net_need', 'gross_withdrawal',
        'growth', 'inheritance', 'end_assets'
    ]
    
    # Fields that don't need adjustment
    passthrough_fields = [
        'years', 'floor_applied', 'ceiling_applied', 'guardrail_action',
        'expected_return', 'withdrawal_rate'
    ]
    
    for field in nominal_fields:
        if field in details:
            real_values = np.array(details[field])
            years_offset = np.array(details['years']) - start_year
            inflation_factors = (1 + inflation_rate) ** years_offset
            nominal_details[field] = (real_values * inflation_factors).tolist()
    
    for field in passthrough_fields:
        if field in details:
            nominal_details[field] = details[field]
    
    return nominal_details