// AR5 GWP Values (Intergovernmental Panel on Climate Change, 5th Assessment Report)
export const GWP_AR5 = {
    CO2: 1,
    CH4: 28,
    N2O: 264,   // CALC-04 FIX: IPCC AR5 WG1 Table 8.7 (2013) — correct value is 264, not 265
};

// Standard GWP for the application (default to AR5)
export const DEFAULT_GWP = GWP_AR5;

export const BOUNDARY_OPTIONS = {
    'Operational Control': [
        'Wholly Owned',
        'Majority Operated',
        'Minority Operated',
        'Contractual Authority'
    ],
    'Financial Control': [
        'Wholly Owned',
        'Consolidated Subsidiary',
        'Financial Lease'
    ],
    'Equity Share': [
        'Proportional Interest',
        'Equity Method Investment',
        'Joint Venture'
    ]
};
