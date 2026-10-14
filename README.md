# TownSim

TownSim is a deterministic, CPU-first economic sandbox of a 10,000-person town with households, firms, banks, a central bank/Treasury layer, stock/gold market channels, and scheduled shock scenarios.

It is a reduced-form model for experimentation and regression testing, not financial advice and not a full reproduction of the U.S. financial system.

## Fresh-checkout install/run/test

```bash
python -m townsim.cli --days 365 --seed 7 --scenario baseline --output out.json --csv out.csv
python -m unittest discover -s tests -v
```

The repository includes a top-level `townsim` package bridge so `python -m townsim.cli` and tests work from a fresh checkout without extra environment variables.

## CLI examples

```bash
python -m townsim.cli --days 180 --seed 9 --scenario supply_disruption --output run.json
python -m townsim.cli --days 60 --seed 4 --scenario baseline --event 30:bank_run_wave --event 40:credit_tightening --output event_run.json
python -m townsim.cli --load run.json --days 30 --output resumed.json
```

## Model scope

- Households: cash, income, deposits, debt, employment, welfare, daily-needs spending categories.
- Firms: industry, workers, wages, output, inventory, prices, revenue, costs, debt, equity, bankruptcy flag.
- Loans: principal, rate, maturity, borrower type, delinquency, collateral, recovery, assigned bank.
- Banks: reserves, loans, securities, fixed assets, deposits, wholesale/interbank funding proxy, central-bank borrowing, equity capital, provisions, profits.
- Policy/fiscal: policy-rate target rule, reserve remuneration, discount window, Treasury bills/bonds yields, taxes/transfers/spending, debt issuance and deficits.
- Markets: stock index via earnings and discount rates; gold via real rates, inflation stress, fiscal/bank stress, and seeded noise.

## Scenarios

`baseline`, `inflation`, `recession`, `bank_run`, `deposit_flight`, `credit_crunch`, `housing_decline`, `housing_crisis`, `energy_shock`, `supply_disruption`, `pandemic`, `market_crash`, `sovereign_fiscal_shock`, `gold_shock`, `terror_shock`

Scenario schedules are deterministic by seed and can be extended with `--event DAY:EVENT`.
The `terror_shock` schedule models panic/uncertainty behavior (confidence drop, risk-premium widening, and stock sell-off with flight-to-safety pressure).

## Persistence and metrics

- JSON checkpoint save/load includes RNG state for deterministic replay.
- Daily internal metrics are retained in-memory.
- Monthly summaries are stored in `state.metrics` and exportable via `--csv`.

## Hardware note

V100 SXM2 modules require compatible server/HGX-style platforms with appropriate carrier, cooling, and power; they are not directly installable in an i3-8100 desktop.

See `docs/ARCHITECTURE.md` for equations, units, assumptions, calibration hooks, and limitations.
