"""
Tax and Social Security utility functions
Extracted from legacy app.py to prevent import conflicts in multipage app
"""

def get_state_tax_rates(state, filing_status):
    """Get combined federal + state tax rates for common states"""
    # These are rough estimates combining federal and state effective rates
    state_rates = {
        'Federal Only': {
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'CA': {  # High state tax
            'MFJ': [(0, 0.13), (94_300, 0.31), (201_000, 0.36)],
            'Single': [(0, 0.13), (47_150, 0.31), (100_500, 0.36)]
        },
        'NY': {  # High state tax
            'MFJ': [(0, 0.14), (94_300, 0.30), (201_000, 0.35)],
            'Single': [(0, 0.14), (47_150, 0.30), (100_500, 0.35)]
        },
        'TX': {  # No state income tax
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'FL': {  # No state income tax
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'WA': {  # No state income tax
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'NV': {  # No state income tax
            'MFJ': [(0, 0.10), (94_300, 0.22), (201_000, 0.24)],
            'Single': [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        },
        'PA': {  # Flat state tax
            'MFJ': [(0, 0.13), (94_300, 0.25), (201_000, 0.27)],
            'Single': [(0, 0.13), (47_150, 0.25), (100_500, 0.27)]
        },
        'OH': {  # Moderate state tax
            'MFJ': [(0, 0.12), (94_300, 0.26), (201_000, 0.29)],
            'Single': [(0, 0.12), (47_150, 0.26), (100_500, 0.29)]
        },
        'IL': {  # Moderate state tax
            'MFJ': [(0, 0.12), (94_300, 0.27), (201_000, 0.30)],
            'Single': [(0, 0.12), (47_150, 0.27), (100_500, 0.30)]
        }
    }

    return state_rates.get(state, state_rates['Federal Only'])[filing_status]


def calculate_social_security_benefit(year, start_year, retirement_age, annual_benefit, scenario, custom_reduction, reduction_start_year, start_age):
    """Calculate Social Security benefit for a given year with projected funding scenarios"""
    # Calculate age based on actual retirement age, not hardcoded 65
    age_at_year = retirement_age + (year - start_year)

    # Not eligible yet
    if age_at_year < start_age:
        return 0

    base_benefit = annual_benefit

    # Apply scenario-based reductions
    if year >= reduction_start_year:
        if scenario == 'conservative':
            # Full 19% cut starting 2034, no reform
            reduction = 0.19
        elif scenario == 'moderate':
            # Gradual reduction to 10% cut, partial reforms
            years_since_cut = year - reduction_start_year
            reduction = min(0.10, 0.05 + (years_since_cut * 0.01))  # Gradual to 10%
        elif scenario == 'optimistic':
            # Full benefits maintained through reforms
            reduction = 0.0
        elif scenario == 'custom':
            # User-defined reduction
            reduction = custom_reduction
        else:
            reduction = 0.0
    else:
        reduction = 0.0

    return base_benefit * (1 - reduction)