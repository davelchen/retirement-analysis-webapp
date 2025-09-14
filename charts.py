"""
Plotly chart builders for retirement simulation visualizations.
Creates interactive charts for wealth distributions, percentile bands, and comparisons.
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional, Tuple


def create_terminal_wealth_distribution(terminal_wealth: np.ndarray,
                                      title: str = "Terminal Wealth Distribution",
                                      currency_format: str = "real") -> go.Figure:
    """
    Create detailed histogram showing distribution of terminal wealth outcomes with high resolution.
    
    Args:
        terminal_wealth: Array of terminal wealth values from simulation
        title: Chart title
        currency_format: "real" or "nominal" for axis labels
        
    Returns:
        Plotly figure
    """
    # Convert to millions for readability
    wealth_millions = terminal_wealth / 1_000_000
    
    # Calculate detailed statistics
    percentiles = [5, 10, 25, 50, 75, 90, 95]
    perc_values = np.percentile(wealth_millions, percentiles)
    mean_val = np.mean(wealth_millions)
    std_val = np.std(wealth_millions)
    
    # Determine optimal bin count based on data range and size
    n_bins = min(200, max(100, int(np.sqrt(len(wealth_millions)) * 2)))
    
    fig = go.Figure()
    
    # Add high-resolution histogram
    fig.add_trace(go.Histogram(
        x=wealth_millions,
        nbinsx=n_bins,
        name="Terminal Wealth",
        hovertemplate="<b>Wealth Range:</b> $%{x:.2f}M<br>" +
                     "<b>Simulations:</b> %{y}<br>" +
                     "<b>Probability:</b> %{y}/" + f"{len(wealth_millions)} = " +
                     "%{customdata:.1%}<br>" +
                     "<extra></extra>",
        customdata=np.ones(len(wealth_millions)) / len(wealth_millions),
        marker=dict(
            color='lightblue', 
            line=dict(color='darkblue', width=0.5),
            opacity=0.8
        )
    ))
    
    # Add density curve overlay (only if we have enough data points and variance)
    if len(wealth_millions) > 1 and np.var(wealth_millions) > 0:
        try:
            from scipy import stats
            kde = stats.gaussian_kde(wealth_millions)
            x_range = np.linspace(wealth_millions.min(), wealth_millions.max(), 500)
            density = kde(x_range)
            
            # Scale density to match histogram height
            hist_max = np.histogram(wealth_millions, bins=n_bins)[0].max()
            if hist_max > 0 and density.max() > 0:
                density_scaled = density * hist_max / density.max() * 0.8
                
                fig.add_trace(go.Scatter(
                    x=x_range,
                    y=density_scaled,
                    mode='lines',
                    name='Density Curve',
                    line=dict(color='darkred', width=3),
                    hovertemplate="<b>Wealth:</b> $%{x:.2f}M<br>" +
                                 "<b>Density:</b> %{y:.1f}<br>" +
                                 "<extra></extra>",
                    yaxis='y2'
                ))
        except (ValueError, np.linalg.LinAlgError):
            # Skip density curve if KDE fails
            pass
    
    # Add key percentile lines only (P10, P50, P90)
    key_percentiles = [10, 50, 90]
    key_values = [np.percentile(wealth_millions, p) for p in key_percentiles]
    colors = ['red', 'green', 'blue']
    
    for perc, val, color in zip(key_percentiles, key_values, colors):
        fig.add_vline(
            x=val, 
            line_dash="dash", 
            line_color=color,
            line_width=2,
            annotation=dict(
                text=f"P{perc}: ${val:.1f}M",
                textangle=-90,
                xanchor="left",
                yanchor="bottom"
            )
        )
    
    # Add only depletion line (most important threshold)
    if np.any(wealth_millions <= 0):
        failure_rate = np.mean(wealth_millions <= 0) * 100
        fig.add_vline(
            x=0,
            line_dash="solid",
            line_color="darkred",
            line_width=3,
            annotation=dict(
                text=f"Depletion: {failure_rate:.1f}%",
                textangle=0,
                xanchor="left",
                yanchor="middle",
                bgcolor="white",
                bordercolor="darkred"
            )
        )
    
    # Add compact summary statistics as subtitle
    success_rate = np.mean(wealth_millions > 0)
    median_val = key_values[1]  # P50 is index 1 in key_values (P10, P50, P90)
    stats_text = (
        f"Mean: ${mean_val:.1f}M • "
        f"Median: ${median_val:.1f}M • "
        f"Success: {success_rate:.1%} • "
        f"{len(wealth_millions):,} Simulations"
    )
    
    # Format axes
    currency_label = "Real" if currency_format == "real" else "Nominal"
    fig.update_layout(
        title=dict(
            text=f"{title} ({currency_label} Dollars)<br><sub>{stats_text}</sub>",
            x=0.5,
            xanchor='center'
        ),
        xaxis_title=f"Terminal Wealth (${currency_label} Millions)",
        yaxis_title="Number of Simulations",
        yaxis2=dict(
            title="Density",
            overlaying="y",
            side="right",
            showgrid=False
        ),
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            x=0.02, y=0.98,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="lightgray",
            borderwidth=1
        ),
        height=500,
        margin=dict(t=100, b=50, l=50, r=50)
    )
    
    return fig


def create_wealth_percentile_bands(years: np.ndarray,
                                 percentiles: Dict[str, np.ndarray],
                                 title: str = "Wealth Path Percentile Bands",
                                 currency_format: str = "real") -> go.Figure:
    """
    Create filled area chart showing P10/P50/P90 wealth bands over time.
    
    Args:
        years: Array of years
        percentiles: Dictionary with 'p10', 'p50', 'p90' arrays
        title: Chart title
        currency_format: "real" or "nominal" for axis labels
        
    Returns:
        Plotly figure
    """
    # Convert to millions for readability
    p10_millions = percentiles['p10'] / 1_000_000
    p50_millions = percentiles['p50'] / 1_000_000
    p90_millions = percentiles['p90'] / 1_000_000
    
    fig = go.Figure()
    
    # Add filled areas
    fig.add_trace(go.Scatter(
        x=years, y=p90_millions,
        mode='lines',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=years, y=p10_millions,
        fill='tonexty',
        mode='lines',
        line=dict(color='lightblue'),
        name='P10-P90 Range',
        fillcolor='rgba(173,216,230,0.3)',
        customdata=np.column_stack([p10_millions, p90_millions]),
        hovertemplate="<b>Year:</b> %{x}<br>" +
                     "<b>P10 (Pessimistic):</b> $%{customdata[0]:.1f}M<br>" +
                     "<b>P90 (Optimistic):</b> $%{customdata[1]:.1f}M<br>" +
                     "<b>Range:</b> $%{customdata[0]:.1f}M - $%{customdata[1]:.1f}M<br>" +
                     "<extra></extra>"
    ))
    
    fig.add_trace(go.Scatter(
        x=years, y=p50_millions,
        mode='lines',
        line=dict(color='darkblue', width=3),
        name='P50 (Median)',
        hovertemplate="<b>Year:</b> %{x}<br>" +
                     "<b>Median Wealth:</b> $%{y:.1f}M<br>" +
                     "<extra></extra>"
    ))
    
    # Format axes
    currency_label = "Real" if currency_format == "real" else "Nominal"
    fig.update_layout(
        title=f"{title} ({currency_label} Dollars)",
        xaxis_title="Year",
        yaxis_title=f"Wealth (${currency_label} Millions)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig


def create_comparison_chart(scenarios: Dict[str, np.ndarray],
                           chart_type: str = "terminal_wealth",
                           title: str = "Scenario Comparison") -> go.Figure:
    """
    Create comparison chart for multiple scenarios.
    
    Args:
        scenarios: Dictionary mapping scenario names to terminal wealth arrays
        chart_type: "terminal_wealth" or "success_rate"
        title: Chart title
        
    Returns:
        Plotly figure
    """
    if chart_type == "terminal_wealth":
        return _create_terminal_wealth_comparison(scenarios, title)
    elif chart_type == "success_rate":
        return _create_success_rate_comparison(scenarios, title)
    else:
        raise ValueError(f"Unknown chart type: {chart_type}")


def _create_terminal_wealth_comparison(scenarios: Dict[str, np.ndarray],
                                     title: str) -> go.Figure:
    """Create overlaid histograms comparing terminal wealth distributions"""
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set1
    
    for i, (scenario_name, terminal_wealth) in enumerate(scenarios.items()):
        wealth_millions = terminal_wealth / 1_000_000
        
        fig.add_trace(go.Histogram(
            x=wealth_millions,
            name=scenario_name,
            opacity=0.7,
            nbinsx=40,
            marker_color=colors[i % len(colors)],
            hovertemplate=f"<b>{scenario_name}</b><br>" +
                         "<b>Wealth Range:</b> $%{x:.1f}M<br>" +
                         "<b>Count:</b> %{y}<br>" +
                         "<extra></extra>"
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Terminal Wealth ($ Millions)",
        yaxis_title="Number of Simulations",
        template="plotly_white",
        barmode='overlay',
        hovermode="x unified"
    )
    
    return fig


def _create_success_rate_comparison(scenarios: Dict[str, np.ndarray],
                                   title: str) -> go.Figure:
    """Create bar chart comparing success rates across scenarios"""
    scenario_names = list(scenarios.keys())
    success_rates = []
    
    for terminal_wealth in scenarios.values():
        # Success = non-depletion (wealth > 0)
        success_rate = np.mean(terminal_wealth > 0) * 100
        success_rates.append(success_rate)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=scenario_names,
        y=success_rates,
        marker_color='lightblue',
        marker_line_color='darkblue',
        marker_line_width=1,
        hovertemplate="<b>%{x}</b><br>" +
                     "<b>Success Rate:</b> %{y:.1f}%<br>" +
                     "<extra></extra>"
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Scenario",
        yaxis_title="Success Rate (%)",
        template="plotly_white",
        showlegend=False
    )
    
    # Add percentage labels on bars
    for i, rate in enumerate(success_rates):
        fig.add_annotation(
            x=i,
            y=rate + 1,
            text=f"{rate:.1f}%",
            showarrow=False,
            font=dict(size=12)
        )
    
    return fig


def create_spending_chart(years: np.ndarray,
                         spending_components: Dict[str, np.ndarray],
                         title: str = "Annual Spending Breakdown") -> go.Figure:
    """
    Create stacked area chart showing spending components over time.
    
    Args:
        years: Array of years
        spending_components: Dict with component names and values
        title: Chart title
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Define component order and colors
    component_order = ['Base Spending', 'College Top-Up', 'One-Time Expenses']
    colors = ['lightblue', 'lightgreen', 'lightcoral']
    
    for i, component in enumerate(component_order):
        if component in spending_components:
            values = spending_components[component] / 1000  # Convert to thousands
            
            fig.add_trace(go.Scatter(
                x=years,
                y=values,
                mode='lines',
                stackgroup='one',
                name=component,
                line=dict(width=0.5),
                fillcolor=colors[i % len(colors)],
                hovertemplate=f"<b>{component}</b><br>" +
                             "<b>Year:</b> %{x}<br>" +
                             "<b>Amount:</b> $%{y:.0f}K<br>" +
                             "<extra></extra>"
            ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Annual Spending ($000s)",
        template="plotly_white",
        hovermode="x unified"
    )
    
    return fig


def create_withdrawal_rate_chart(years: np.ndarray,
                                withdrawal_rates: np.ndarray,
                                guardrail_lower: float = 0.028,
                                guardrail_upper: float = 0.045,
                                title: str = "Withdrawal Rate Over Time") -> go.Figure:
    """
    Create line chart showing withdrawal rates with guardrail bands.
    
    Args:
        years: Array of years
        withdrawal_rates: Array of withdrawal rates (as decimals)
        guardrail_lower: Lower guardrail threshold
        guardrail_upper: Upper guardrail threshold
        title: Chart title
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Convert to percentages
    wr_pct = withdrawal_rates * 100
    lower_pct = guardrail_lower * 100
    upper_pct = guardrail_upper * 100
    
    # Add withdrawal rate line
    fig.add_trace(go.Scatter(
        x=years,
        y=wr_pct,
        mode='lines+markers',
        name='Withdrawal Rate',
        line=dict(color='darkblue', width=2),
        marker=dict(size=4),
        hovertemplate="<b>Year:</b> %{x}<br>" +
                     "<b>Withdrawal Rate:</b> %{y:.1f}%<br>" +
                     "<extra></extra>"
    ))
    
    # Add guardrail bands
    fig.add_hline(y=lower_pct, line_dash="dash", line_color="green",
                 annotation_text=f"Lower Guardrail: {lower_pct:.1f}%")
    fig.add_hline(y=upper_pct, line_dash="dash", line_color="red",
                 annotation_text=f"Upper Guardrail: {upper_pct:.1f}%")
    
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Withdrawal Rate (%)",
        template="plotly_white",
        hovermode="x unified",
        showlegend=False
    )
    
    return fig


def create_tax_analysis_chart(gross_withdrawals: np.ndarray,
                             taxes_paid: np.ndarray,
                             years: np.ndarray,
                             title: str = "Tax Analysis") -> go.Figure:
    """
    Create chart showing gross withdrawals vs taxes paid.
    
    Args:
        gross_withdrawals: Array of gross withdrawal amounts
        taxes_paid: Array of taxes paid
        years: Array of years
        title: Chart title
        
    Returns:
        Plotly figure
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Annual Amounts', 'Effective Tax Rate'),
        vertical_spacing=0.08
    )
    
    # Convert to thousands for readability
    gross_k = gross_withdrawals / 1000
    taxes_k = taxes_paid / 1000
    
    # Top plot: Gross withdrawals and taxes
    fig.add_trace(
        go.Scatter(x=years, y=gross_k, name='Gross Withdrawal',
                  line=dict(color='darkblue', width=2),
                  hovertemplate="<b>Year:</b> %{x}<br>" +
                               "<b>Gross Withdrawal:</b> $%{y:.0f}K<br>" +
                               "<extra></extra>"),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=years, y=taxes_k, name='Taxes Paid',
                  line=dict(color='red', width=2),
                  hovertemplate="<b>Year:</b> %{x}<br>" +
                               "<b>Taxes:</b> $%{y:.0f}K<br>" +
                               "<extra></extra>"),
        row=1, col=1
    )
    
    # Bottom plot: Effective tax rate
    effective_rates = np.where(gross_withdrawals > 0, 
                              (taxes_paid / gross_withdrawals) * 100, 0)
    
    fig.add_trace(
        go.Scatter(x=years, y=effective_rates, name='Effective Tax Rate',
                  line=dict(color='green', width=2),
                  hovertemplate="<b>Year:</b> %{x}<br>" +
                               "<b>Effective Rate:</b> %{y:.1f}%<br>" +
                               "<extra></extra>"),
        row=2, col=1
    )
    
    fig.update_layout(
        title=title,
        template="plotly_white",
        hovermode="x unified",
        height=600
    )
    
    fig.update_xaxes(title_text="Year", row=2, col=1)
    fig.update_yaxes(title_text="Amount ($000s)", row=1, col=1)
    fig.update_yaxes(title_text="Tax Rate (%)", row=2, col=1)
    
    return fig


def create_monte_carlo_paths_sample(years: np.ndarray,
                                   wealth_paths: np.ndarray,
                                   num_samples: int = 50,
                                   title: str = "Monte Carlo Path Samples") -> go.Figure:
    """
    Create chart showing sample individual Monte Carlo simulation paths.
    
    Args:
        years: Array of years
        wealth_paths: 2D array of wealth paths (simulations x years)
        num_samples: Number of sample paths to display
        title: Chart title
        
    Returns:
        Plotly figure
    """
    # Select random sample of paths
    n_sims = wealth_paths.shape[0]
    sample_indices = np.random.choice(n_sims, min(num_samples, n_sims), replace=False)
    
    fig = go.Figure()
    
    # Add sample paths with reduced opacity
    for i, idx in enumerate(sample_indices):
        path_millions = wealth_paths[idx] / 1_000_000
        
        # Color paths by outcome (red for failure, blue for success)
        color = 'red' if path_millions[-1] <= 0 else 'blue'
        opacity = 0.3
        
        fig.add_trace(go.Scatter(
            x=years,
            y=path_millions,
            mode='lines',
            line=dict(color=color, width=1),
            opacity=opacity,
            showlegend=False,
            hovertemplate=f"<b>Path {idx}</b><br>" +
                         "<b>Year:</b> %{x}<br>" +
                         "<b>Wealth:</b> $%{y:.1f}M<br>" +
                         "<extra></extra>"
        ))
    
    # Add percentile bands for context
    percentiles = {
        'p10': np.percentile(wealth_paths, 10, axis=0) / 1_000_000,
        'p50': np.percentile(wealth_paths, 50, axis=0) / 1_000_000,
        'p90': np.percentile(wealth_paths, 90, axis=0) / 1_000_000
    }
    
    # Add P10-P90 band
    fig.add_trace(go.Scatter(
        x=years, y=percentiles['p90'],
        mode='lines', line=dict(color='rgba(0,0,0,0)'),
        showlegend=False, hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=years, y=percentiles['p10'],
        fill='tonexty', mode='lines',
        line=dict(color='lightgray', width=1),
        fillcolor='rgba(128,128,128,0.2)',
        name='P10-P90 Range',
        customdata=np.column_stack([percentiles['p10'], percentiles['p90']]),
        hovertemplate="<b>Year:</b> %{x}<br>" +
                     "<b>P10 (Pessimistic):</b> $%{customdata[0]:.1f}M<br>" +
                     "<b>P90 (Optimistic):</b> $%{customdata[1]:.1f}M<br>" +
                     "<b>Range:</b> $%{customdata[0]:.1f}M - $%{customdata[1]:.1f}M<br>" +
                     "<extra></extra>"
    ))
    
    # Add median line
    fig.add_trace(go.Scatter(
        x=years, y=percentiles['p50'],
        mode='lines', line=dict(color='black', width=2),
        name='Median Path',
        hovertemplate="<b>Median</b><br>" +
                     "<b>Year:</b> %{x}<br>" +
                     "<b>Wealth:</b> $%{y:.1f}M<br>" +
                     "<extra></extra>"
    ))
    
    fig.update_layout(
        title=f"{title} ({num_samples} Sample Paths)",
        xaxis_title="Year",
        yaxis_title="Portfolio Value ($ Millions)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig


def create_success_probability_over_time(years: np.ndarray,
                                       wealth_paths: np.ndarray,
                                       success_thresholds: List[float] = [0, 1_000_000, 2_500_000],
                                       title: str = "Success Probability Over Time") -> go.Figure:
    """
    Create chart showing probability of success (wealth above thresholds) over time.
    
    Args:
        years: Array of years
        wealth_paths: 2D array of wealth paths (simulations x years) 
        success_thresholds: List of wealth thresholds to track
        title: Chart title
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    colors = ['red', 'orange', 'green', 'blue', 'purple']
    threshold_labels = []
    
    for i, threshold in enumerate(success_thresholds):
        # Calculate success probability at each time point
        success_probs = []
        for year_idx in range(len(years)):
            prob = np.mean(wealth_paths[:, year_idx] > threshold) * 100
            success_probs.append(prob)
        
        # Create label
        if threshold == 0:
            label = "Non-Depletion"
        else:
            label = f"Above ${threshold/1_000_000:.1f}M"
        threshold_labels.append(label)
        
        fig.add_trace(go.Scatter(
            x=years,
            y=success_probs,
            mode='lines+markers',
            name=label,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=4),
            hovertemplate=f"<b>{label}</b><br>" +
                         "<b>Year:</b> %{x}<br>" +
                         "<b>Success Prob:</b> %{y:.1f}%<br>" +
                         "<extra></extra>"
        ))
    
    # Add reference lines
    fig.add_hline(y=90, line_dash="dash", line_color="green", 
                 annotation_text="90% Success Target")
    fig.add_hline(y=95, line_dash="dash", line_color="darkgreen",
                 annotation_text="95% Success Target")
    
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Success Probability (%)",
        yaxis=dict(range=[0, 100]),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.02, y=0.02)
    )
    
    return fig


def create_cash_flow_waterfall(year_by_year_details: Dict,
                              selected_year: int = None,
                              title: str = "Annual Cash Flow Breakdown") -> go.Figure:
    """
    Create waterfall chart showing cash flow sources and uses.
    
    Args:
        year_by_year_details: Dictionary with year-by-year simulation details
        selected_year: Specific year to analyze (if None, uses first year)
        title: Chart title
        
    Returns:
        Plotly figure
    """
    years = year_by_year_details.get('years', [])
    if not years:
        return go.Figure()
    
    # Select year to analyze
    if selected_year is None:
        year_idx = 0
    else:
        try:
            year_idx = years.index(selected_year)
        except ValueError:
            year_idx = 0
    
    selected_year = years[year_idx]
    
    # Extract cash flow components
    components = []
    values = []
    
    # Starting wealth
    start_wealth = year_by_year_details.get('start_wealth', [0] * len(years))[year_idx]
    components.append('Starting Wealth')
    values.append(start_wealth)
    
    # Income sources (positive)
    other_income = year_by_year_details.get('other_income', [0] * len(years))[year_idx]
    if other_income > 0:
        components.append('Other Income')
        values.append(other_income)
    
    re_income = year_by_year_details.get('re_income', [0] * len(years))[year_idx]
    if re_income > 0:
        components.append('Real Estate Income')
        values.append(re_income)

    ss_income = year_by_year_details.get('ss_income', [0] * len(years))[year_idx]
    if ss_income > 0:
        components.append('Social Security Income')
        values.append(ss_income)

    inheritance = year_by_year_details.get('inheritance', [0] * len(years))[year_idx]
    if inheritance > 0:
        components.append('Inheritance')
        values.append(inheritance)
    
    # Investment growth
    investment_growth = year_by_year_details.get('investment_growth', [0] * len(years))[year_idx]
    components.append('Investment Growth')
    values.append(investment_growth)
    
    # Expenses (negative)
    base_spending = -year_by_year_details.get('base_spending', [0] * len(years))[year_idx]
    components.append('Base Spending')
    values.append(base_spending)
    
    college_topup = -year_by_year_details.get('college_topup', [0] * len(years))[year_idx]
    if college_topup < 0:
        components.append('College Expenses')
        values.append(college_topup)
    
    onetime = -year_by_year_details.get('onetime_expense', [0] * len(years))[year_idx] 
    if onetime < 0:
        components.append('One-time Expenses')
        values.append(onetime)
    
    taxes = -year_by_year_details.get('taxes_paid', [0] * len(years))[year_idx]
    if taxes < 0:
        components.append('Taxes')
        values.append(taxes)
    
    # Ending wealth
    end_wealth = year_by_year_details.get('end_wealth', [0] * len(years))[year_idx]
    components.append('Ending Wealth')
    values.append(end_wealth)
    
    # Convert to thousands for readability
    values_k = [v / 1000 for v in values]
    
    # Create waterfall chart
    fig = go.Figure(go.Waterfall(
        name=f"Year {selected_year}",
        orientation="v",
        measure=["absolute"] + ["relative"] * (len(values) - 2) + ["total"],
        x=components,
        textposition="outside",
        text=[f"${v:,.0f}K" for v in values_k],
        y=values_k,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "green"}},
        decreasing={"marker": {"color": "red"}},
        totals={"marker": {"color": "blue"}}
    ))
    
    fig.update_layout(
        title=f"{title} - Year {selected_year}",
        yaxis_title="Cash Flow ($000s)",
        template="plotly_white",
        showlegend=False
    )
    
    return fig


def create_sequence_of_returns_analysis(wealth_paths: np.ndarray,
                                      years: np.ndarray,
                                      title: str = "Sequence of Returns Risk Analysis") -> go.Figure:
    """
    Create chart comparing early vs late recession scenarios.
    
    Args:
        wealth_paths: 2D array of wealth paths
        years: Array of years
        title: Chart title
        
    Returns:
        Plotly figure
    """
    # Split simulations into early decline vs late decline
    n_sims, n_years = wealth_paths.shape
    mid_point = n_years // 2
    
    # Identify early decliners (big losses in first half)
    early_decline_mask = []
    late_decline_mask = []
    stable_mask = []
    
    for i in range(n_sims):
        path = wealth_paths[i]
        early_decline = (path[0] - path[mid_point]) / path[0] if path[0] > 0 else 0
        late_decline = (path[mid_point] - path[-1]) / path[mid_point] if path[mid_point] > 0 else 0
        
        if early_decline > 0.3:  # Lost >30% in first half
            early_decline_mask.append(i)
        elif late_decline > 0.3:  # Lost >30% in second half
            late_decline_mask.append(i)
        else:
            stable_mask.append(i)
    
    fig = go.Figure()
    
    # Plot percentiles for each group
    groups = [
        ("Early Market Decline", early_decline_mask, "red"),
        ("Late Market Decline", late_decline_mask, "orange"), 
        ("Stable Returns", stable_mask, "green")
    ]
    
    for group_name, indices, color in groups:
        if not indices:
            continue
            
        group_paths = wealth_paths[indices] / 1_000_000
        p50 = np.percentile(group_paths, 50, axis=0)
        
        fig.add_trace(go.Scatter(
            x=years,
            y=p50,
            mode='lines',
            name=f"{group_name} (Median)",
            line=dict(color=color, width=3),
            hovertemplate=f"<b>{group_name}</b><br>" +
                         "<b>Year:</b> %{x}<br>" +
                         "<b>Wealth:</b> $%{y:.1f}M<br>" +
                         f"<b>Scenarios:</b> {len(indices)}<br>" +
                         "<extra></extra>"
        ))
    
    # Add annotations explaining the analysis
    fig.add_annotation(
        text="Early market declines are typically more harmful<br>to retirement success than late declines",
        xref="paper", yref="paper",
        x=0.02, y=0.15,
        showarrow=False,
        align="left",
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="black",
        borderwidth=1
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Portfolio Value ($ Millions)", 
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.7, y=0.98)
    )
    
    return fig


def create_drawdown_analysis(wealth_paths: np.ndarray,
                           years: np.ndarray,
                           title: str = "Portfolio Drawdown Analysis") -> go.Figure:
    """
    Create chart showing maximum drawdown analysis over time.
    
    Args:
        wealth_paths: 2D array of wealth paths
        years: Array of years
        title: Chart title
        
    Returns:
        Plotly figure
    """
    # Calculate drawdowns for each path
    drawdowns = np.zeros_like(wealth_paths)
    
    for i in range(wealth_paths.shape[0]):
        path = wealth_paths[i]
        running_max = np.maximum.accumulate(path)
        drawdowns[i] = (path - running_max) / running_max * 100
    
    # Calculate percentiles of drawdowns
    p10_dd = np.percentile(drawdowns, 10, axis=0)  # Worst 10%
    p50_dd = np.percentile(drawdowns, 50, axis=0)  # Median
    p90_dd = np.percentile(drawdowns, 90, axis=0)  # Best 10%
    
    fig = go.Figure()
    
    # Add drawdown bands
    fig.add_trace(go.Scatter(
        x=years, y=p10_dd,
        mode='lines', line=dict(color='rgba(0,0,0,0)'),
        showlegend=False, hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=years, y=p90_dd,
        fill='tonexty', mode='lines',
        line=dict(color='lightcoral'),
        fillcolor='rgba(255,182,193,0.3)',
        name='P10-P90 Drawdown Range',
        customdata=np.column_stack([p10_dd, p90_dd]),
        hovertemplate="<b>Year:</b> %{x}<br>" +
                     "<b>P10 Drawdown (Worst Case):</b> %{customdata[0]:.1f}%<br>" +
                     "<b>P90 Drawdown (Best Case):</b> %{customdata[1]:.1f}%<br>" +
                     "<b>Drawdown Range:</b> %{customdata[1]:.1f}% to %{customdata[0]:.1f}%<br>" +
                     "<extra></extra>"
    ))
    
    # Add median drawdown
    fig.add_trace(go.Scatter(
        x=years, y=p50_dd,
        mode='lines', line=dict(color='darkred', width=3),
        name='Median Drawdown',
        hovertemplate="<b>Median Drawdown</b><br>" +
                     "<b>Year:</b> %{x}<br>" +
                     "<b>Drawdown:</b> %{y:.1f}%<br>" +
                     "<extra></extra>"
    ))
    
    # Add reference lines for significant drawdown levels
    fig.add_hline(y=-20, line_dash="dash", line_color="orange",
                 annotation_text="20% Drawdown")
    fig.add_hline(y=-30, line_dash="dash", line_color="red", 
                 annotation_text="30% Drawdown") 
    fig.add_hline(y=-50, line_dash="dash", line_color="darkred",
                 annotation_text="50% Drawdown")
    
    # Calculate and display key statistics
    max_drawdowns = np.min(drawdowns, axis=1)  # Most negative for each path
    avg_max_dd = np.mean(max_drawdowns)
    worst_max_dd = np.min(max_drawdowns)
    
    stats_text = (
        f"<b>Maximum Drawdown Stats</b><br>"
        f"Average Max DD: {avg_max_dd:.1f}%<br>"
        f"Worst Max DD: {worst_max_dd:.1f}%<br>"
        f"DD > 30%: {np.mean(max_drawdowns < -30):.1%} of paths<br>"
        f"DD > 50%: {np.mean(max_drawdowns < -50):.1%} of paths"
    )
    
    fig.add_annotation(
        text=stats_text,
        xref="paper", yref="paper", 
        x=0.02, y=0.15,
        showarrow=False,
        align="left",
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="black",
        borderwidth=1
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Drawdown from Peak (%)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.7, y=0.02)
    )

    return fig


def create_income_sources_stacked_area(year_by_year_details: Dict,
                                     title: str = "Income Sources Over Time",
                                     currency_format: str = "real") -> go.Figure:
    """
    Create stacked area chart showing different income sources over time.

    Args:
        year_by_year_details: Dictionary with year-by-year simulation details
        title: Chart title
        currency_format: "real" or "nominal" for axis labels

    Returns:
        Plotly figure
    """
    years = year_by_year_details.get('years', [])
    if not years:
        return go.Figure()

    # Get income components (convert to thousands for readability)
    portfolio_withdrawals = np.array(year_by_year_details.get('gross_withdrawal', [0] * len(years))) / 1000
    social_security = np.array(year_by_year_details.get('social_security_income', [0] * len(years))) / 1000
    other_income = np.array(year_by_year_details.get('other_income', [0] * len(years))) / 1000
    re_income = np.array(year_by_year_details.get('re_income', [0] * len(years))) / 1000

    fig = go.Figure()

    # Stack order from bottom to top (reverse order for stacking)
    income_sources = [
        ("Portfolio Withdrawals", portfolio_withdrawals, 'lightblue'),
        ("Social Security", social_security, 'lightgreen'),
        ("Other Income", other_income, 'lightcoral'),
        ("Real Estate Income", re_income, 'lightyellow')
    ]

    # Add traces in reverse order for proper stacking
    for name, values, color in income_sources:
        # Only add if there's any meaningful income from this source
        if np.sum(values) > 0:
            fig.add_trace(go.Scatter(
                x=years,
                y=values,
                mode='lines',
                stackgroup='one',
                name=name,
                line=dict(width=0.5),
                fillcolor=color,
                hovertemplate=f"<b>{name}</b><br>" +
                             "<b>Year:</b> %{x}<br>" +
                             "<b>Amount:</b> $%{y:.0f}K<br>" +
                             "<extra></extra>"
            ))

    # Calculate total income for context
    total_income = portfolio_withdrawals + social_security + other_income + re_income

    # Add total income line for reference
    if np.sum(total_income) > 0:
        fig.add_trace(go.Scatter(
            x=years,
            y=total_income,
            mode='lines',
            name='Total Income',
            line=dict(color='darkblue', width=3, dash='dash'),
            hovertemplate="<b>Total Income</b><br>" +
                         "<b>Year:</b> %{x}<br>" +
                         "<b>Total:</b> $%{y:.0f}K<br>" +
                         "<extra></extra>"
        ))

    # Add annotations showing the income transition
    if len(years) > 10:
        mid_year = years[len(years)//2]
        mid_idx = len(years)//2

        # Show percentage breakdown at midpoint
        mid_portfolio = portfolio_withdrawals[mid_idx]
        mid_ss = social_security[mid_idx]
        mid_total = total_income[mid_idx]

        if mid_total > 0:
            portfolio_pct = (mid_portfolio / mid_total) * 100
            ss_pct = (mid_ss / mid_total) * 100

            annotation_text = (
                f"<b>{mid_year} Income Mix</b><br>"
                f"Portfolio: {portfolio_pct:.0f}%<br>"
                f"Social Security: {ss_pct:.0f}%"
            )

            fig.add_annotation(
                x=mid_year,
                y=mid_total * 0.7,
                text=annotation_text,
                showarrow=True,
                arrowhead=2,
                arrowcolor="black",
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="black",
                borderwidth=1,
                align="left"
            )

    # Format chart
    currency_label = "Real" if currency_format == "real" else "Nominal"
    fig.update_layout(
        title=f"{title} ({currency_label} Dollars)",
        xaxis_title="Year",
        yaxis_title=f"Annual Income (${currency_label} Thousands)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            x=0.02, y=0.98,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="lightgray",
            borderwidth=1
        ),
        height=500
    )

    return fig


def create_asset_allocation_evolution(params: 'SimulationParams',
                                     year_by_year_details: Dict,
                                     title: str = "Asset Allocation Evolution",
                                     currency_format: str = "real") -> go.Figure:
    """
    Create stacked area chart showing asset allocation evolution over time.
    Shows both static allocation and age-based glide path evolution.

    Args:
        params: SimulationParams object with allocation weights
        year_by_year_details: Dictionary with year-by-year simulation details
        title: Chart title
        currency_format: "real" or "nominal" for axis labels

    Returns:
        Plotly figure
    """
    years = year_by_year_details.get('years', [])
    if not years:
        return go.Figure()

    # Get portfolio values over time
    portfolio_values = np.array(year_by_year_details.get('start_assets', [0] * len(years)))

    # Calculate years since retirement start for glide path
    years_since_start = np.array(years) - years[0]

    # Create age-based glide path (becoming more conservative over time)
    # Start with current allocation, gradually shift to more conservative
    initial_equity = params.w_equity
    initial_bonds = params.w_bonds
    initial_re = params.w_real_estate
    initial_cash = params.w_cash

    # Create glide path: reduce equity by ~0.5% per year, increase bonds/cash
    equity_reduction_per_year = 0.005  # 0.5% per year

    equity_weights = []
    bonds_weights = []
    re_weights = []
    cash_weights = []

    for years_elapsed in years_since_start:
        # Calculate equity reduction (capped at 50% of original)
        equity_reduction = min(equity_reduction_per_year * years_elapsed, initial_equity * 0.5)
        current_equity = max(initial_equity - equity_reduction, initial_equity * 0.5)

        # Redistribute reduced equity proportionally to bonds and cash
        reduction_amount = initial_equity - current_equity
        bonds_increase = reduction_amount * 0.7  # 70% to bonds
        cash_increase = reduction_amount * 0.3   # 30% to cash

        current_bonds = initial_bonds + bonds_increase
        current_cash = initial_cash + cash_increase
        current_re = initial_re  # Keep RE allocation stable

        # Normalize to ensure they sum to 1.0
        total = current_equity + current_bonds + current_re + current_cash
        if total > 0:
            current_equity /= total
            current_bonds /= total
            current_re /= total
            current_cash /= total

        equity_weights.append(current_equity)
        bonds_weights.append(current_bonds)
        re_weights.append(current_re)
        cash_weights.append(current_cash)

    # Convert to numpy arrays
    equity_weights = np.array(equity_weights)
    bonds_weights = np.array(bonds_weights)
    re_weights = np.array(re_weights)
    cash_weights = np.array(cash_weights)

    # Calculate dollar amounts for each asset class
    equity_values = portfolio_values * equity_weights / 1000  # Convert to thousands
    bonds_values = portfolio_values * bonds_weights / 1000
    re_values = portfolio_values * re_weights / 1000
    cash_values = portfolio_values * cash_weights / 1000

    fig = go.Figure()

    # Asset allocation traces (stacked from bottom to top)
    allocations = [
        ("Cash", cash_values, 'lightgray'),
        ("Real Estate", re_values, 'lightyellow'),
        ("Bonds", bonds_values, 'lightcoral'),
        ("Equities", equity_values, 'lightblue')
    ]

    # Add stacked areas
    for name, values, color in allocations:
        # Only add if there's meaningful allocation
        if np.max(values) > 0:
            fig.add_trace(go.Scatter(
                x=years,
                y=values,
                mode='lines',
                stackgroup='one',
                name=name,
                line=dict(width=0.5),
                fillcolor=color,
                hovertemplate=f"<b>{name}</b><br>" +
                             "<b>Year:</b> %{x}<br>" +
                             "<b>Value:</b> $%{y:.0f}K<br>" +
                             "<extra></extra>"
            ))

    # Add allocation percentage annotations at key points
    if len(years) > 10:
        # Show allocation at start and end
        start_year = years[0]
        end_year = years[-1]
        start_equity_pct = equity_weights[0] * 100
        end_equity_pct = equity_weights[-1] * 100

        # Annotation showing the glide path
        annotation_text = (
            f"<b>Glide Path Evolution</b><br>"
            f"{start_year}: {start_equity_pct:.0f}% Equities<br>"
            f"{end_year}: {end_equity_pct:.0f}% Equities<br>"
            f"Shift: {start_equity_pct - end_equity_pct:.1f}% to Bonds/Cash"
        )

        mid_year = years[len(years)//2]
        mid_total = np.sum([equity_values[len(years)//2], bonds_values[len(years)//2],
                           re_values[len(years)//2], cash_values[len(years)//2]])

        fig.add_annotation(
            x=mid_year,
            y=mid_total * 0.8,
            text=annotation_text,
            showarrow=True,
            arrowhead=2,
            arrowcolor="black",
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="black",
            borderwidth=1,
            align="left"
        )

    # Format chart
    currency_label = "Real" if currency_format == "real" else "Nominal"
    fig.update_layout(
        title=f"{title} ({currency_label} Dollars)<br><sub>Age-Based Glide Path: Equity allocation decreases 0.5% per year</sub>",
        xaxis_title="Year",
        yaxis_title=f"Portfolio Value (${currency_label} Thousands)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            x=0.02, y=0.98,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="lightgray",
            borderwidth=1
        ),
        height=500
    )

    return fig