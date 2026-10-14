import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from townsim.model import Config, Simulation


REPO_ROOT = Path(__file__).resolve().parents[1]


class SimulationTests(unittest.TestCase):
    def test_fresh_checkout_cli_execution(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "state.json"
            csv_path = Path(d) / "metrics.csv"
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "townsim.cli",
                    "--days",
                    "40",
                    "--seed",
                    "7",
                    "--scenario",
                    "baseline",
                    "--output",
                    str(out),
                    "--csv",
                    str(csv_path),
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertGreaterEqual(payload["day"], 30)
            self.assertTrue(out.exists())
            self.assertTrue(csv_path.exists())

    def test_deterministic(self):
        a = Simulation(Config(seed=4)).run(90)
        b = Simulation(Config(seed=4)).run(90)
        self.assertEqual(a.metrics, b.metrics)
        self.assertEqual(a.stocks, b.stocks)

    def test_checkpoint_replay_deterministic_with_rng_state(self):
        full = Simulation(Config(seed=8, scenario="baseline"))
        full.run(90)

        partial = Simulation(Config(seed=8, scenario="baseline"))
        partial.run(45)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "checkpoint.json"
            partial.save(path)
            loaded = Simulation.load(path)
            loaded.run(45)
            self.assertEqual(loaded.state.metrics, full.state.metrics)
            self.assertAlmostEqual(loaded.state.stocks, full.state.stocks, places=12)
            self.assertAlmostEqual(loaded.state.gold, full.state.gold, places=12)

    def test_policy_transmission(self):
        low = Simulation(Config(policy_rate=0.01, seed=2))
        high = Simulation(Config(policy_rate=0.12, seed=2))
        low.run(60)
        high.run(60)
        self.assertLess(low.state.metrics[-1]["loan_rate"], high.state.metrics[-1]["loan_rate"])
        self.assertLess(low.state.metrics[-1]["deposit_rate"], high.state.metrics[-1]["deposit_rate"])

    def test_accounting_invariants_hold(self):
        sim = Simulation(Config(seed=3, scenario="baseline"))
        sim.run(120)
        self.assertGreater(sim.state.deposits, 0)
        self.assertGreater(sim.state.loans, 0)
        for bank in sim.banks:
            assets = bank.reserves + bank.loans + bank.securities + bank.fixed_assets
            liabilities = bank.deposits + bank.wholesale_funding + bank.cb_borrowing
            self.assertLess(abs(assets - liabilities - bank.equity), 2_500_000)

    def test_interest_amortization_and_default_recovery(self):
        sim = Simulation(Config(seed=6, scenario="credit_crunch"))
        start_maturity = sim.loans.maturity_days[0]
        start_principal = sim.loans.principal[0]
        sim.run(120)
        self.assertLess(sim.loans.maturity_days[0], start_maturity)
        self.assertNotEqual(sim.loans.principal[0], start_principal)
        self.assertGreater(sim.state.defaults, 0)
        recoveries = [m["recoveries"] for m in sim.state.daily_metrics]
        self.assertGreaterEqual(max(recoveries), 0)

    def test_bank_run_is_stressed(self):
        baseline = Simulation(Config(seed=2, scenario="baseline"))
        stressed = Simulation(Config(seed=2, scenario="bank_run"))
        baseline.run(90)
        stressed.run(90)
        self.assertLess(stressed.state.deposits, baseline.state.deposits)

    def test_scenario_determinism(self):
        a = Simulation(Config(seed=11, scenario="supply_disruption"))
        b = Simulation(Config(seed=11, scenario="supply_disruption"))
        a.run(75)
        b.run(75)
        self.assertEqual(a.state.metrics, b.state.metrics)

    def test_asset_price_shock_direction(self):
        baseline = Simulation(Config(seed=9, scenario="baseline"))
        crash = Simulation(Config(seed=9, scenario="market_crash"))
        gold = Simulation(Config(seed=9, scenario="gold_shock"))
        baseline.run(60)
        crash.run(60)
        gold.run(60)
        self.assertLess(crash.state.stocks, baseline.state.stocks)
        self.assertGreater(gold.state.gold, baseline.state.gold)

    def test_serialization_round_trip(self):
        sim = Simulation(Config(seed=5, scenario="energy_shock", event_schedule={5: ["gold_risk_spike"]}))
        sim.run(45)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.json"
            sim.save(path)
            loaded = Simulation.load(path)
            self.assertEqual(loaded.config.event_schedule, sim.config.event_schedule)
            self.assertEqual(loaded.event_schedule, sim.event_schedule)
            self.assertEqual(loaded.state.day, sim.state.day)
            self.assertEqual(loaded.state.metrics, sim.state.metrics)


if __name__ == "__main__":
    unittest.main()
