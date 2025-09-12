#!/usr/bin/env python3
"""
Demo script showing how to use the retirement simulation modules programmatically.
This demonstrates the core functionality without the Streamlit UI.
"""

from simulation import SimulationParams, RetirementSimulator, calculate_percentiles, calculate_summary_stats
from deterministic import DeterministicProjector
from tax import calculate_tax, solve_gross_withdrawal
from charts import create_terminal_wealth_distribution, create_wealth_percentile_bands
from io_utils import create_parameters_download_json, format_currency
import numpy as np


def main():
    print("🚀 Retirement Simulation Demo")
    print("=" * 50)
    
    # 1. Create simulation parameters
    print("\n📊 Setting up simulation parameters...")
    params = SimulationParams(
        start_capital=8_000_000,
        horizon_years=30,
        num_sims=1_000,
        w_equity=0.7,
        w_bonds=0.2,
        w_real_estate=0.1,
        w_cash=0.0,
        regime="baseline",
        random_seed=42  # For reproducible results
    )
    
    print(f"   Start capital: {format_currency(params.start_capital, 'real')}")
    print(f"   Allocation: {params.w_equity:.0%} equity, {params.w_bonds:.0%} bonds, {params.w_real_estate:.0%} RE")
    print(f"   Horizon: {params.horizon_years} years, {params.num_sims:,} simulations")
    
    # 2. Run Monte Carlo simulation
    print("\n🎲 Running Monte Carlo simulation...")
    simulator = RetirementSimulator(params)
    results = simulator.run_simulation()
    
    # 3. Calculate and display summary statistics
    print(f"\n📈 Results Summary:")
    terminal_stats = calculate_summary_stats(results.terminal_wealth)
    
    print(f"   Success Rate: {results.success_rate:.1%}")
    print(f"   Terminal Wealth (P10/P50/P90): {format_currency(terminal_stats['p10'], 'real')} / "
          f"{format_currency(terminal_stats['p50'], 'real')} / {format_currency(terminal_stats['p90'], 'real')}")
    print(f"   Probability < $5M: {terminal_stats['prob_below_5m']:.1%}")
    print(f"   Median guardrail hits: {np.median(results.guardrail_hits):.0f}")
    
    # 4. Demonstrate tax calculations
    print(f"\n💰 Tax Calculation Demo:")
    
    # Example gross-up calculation
    net_need = 250_000
    standard_deduction = 29_200
    tax_brackets = [(0, 0.10), (94_300, 0.22), (201_000, 0.24)]
    
    gross_withdrawal, taxes = solve_gross_withdrawal(
        net_need, 0, standard_deduction, tax_brackets
    )
    
    print(f"   To meet net need of {format_currency(net_need, 'real')}:")
    print(f"   Gross withdrawal needed: {format_currency(gross_withdrawal, 'real')}")
    print(f"   Taxes paid: {format_currency(taxes, 'real')}")
    print(f"   Effective tax rate: {taxes/gross_withdrawal:.1%}")
    
    # 5. Run deterministic projection for comparison
    print(f"\n📉 Deterministic Projection:")
    projector = DeterministicProjector(params)
    det_results = projector.run_projection()
    
    final_wealth_det = det_results.wealth_path[-1]
    print(f"   Final wealth (deterministic): {format_currency(final_wealth_det, 'real')}")
    print(f"   Total guardrail hits: {det_results.guardrail_hits}")
    
    # 6. Show some year-by-year details
    print(f"\n📋 Sample Year-by-Year Details (First 5 Years):")
    details = det_results.year_by_year_details
    print(f"   {'Year':<6} {'Start Assets':<15} {'Withdrawal':<12} {'Taxes':<10} {'End Assets':<15}")
    print(f"   {'-'*6} {'-'*15} {'-'*12} {'-'*10} {'-'*15}")
    
    for i in range(min(5, len(details['years']))):
        year = details['years'][i]
        start = details['start_assets'][i]
        withdrawal = details['gross_withdrawal'][i]
        taxes = details['taxes'][i]
        end = details['end_assets'][i]
        
        print(f"   {year:<6} ${start/1000:>11,.0f}K ${withdrawal/1000:>8,.0f}K ${taxes/1000:>6,.0f}K ${end/1000:>11,.0f}K")
    
    # 7. Parameter export demo
    print(f"\n💾 Parameter Export Demo:")
    json_params = create_parameters_download_json(params)
    print(f"   Parameters exported to JSON ({len(json_params)} characters)")
    print(f"   Sample: {json_params[:100]}...")
    
    print(f"\n✅ Demo completed successfully!")
    print(f"   To run the full Streamlit UI: streamlit run app.py")
    print(f"   To run tests: python3 -m pytest tests/ -v")


if __name__ == "__main__":
    main()