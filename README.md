# TownSim

A deterministic, CPU-first research simulation of a 10,000-person town with households, firms, banks, government, stocks, gold, and daily needs. It is an extensible model, not a complete replica of the U.S. financial system or financial advice.

## Run

```bash
python -m townsim.cli --days 365 --seed 7 --scenario baseline --output out.json
python -m unittest discover -s tests -v
```

The model uses only the Python standard library. Optional GPU acceleration can be added behind the `Backend` boundary; SXM2 V100 modules require compatible server/HGX carrier hardware, cooling, power delivery, and host support and are not directly installable in an i3-8100 desktop.

## Scope

Included: households, jobs, firms, production, inventories, food/housing/energy/transport/health spending, taxes and benefits, deposits and loans, interest, reserves, capital, defaults, deposit flight, policy rates, government debt, a simplified equity market, gold, shocks, checkpoints, metrics, and invariant checks.

Deliberately abstracted: legal-entity detail, derivatives, shadow banking, international flows, intraday payment settlement, detailed U.S. regulation/reporting, market microstructure, and real-data ingestion. See `docs/ARCHITECTURE.md`.
