import argparse
import json

from .model import Config, Simulation


def _parse_event_schedule(event_args: list[str]) -> dict[int, list[str]]:
    schedule: dict[int, list[str]] = {}
    for arg in event_args:
        day_text, event_name = arg.split(":", 1)
        day = int(day_text)
        schedule.setdefault(day, []).append(event_name)
    return schedule


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TownSim macro/banking model")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--scenario",
        default="baseline",
        choices=[
            "baseline",
            "inflation",
            "recession",
            "credit_crunch",
            "bank_run",
            "deposit_flight",
            "housing_decline",
            "housing_crisis",
            "energy_shock",
            "supply_disruption",
            "pandemic",
            "market_crash",
            "sovereign_fiscal_shock",
            "gold_shock",
            "terror_shock",
        ],
    )
    parser.add_argument("--event", action="append", default=[], help="Extra scheduled event in DAY:EVENT format")
    parser.add_argument("--output", default="townsim.json")
    parser.add_argument("--csv", help="Optional path for monthly CSV metrics export")
    parser.add_argument("--load", help="Load existing checkpoint before running")
    args = parser.parse_args()

    if args.load:
        sim = Simulation.load(args.load)
        if args.seed != 1:
            sim.config.seed = args.seed
    else:
        schedule = _parse_event_schedule(args.event)
        sim = Simulation(Config(seed=args.seed, scenario=args.scenario, event_schedule=schedule))

    sim.run(args.days)
    sim.save(args.output)
    if args.csv:
        sim.export_metrics_csv(args.csv)
    print(json.dumps(sim.state.metrics[-1] if sim.state.metrics else {"day": sim.state.day}, indent=2))


if __name__ == "__main__":
    main()
