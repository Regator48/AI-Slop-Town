# Architecture and limitations

## Design goals

- Deterministic seeded simulation with reproducible checkpoint replay.
- CPU-only standard-library implementation (lists/arrays by index) with no CUDA/network requirement.
- Transparent reduced-form accounting and policy channels suitable for tests and extensions.

## Core state vectors

### Households

Per-household arrays: `cash`, `income`, `deposits`, `debt`, `employed`, `welfare`, and per-category daily expenses.

Daily-needs categories:

- food/agriculture
- energy/utilities
- housing/construction
- transport
- retail
- healthcare
- education
- professional services

### Firms

Per-firm arrays: `industry`, `workers`, `wages`, `output`, `inventory`, `prices`, `revenue`, `costs`, `debt`, `equity`, `active`.

Industries represented:

- food/agriculture
- energy/utilities
- housing/construction
- manufacturing
- transport
- retail
- healthcare
- education
- government
- finance
- professional services

### Loans

Per-loan arrays: `principal`, `rate`, `maturity_days`, `borrower_type`, `delinquency_days`, `collateral`, `recovery_rate`, `bank_id`.

## Banking accounting

Each bank tracks assets and liabilities explicitly.

- Assets: reserves, loans, securities, fixed assets
- Liabilities/funding: deposits, wholesale/interbank funding proxy, central-bank borrowing
- Capital/equity and provisions tracked separately

Daily mechanics:

- Loan interest accrual and amortization
- Deposit interest expense
- Delinquency transitions and charge-offs
- Collateral recovery and provisions
- Discount-window borrowing when liquidity is stressed
- Liquidity and capital ratio checks

Invariant checks raise explicit `ValueError` messages for negative balances and balance-sheet mismatches:

`assets - liabilities - equity ≈ 0` (within configured tolerance for reduced-form aggregation)

## Central bank and Treasury layer

- Policy-rate target with simple reaction rule to inflation/unemployment gaps
- Reserve remuneration and discount-window rate
- Treasury taxes, transfers, spending, deficits, debt stock
- Bill and bond yield proxies with maturity spread (`bond_rate - bill_rate`)
- Debt issuance split into bills/bonds when deficits are positive

## Market channels

Stock index (reduced form):

- `fair_index = expected_cash_flow / (risk_free + equity_risk_premium)`
- index mean-reverts toward `fair_index`

Gold (reduced form):

- responds to real rates, inflation pressure, bank stress, fiscal/currency-stress proxy, and seeded noise

No predictive claims are made.

## Scenario schedules

Scenarios use deterministic event schedules keyed by day, plus optional CLI-injected events (`--event DAY:EVENT`).

Included scenarios: baseline growth, inflation, recession, bank run/deposit flight, credit crunch, housing decline, energy shock, supply disruption, pandemic-like shock, market crash, sovereign/fiscal shock, gold shock.

## Reporting and persistence

- Daily internal metrics (`state.daily_metrics`)
- Monthly summaries (`state.metrics`) including output/GDP proxy, CPI/inflation, unemployment, wages, inequality proxy, consumption, credit growth/defaults, bank capital/liquidity, deposits, rates, yield curve, stock index, gold, debt/deficit, quality-of-life proxy
- JSON checkpoint round-trip includes RNG state for deterministic replay
- CSV export for monthly metrics

## Units and assumptions

- Time step: 1 simulated day
- Rates: annualized decimals (e.g., `0.05 = 5%`)
- Monetary values: abstract USD-like scalar units
- Population/firm/loan levels are stylized and intended for directional behavior/testing

## Calibration hooks (public aggregate US data)

The model is structured so scenario/event parameters, policy rule weights, and initial state levels can be calibrated to public aggregate series (for example policy rates, unemployment, CPI, yield curve, credit growth, bank capital/liquidity aggregates).

## Limitations

This remains a reduced-form model. It does not include full institution-level legal/regulatory detail, derivatives books, payment-system intraday settlement, global capital flows, or market microstructure.

Hardware note: V100 SXM2 modules require a compatible server/HGX platform and are not directly installable in an i3-8100 desktop.
