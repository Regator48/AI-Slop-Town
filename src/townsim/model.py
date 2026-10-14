from __future__ import annotations
import json, math, random
from dataclasses import asdict, dataclass, field
from pathlib import Path

@dataclass
class Config:
    people: int = 10_000
    firms: int = 500
    banks: int = 3
    seed: int = 1
    policy_rate: float = .05
    scenario: str = "baseline"

@dataclass
class Bank:
    deposits: float = 25_000_000
    loans: float = 20_000_000
    securities: float = 5_000_000
    reserves: float = 3_000_000
    capital: float = 2_500_000
    profit: float = 0.0
    failed: bool = False

@dataclass
class State:
    day: int = 0
    cash: float = 15_000_000
    deposits: float = 75_000_000
    loans: float = 60_000_000
    output: float = 0.0
    prices: float = 1.0
    unemployment: float = .04
    wages: float = 20.0
    policy_rate: float = .05
    gold: float = 2000.0
    stocks: float = 100.0
    government_debt: float = 20_000_000
    deficit: float = 0.0
    defaults: float = 0.0
    bank_failures: int = 0
    quality_of_life: float = 1.0
    metrics: list[dict] = field(default_factory=list)

class Simulation:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.rng = random.Random(self.config.seed)
        self.state = State(policy_rate=self.config.policy_rate)
        self.banks = [Bank() for _ in range(self.config.banks)]
        self._apply_scenario_setup()

    def _apply_scenario_setup(self):
        s, c = self.state, self.config.scenario
        if c in {"inflation", "energy_shock"}: s.prices = 1.08
        if c in {"recession", "credit_crunch"}: s.unemployment = .10
        if c in {"bank_run", "deposit_flight"}:
            s.deposits *= .85
            for b in self.banks: b.deposits *= .85; b.reserves *= .60
        if c == "housing_crisis": s.prices = .97
        if c == "market_crash": s.stocks = 70.0
        if c == "gold_shock": s.gold = 2400.0

    def step(self):
        s, c, r = self.state, self.config, self.rng
        s.day += 1
        # Policy reaction: simple Taylor-style rule with scenario shock.
        inflation = (s.prices - 1.0) * .02 + r.gauss(0, .001)
        target = .02
        shock = {"inflation": .003, "recession": -.002, "energy_shock": .004}.get(c, 0)
        s.policy_rate = max(0.0, s.policy_rate + .12 * (inflation - target) + shock)
        # Labor, production, wages, and daily needs.
        desired_unemployment = {"recession": .12, "credit_crunch": .11, "pandemic": .16}.get(c, .04)
        s.unemployment += .04 * (desired_unemployment - s.unemployment) + r.gauss(0, .001)
        s.unemployment = min(.30, max(.01, s.unemployment))
        s.wages *= 1 + .00005 - .0003 * s.unemployment + r.gauss(0, .0002)
        workers = c.people if False else self.config.people * (1 - s.unemployment)
        productivity = 1 + .12 * math.sin(s.day / 90) + r.gauss(0, .01)
        s.output = workers * s.wages / 365 * productivity
        demand = self.config.people * (8.0 + .7 * s.wages / 20) / s.prices
        if c in {"recession", "pandemic"}: demand *= .90
        s.prices *= 1 + .00012 * (demand / max(s.output, 1) - .85) + .00015 * (1 if c == "energy_shock" else 0)
        s.prices = max(.5, s.prices)
        # Banking: deposit/loan rates, interest, credit losses, reserve drain.
        loan_rate = s.policy_rate + .035
        deposit_rate = max(0, s.policy_rate - .01)
        total_profit = 0.0
        for b in self.banks:
            if b.failed: continue
            interest = b.loans * loan_rate / 365 - b.deposits * deposit_rate / 365
            new_defaults = max(0, b.loans * (s.unemployment - .04) * .00004)
            if c in {"credit_crunch", "bank_run"}: new_defaults *= 2.5
            b.loans -= new_defaults
            b.capital -= new_defaults
            b.profit += interest - new_defaults
            total_profit += interest - new_defaults
            b.reserves += b.profit / 365
            if b.capital < b.deposits * .02 or b.reserves < 0:
                b.failed = True; s.bank_failures += 1
        s.defaults += sum(max(0, b.loans * (s.unemployment - .04) * .00004) for b in self.banks)
        # Fiscal sector and household financial stress.
        taxes = max(0, s.output * .20)
        benefits = self.config.people * s.unemployment * 18
        s.deficit = benefits + 1500 - taxes
        s.government_debt += s.deficit
        s.deposits += s.output - demand - s.deficit
        s.deposits = max(1, s.deposits)
        s.loans = sum(b.loans for b in self.banks)
        s.cash = s.deposits * .10
        # Asset prices: transparent reduced-form channels.
        real_rate = s.policy_rate - inflation
        s.gold *= math.exp(-.10 * real_rate + .15 * (s.unemployment - .04) + r.gauss(0, .003))
        earnings = s.output * (1 - s.unemployment) / max(s.prices, .1)
        s.stocks *= math.exp(.00001 * earnings - .25 * (s.policy_rate - .05) - .35 * s.unemployment + r.gauss(0, .008))
        s.quality_of_life = max(0, 1 - .7 * s.unemployment - .2 * max(0, s.prices - 1))
        if s.day % 30 == 0: self.record_metrics(inflation, loan_rate, deposit_rate)
        self.check_invariants()
        return s

    def record_metrics(self, inflation=0.0, loan_rate=0.0, deposit_rate=0.0):
        s = self.state
        s.metrics.append({"day": s.day, "output": s.output, "cpi": s.prices, "inflation": inflation,
            "unemployment": s.unemployment, "wages": s.wages, "deposits": s.deposits,
            "loans": s.loans, "loan_rate": loan_rate, "deposit_rate": deposit_rate,
            "policy_rate": s.policy_rate, "gold": s.gold, "stocks": s.stocks,
            "government_debt": s.government_debt, "defaults": s.defaults,
            "bank_failures": s.bank_failures, "quality_of_life": s.quality_of_life})

    def check_invariants(self):
        s = self.state
        assert s.deposits >= 0 and s.loans >= 0 and s.prices > 0
        for b in self.banks:
            assert b.deposits >= 0 and b.loans >= 0 and b.reserves > -1e12

    def run(self, days: int):
        for _ in range(days): self.step()
        return self.state

    def save(self, path: str | Path):
        data = {"config": asdict(self.config), "state": asdict(self.state), "banks": [asdict(b) for b in self.banks]}
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str | Path):
        data = json.loads(Path(path).read_text())
        sim = cls(Config(**data["config"]))
        sim.state = State(**data["state"])
        sim.banks = [Bank(**b) for b in data["banks"]]
        return sim
