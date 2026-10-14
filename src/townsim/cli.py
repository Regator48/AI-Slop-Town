import argparse, json
from .model import Config, Simulation

def main():
    p = argparse.ArgumentParser(description="Run the TownSim macro/banking model")
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--scenario", default="baseline", choices=["baseline", "inflation", "recession", "credit_crunch", "bank_run", "deposit_flight", "housing_crisis", "energy_shock", "pandemic", "market_crash", "gold_shock"])
    p.add_argument("--output", default="townsim.json")
    args = p.parse_args()
    sim = Simulation(Config(seed=args.seed, scenario=args.scenario))
    sim.run(args.days)
    sim.save(args.output)
    print(json.dumps(sim.state.metrics[-1] if sim.state.metrics else {"day": sim.state.day}, indent=2))

if __name__ == "__main__": main()
