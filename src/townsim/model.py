from __future__ import annotations

import ast
import csv
import json
import math
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

INDUSTRIES = [
    "food_agriculture",
    "energy_utilities",
    "housing_construction",
    "manufacturing",
    "transport",
    "retail",
    "healthcare",
    "education",
    "government",
    "finance",
    "professional_services",
]

DAILY_NEEDS = [
    "food_agriculture",
    "energy_utilities",
    "housing_construction",
    "transport",
    "healthcare",
    "education",
    "retail",
    "professional_services",
]


@dataclass
class Config:
    people: int = 10_000
    firms: int = 500
    banks: int = 3
    seed: int = 1
    policy_rate: float = 0.05
    scenario: str = "baseline"
    event_schedule: dict[int, list[str]] = field(default_factory=dict)


@dataclass
class HouseholdState:
    cash: list[float]
    income: list[float]
    deposits: list[float]
    debt: list[float]
    employed: list[int]
    welfare: list[float]
    expenses: dict[str, list[float]]


@dataclass
class FirmState:
    industry: list[int]
    workers: list[int]
    wages: list[float]
    output: list[float]
    inventory: list[float]
    prices: list[float]
    revenue: list[float]
    costs: list[float]
    debt: list[float]
    equity: list[float]
    active: list[int]


@dataclass
class LoanBook:
    principal: list[float]
    rate: list[float]
    maturity_days: list[int]
    borrower_type: list[str]
    delinquency_days: list[int]
    collateral: list[float]
    recovery_rate: list[float]
    bank_id: list[int]


@dataclass
class Bank:
    reserves: float = 3_000_000
    loans: float = 20_000_000
    securities: float = 5_000_000
    fixed_assets: float = 750_000
    deposits: float = 25_000_000
    wholesale_funding: float = 1_500_000
    cb_borrowing: float = 0.0
    equity: float = 2_500_000
    provisions: float = 150_000
    profit: float = 0.0
    failed: bool = False


@dataclass
class CentralBank:
    policy_rate_target: float = 0.05
    reserve_remuneration: float = 0.03
    discount_window_rate: float = 0.06


@dataclass
class Treasury:
    tax_rate: float = 0.20
    spending_daily: float = 1_500.0
    transfer_per_unemployed: float = 18.0
    debt: float = 20_000_000
    deficit: float = 0.0
    bill_rate: float = 0.045
    bond_rate: float = 0.055
    bills_outstanding: float = 12_000_000
    bonds_outstanding: float = 8_000_000


@dataclass
class State:
    day: int = 0
    cash: float = 15_000_000
    deposits: float = 75_000_000
    loans: float = 60_000_000
    output: float = 0.0
    prices: float = 1.0
    unemployment: float = 0.04
    wages: float = 20.0
    policy_rate: float = 0.05
    gold: float = 2000.0
    stocks: float = 100.0
    government_debt: float = 20_000_000
    deficit: float = 0.0
    defaults: float = 0.0
    bank_failures: int = 0
    quality_of_life: float = 1.0
    consumer_confidence: float = 1.0
    market_fear: float = 0.0
    shortage_index: float = 0.0
    consumption: float = 0.0
    credit_growth: float = 0.0
    metrics: list[dict[str, float]] = field(default_factory=list)
    daily_metrics: list[dict[str, float]] = field(default_factory=list)


SCENARIO_EVENT_SCHEDULES = {
    "baseline": {},
    "inflation": {30: ["energy_shock_mild"], 90: ["demand_boom"]},
    "recession": {30: ["employment_shock"], 90: ["credit_tightening"]},
    "bank_run": {45: ["bank_run_wave"], 46: ["bank_run_wave"]},
    "deposit_flight": {60: ["deposit_flight_wave"]},
    "credit_crunch": {45: ["credit_tightening"], 120: ["credit_tightening"]},
    "housing_decline": {40: ["housing_decline_wave"], 120: ["housing_decline_wave"]},
    "housing_crisis": {40: ["housing_decline_wave"], 120: ["housing_decline_wave"]},
    "energy_shock": {20: ["energy_shock"], 100: ["energy_shock_mild"]},
    "supply_disruption": {35: ["supply_disruption"], 36: ["supply_disruption"]},
    "pandemic": {25: ["pandemic_wave"], 120: ["pandemic_wave"]},
    "market_crash": {30: ["equity_crash"], 31: ["equity_crash"]},
    "sovereign_fiscal_shock": {90: ["fiscal_shock"], 180: ["fiscal_shock"]},
    "gold_shock": {50: ["gold_risk_spike"], 140: ["gold_risk_spike"]},
    "terror_shock": {15: ["terror_attack_shock"], 16: ["panic_selloff"]},
}


class Simulation:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.rng = random.Random(self.config.seed)
        self.state = State(policy_rate=self.config.policy_rate)
        self.central_bank = CentralBank(policy_rate_target=self.config.policy_rate)
        self.treasury = Treasury(debt=self.state.government_debt)
        self.banks = [Bank() for _ in range(self.config.banks)]
        self.households = self._init_households()
        self.firms = self._init_firms()
        self.loans = self._init_loans()
        self.event_schedule = self._build_event_schedule()
        self._apply_scenario_setup()

    def _init_households(self) -> HouseholdState:
        n, r = self.config.people, self.rng
        income = [max(12.0, r.gauss(80.0, 22.0)) for _ in range(n)]
        employed = [1 if r.random() > 0.04 else 0 for _ in range(n)]
        welfare = [8.0 if e == 0 else 0.0 for e in employed]
        deposits = [max(25.0, r.gauss(7500.0, 1500.0)) for _ in range(n)]
        cash = [d * 0.12 for d in deposits]
        debt = [max(0.0, r.gauss(2200.0, 1400.0)) for _ in range(n)]
        expenses = {
            need: [max(0.1, r.gauss(need_base, need_base * 0.15)) for _ in range(n)]
            for need, need_base in {
                "food_agriculture": 5.5,
                "energy_utilities": 3.5,
                "housing_construction": 9.5,
                "transport": 2.8,
                "healthcare": 1.5,
                "education": 1.0,
                "retail": 2.2,
                "professional_services": 1.8,
            }.items()
        }
        return HouseholdState(
            cash=cash,
            income=income,
            deposits=deposits,
            debt=debt,
            employed=employed,
            welfare=welfare,
            expenses=expenses,
        )

    def _init_firms(self) -> FirmState:
        m, r = self.config.firms, self.rng
        industry = [i % len(INDUSTRIES) for i in range(m)]
        workers = [max(2, int(r.gauss(16, 5))) for _ in range(m)]
        wages = [max(14.0, r.gauss(22.0, 4.0)) for _ in range(m)]
        output = [max(8.0, r.gauss(35.0, 8.0)) for _ in range(m)]
        inventory = [max(15.0, r.gauss(100.0, 18.0)) for _ in range(m)]
        prices = [max(0.7, r.gauss(1.0, 0.09)) for _ in range(m)]
        debt = [max(0.0, r.gauss(80_000.0, 15_000.0)) for _ in range(m)]
        equity = [max(40_000.0, r.gauss(180_000.0, 25_000.0)) for _ in range(m)]
        return FirmState(
            industry=industry,
            workers=workers,
            wages=wages,
            output=output,
            inventory=inventory,
            prices=prices,
            revenue=[0.0] * m,
            costs=[0.0] * m,
            debt=debt,
            equity=equity,
            active=[1] * m,
        )

    def _init_loans(self) -> LoanBook:
        r = self.rng
        household_loan_count = max(200, self.config.people // 30)
        firm_loan_count = max(120, self.config.firms // 2)
        principal: list[float] = []
        rate: list[float] = []
        maturity_days: list[int] = []
        borrower_type: list[str] = []
        delinquency_days: list[int] = []
        collateral: list[float] = []
        recovery_rate: list[float] = []
        bank_id: list[int] = []
        for _ in range(household_loan_count):
            principal.append(max(400.0, r.gauss(8_000.0, 2_200.0)))
            rate.append(0.06 + r.random() * 0.025)
            maturity_days.append(r.randint(365, 365 * 8))
            borrower_type.append("household")
            delinquency_days.append(0)
            collateral.append(principal[-1] * (0.25 + 0.25 * r.random()))
            recovery_rate.append(0.35 + 0.25 * r.random())
            bank_id.append(r.randrange(self.config.banks))
        for _ in range(firm_loan_count):
            principal.append(max(10_000.0, r.gauss(220_000.0, 65_000.0)))
            rate.append(0.055 + r.random() * 0.03)
            maturity_days.append(r.randint(365 * 2, 365 * 12))
            borrower_type.append("firm")
            delinquency_days.append(0)
            collateral.append(principal[-1] * (0.45 + 0.35 * r.random()))
            recovery_rate.append(0.45 + 0.25 * r.random())
            bank_id.append(r.randrange(self.config.banks))
        return LoanBook(
            principal=principal,
            rate=rate,
            maturity_days=maturity_days,
            borrower_type=borrower_type,
            delinquency_days=delinquency_days,
            collateral=collateral,
            recovery_rate=recovery_rate,
            bank_id=bank_id,
        )

    def _build_event_schedule(self) -> dict[int, list[str]]:
        base = {
            int(day): list(events)
            for day, events in SCENARIO_EVENT_SCHEDULES.get(self.config.scenario, {}).items()
        }
        for day, events in (self.config.event_schedule or {}).items():
            base.setdefault(int(day), []).extend(events)
        return base

    def _apply_scenario_setup(self) -> None:
        s, scenario = self.state, self.config.scenario
        if scenario in {"inflation", "energy_shock"}:
            s.prices = 1.08
        if scenario in {"recession", "credit_crunch", "pandemic"}:
            s.unemployment = 0.10
        if scenario in {"bank_run", "deposit_flight"}:
            s.deposits *= 0.90
            for bank in self.banks:
                bank.deposits *= 0.90
                bank.reserves *= 0.70
        if scenario in {"housing_decline", "housing_crisis"}:
            s.prices = 0.97
        if scenario == "market_crash":
            s.stocks = 80.0
        if scenario == "gold_shock":
            s.gold = 2300.0
        if scenario == "terror_shock":
            s.consumer_confidence = 0.95
            s.market_fear = 0.08
        self.state.loans = sum(self.loans.principal)

    def _apply_event(self, event_name: str) -> None:
        s = self.state
        if event_name == "energy_shock":
            s.prices *= 1.015
        elif event_name == "energy_shock_mild":
            s.prices *= 1.008
        elif event_name == "demand_boom":
            s.wages *= 1.004
        elif event_name == "employment_shock":
            s.unemployment = min(0.30, s.unemployment + 0.012)
        elif event_name == "credit_tightening":
            self.central_bank.policy_rate_target = min(0.15, self.central_bank.policy_rate_target + 0.003)
        elif event_name == "bank_run_wave":
            for bank in self.banks:
                run_outflow = bank.deposits * 0.05
                bank.deposits -= run_outflow
                bank.reserves -= run_outflow
            self._apply_household_deposit_outflow(0.015)
        elif event_name == "deposit_flight_wave":
            for bank in self.banks:
                outflow = bank.deposits * 0.03
                bank.deposits -= outflow
                bank.wholesale_funding += outflow * 0.6
            self._apply_household_deposit_outflow(0.008)
        elif event_name == "housing_decline_wave":
            s.prices *= 0.992
        elif event_name == "supply_disruption":
            s.shortage_index += 0.015
            for idx, active in enumerate(self.firms.active):
                if active and self.firms.industry[idx] in {0, 3, 4}:
                    self.firms.output[idx] *= 0.96
        elif event_name == "pandemic_wave":
            s.unemployment = min(0.30, s.unemployment + 0.015)
            s.shortage_index += 0.02
        elif event_name == "equity_crash":
            s.stocks *= 0.92
        elif event_name == "fiscal_shock":
            self.treasury.spending_daily *= 1.03
            self.treasury.tax_rate = max(0.15, self.treasury.tax_rate - 0.005)
        elif event_name == "gold_risk_spike":
            s.gold *= 1.03
        elif event_name == "terror_attack_shock":
            s.market_fear = min(1.0, s.market_fear + 0.65)
            s.consumer_confidence = max(0.45, s.consumer_confidence * 0.82)
            s.unemployment = min(0.30, s.unemployment + 0.006)
            s.stocks *= 0.88
            s.gold *= 1.02
        elif event_name == "panic_selloff":
            s.market_fear = min(1.0, s.market_fear + 0.20)
            s.stocks *= 0.95
            self._apply_household_deposit_outflow(0.005)

    def _apply_household_deposit_outflow(self, outflow_share: float) -> None:
        for idx, dep in enumerate(self.households.deposits):
            outflow = dep * outflow_share
            self.households.deposits[idx] = max(0.0, dep - outflow)
            self.households.cash[idx] += outflow * 0.2

    def _daily_policy(self, inflation_estimate: float) -> None:
        s = self.state
        self.central_bank.policy_rate_target = max(
            0.0,
            min(
                0.20,
                self.central_bank.policy_rate_target
                + 0.18 * (inflation_estimate - 0.02)
                + 0.08 * (0.05 - s.unemployment),
            ),
        )
        s.policy_rate += 0.25 * (self.central_bank.policy_rate_target - s.policy_rate)
        s.policy_rate = max(0.0, min(0.20, s.policy_rate))
        self.central_bank.reserve_remuneration = max(0.0, s.policy_rate - 0.01)
        self.central_bank.discount_window_rate = s.policy_rate + 0.012
        self.treasury.bill_rate = max(0.0, s.policy_rate - 0.002)
        self.treasury.bond_rate = max(self.treasury.bill_rate + 0.004, s.policy_rate + 0.004)
        if s.market_fear > 0.0:
            # Flight-to-safety channel: short safe yields compress in high fear regimes.
            self.treasury.bill_rate = max(0.0, self.treasury.bill_rate - 0.003 * s.market_fear)

    def _labor_and_production(self) -> tuple[float, float]:
        s, f, r = self.state, self.firms, self.rng
        desired_unemployment = {
            "recession": 0.11,
            "credit_crunch": 0.10,
            "pandemic": 0.15,
        }.get(self.config.scenario, 0.04)
        s.unemployment += 0.05 * (desired_unemployment - s.unemployment) + r.gauss(0, 0.0007)
        s.unemployment = min(0.30, max(0.01, s.unemployment))

        total_output = 0.0
        total_payroll = 0.0
        shortages = 0.0
        for i, active in enumerate(f.active):
            if not active:
                continue
            margin = f.revenue[i] - f.costs[i]
            if margin < -2_500:
                f.workers[i] = max(1, f.workers[i] - 1)
            elif margin > 2_500 and f.inventory[i] < f.output[i] * 3:
                f.workers[i] = min(300, f.workers[i] + 1)

            layoff_pressure = 0.02 if s.unemployment > 0.1 else 0.0
            if r.random() < layoff_pressure:
                f.workers[i] = max(1, f.workers[i] - 1)

            productivity = max(0.4, 1.0 + 0.07 * math.sin((s.day + i) / 60))
            f.wages[i] = max(12.0, f.wages[i] * (1 + 0.00004 - 0.0002 * s.unemployment + r.gauss(0, 0.00015)))
            produced = f.workers[i] * f.wages[i] / 365.0 * productivity
            f.output[i] = produced
            f.inventory[i] += produced
            total_output += produced
            payroll = f.workers[i] * f.wages[i]
            total_payroll += payroll

            capacity = max(1.0, f.inventory[i])
            if capacity < produced * 1.2:
                shortages += 0.0005

        employed_people = max(0, int(round(self.config.people * (1 - s.unemployment))))
        if employed_people > 0:
            avg_income = total_payroll / max(1, employed_people)
            for idx in range(self.config.people):
                is_employed = 1 if idx < employed_people else 0
                self.households.employed[idx] = is_employed
                self.households.welfare[idx] = 8.0 if not is_employed else 0.0
                self.households.income[idx] = avg_income if is_employed else 8.0

        s.wages = total_payroll / max(1, employed_people)
        s.output = total_output
        s.shortage_index = min(0.5, max(0.0, s.shortage_index * 0.95 + shortages))
        return total_output, total_payroll

    def _household_consumption(self) -> tuple[float, float]:
        s, h = self.state, self.households
        need_weights = {
            "food_agriculture": 1.0,
            "energy_utilities": 0.8,
            "housing_construction": 1.2,
            "transport": 0.6,
            "healthcare": 0.4,
            "education": 0.3,
            "retail": 0.5,
            "professional_services": 0.35,
        }
        total_consumption = 0.0
        unmet = 0.0
        for idx in range(self.config.people):
            resources = h.cash[idx] + h.deposits[idx] * 0.02 + h.income[idx] + h.welfare[idx]
            spend_budget = max(4.0, resources * (0.32 * s.consumer_confidence))
            spending = 0.0
            for need in DAILY_NEEDS:
                base = h.expenses[need][idx] * need_weights[need]
                adjusted = base * s.prices * (1.0 + 0.2 * s.shortage_index)
                if need in {"retail", "professional_services", "transport"}:
                    adjusted *= max(0.45, 1.0 - 0.7 * s.market_fear)
                item_spend = min(max(0.1, adjusted), max(0.0, spend_budget - spending))
                spending += item_spend
            if spending < spend_budget * 0.7:
                unmet += (spend_budget * 0.7 - spending)

            h.cash[idx] = max(0.0, h.cash[idx] + h.income[idx] + h.welfare[idx] - spending)
            desired_deposit = h.cash[idx] * 0.35
            h.deposits[idx] += desired_deposit
            h.cash[idx] -= desired_deposit
            total_consumption += spending

        s.consumption = total_consumption
        return total_consumption, unmet

    def _update_firm_financials(self, demand: float) -> None:
        f, r = self.firms, self.rng
        demand_per_firm = demand / max(1, self.config.firms)
        for i, active in enumerate(f.active):
            if not active:
                continue
            sell_qty = min(f.inventory[i], demand_per_firm / max(0.4, f.prices[i]))
            revenue = sell_qty * f.prices[i]
            labor_cost = f.workers[i] * f.wages[i]
            input_cost = revenue * 0.45 * (1 + 0.25 * self.state.shortage_index)
            debt_cost = f.debt[i] * (self.state.policy_rate + 0.02) / 365.0
            costs = labor_cost + input_cost + debt_cost
            profit = revenue - costs
            f.revenue[i] = revenue
            f.costs[i] = costs
            f.equity[i] += profit
            f.inventory[i] = max(0.0, f.inventory[i] - sell_qty)
            f.prices[i] = max(0.4, f.prices[i] * (1 + 0.0002 * (demand_per_firm - sell_qty) / max(1.0, sell_qty + 1)))
            if profit < -5_000:
                f.debt[i] += min(20_000.0, -profit * 0.4)
            elif profit > 2_500:
                f.debt[i] = max(0.0, f.debt[i] - profit * 0.1)
            if f.equity[i] < 5_000 and r.random() < 0.15:
                f.active[i] = 0

    def _banking_and_loans(self) -> tuple[float, float, float, float]:
        s, r = self.state, self.rng
        deposit_rate = max(0.0, self.central_bank.reserve_remuneration - 0.003)
        base_loan_rate = max(0.01, s.policy_rate + 0.025 + 0.03 * s.market_fear)

        new_defaults = 0.0
        recoveries = 0.0
        interest_income = [0.0] * len(self.banks)
        interest_expense = [0.0] * len(self.banks)
        principal_repaid = [0.0] * len(self.banks)

        for loan_idx, principal in enumerate(self.loans.principal):
            if principal <= 0:
                continue
            bank_id = self.loans.bank_id[loan_idx]
            bank = self.banks[bank_id]
            if bank.failed:
                continue

            effective_rate = max(base_loan_rate, self.loans.rate[loan_idx])
            interest = principal * effective_rate / 365.0
            self.loans.principal[loan_idx] += interest
            interest_income[bank_id] += interest
            bank.loans += interest

            remaining_days = max(1, self.loans.maturity_days[loan_idx])
            scheduled_principal = principal / remaining_days
            payment = scheduled_principal + interest

            stress = (s.unemployment - 0.04) * 3.0 + s.shortage_index
            delinquency_chance = max(0.0, 0.002 + stress * 0.01)
            if self.config.scenario in {"credit_crunch", "bank_run", "recession"}:
                delinquency_chance *= 1.8
            if r.random() < delinquency_chance:
                self.loans.delinquency_days[loan_idx] += 1
            else:
                self.loans.delinquency_days[loan_idx] = max(0, self.loans.delinquency_days[loan_idx] - 1)

            default_trigger = self.loans.delinquency_days[loan_idx] > 5 or r.random() < max(0.0, delinquency_chance - 0.01) * 0.06
            if default_trigger:
                charge_off = min(self.loans.principal[loan_idx], principal * 0.25)
                recovered = min(charge_off, self.loans.collateral[loan_idx] * self.loans.recovery_rate[loan_idx])
                net_loss = max(0.0, charge_off - recovered)
                self.loans.principal[loan_idx] -= charge_off
                bank.loans -= charge_off
                bank.provisions += net_loss * 0.2
                bank.equity -= net_loss
                new_defaults += net_loss
                recoveries += recovered
                bank.reserves += recovered
                self.loans.delinquency_days[loan_idx] = 0
            else:
                self.loans.principal[loan_idx] = max(0.0, self.loans.principal[loan_idx] - payment)
                bank.loans = max(0.0, bank.loans - scheduled_principal)
                principal_repaid[bank_id] += scheduled_principal

            self.loans.maturity_days[loan_idx] = max(1, self.loans.maturity_days[loan_idx] - 1)

        household_deposits_total = sum(self.households.deposits)
        for i, bank in enumerate(self.banks):
            if bank.failed:
                continue
            share = household_deposits_total / max(1, len(self.banks))
            updated_deposits = max(1.0, 0.95 * bank.deposits + 0.05 * share)
            deposit_delta = updated_deposits - bank.deposits
            bank.deposits = updated_deposits
            bank.reserves += deposit_delta
            dep_interest = bank.deposits * deposit_rate / 365.0
            interest_expense[i] = dep_interest
            bank.profit += interest_income[i] - dep_interest - bank.provisions * 0.002
            bank.reserves += principal_repaid[i] + bank.profit * 0.08
            if bank.reserves < bank.deposits * 0.06:
                needed = bank.deposits * 0.08 - bank.reserves
                bank.cb_borrowing += max(0.0, needed)
                bank.reserves += max(0.0, needed)
                bank.profit -= max(0.0, needed) * self.central_bank.discount_window_rate / 365.0

            liquidity_ratio = bank.reserves / max(1.0, bank.deposits)
            capital_ratio = bank.equity / max(1.0, bank.loans + bank.securities + bank.fixed_assets)
            if liquidity_ratio < 0.015 or capital_ratio < 0.02:
                bank.failed = True
                s.bank_failures += 1
            bank.equity += bank.profit
            bank.profit = 0.0

        if self.config.scenario in {"bank_run", "deposit_flight"} and (s.day % 7 == 0):
            household_outflow = 0.01 if self.config.scenario == "deposit_flight" else 0.016
            self._apply_household_deposit_outflow(household_outflow)
            for bank in self.banks:
                if bank.failed:
                    continue
                outflow = bank.deposits * (0.012 if self.config.scenario == "deposit_flight" else 0.018)
                bank.deposits -= outflow
                bank.reserves -= outflow

        total_loans = sum(max(0.0, p) for p in self.loans.principal)
        prior_loans = max(1.0, s.loans)
        s.credit_growth = (total_loans - prior_loans) / prior_loans
        s.loans = total_loans
        s.defaults += new_defaults
        return deposit_rate, base_loan_rate, new_defaults, recoveries

    def _government(self, output: float) -> None:
        s = self.state
        taxes = max(0.0, output * self.treasury.tax_rate)
        unemployed = self.config.people * s.unemployment
        transfers = unemployed * self.treasury.transfer_per_unemployed
        spending = self.treasury.spending_daily
        self.treasury.deficit = spending + transfers - taxes
        self.treasury.debt += self.treasury.deficit
        issuance = max(0.0, self.treasury.deficit)
        self.treasury.bills_outstanding += issuance * 0.6
        self.treasury.bonds_outstanding += issuance * 0.4
        s.government_debt = self.treasury.debt
        s.deficit = self.treasury.deficit

    def _asset_prices(self, inflation_estimate: float) -> None:
        s = self.state
        firm_earnings = sum(max(0.0, rev - cost) for rev, cost in zip(self.firms.revenue, self.firms.costs))
        expected_cash_flow = firm_earnings / max(1, self.config.firms)
        risk_free = self.treasury.bill_rate
        equity_risk_premium = 0.04 + 0.3 * s.unemployment + 0.5 * s.shortage_index + 0.35 * s.market_fear
        discount = max(0.01, risk_free + equity_risk_premium)
        fair_index = max(20.0, expected_cash_flow / discount)
        s.stocks = max(10.0, (0.96 * s.stocks + 0.04 * fair_index) * (1.0 - 0.03 * s.market_fear))

        real_rate = s.policy_rate - inflation_estimate
        bank_stress = sum(1 for b in self.banks if b.failed) / max(1, len(self.banks))
        currency_stress = max(0.0, s.deficit / max(1.0, s.government_debt))
        gold_demand = 0.5 * bank_stress + 0.7 * currency_stress + 0.4 * max(0.0, inflation_estimate - 0.02) + 0.8 * s.market_fear
        s.gold *= math.exp(-0.08 * real_rate + 0.18 * gold_demand + self.rng.gauss(0.0, 0.0015))

    def step(self) -> State:
        s = self.state
        s.day += 1
        s.market_fear = max(0.0, s.market_fear * 0.965)
        s.consumer_confidence = min(1.0, s.consumer_confidence + (1.0 - s.consumer_confidence) * 0.02)

        for event in self.event_schedule.get(s.day, []):
            self._apply_event(event)

        inflation_estimate = max(-0.05, (s.prices - 1.0) * 0.02 + self.rng.gauss(0, 0.0008))
        self._daily_policy(inflation_estimate)
        output, payroll = self._labor_and_production()
        consumption, unmet_needs = self._household_consumption()

        demand_pressure = consumption / max(1.0, output)
        s.prices *= 1 + 0.00014 * (demand_pressure - 0.9) + 0.0003 * s.shortage_index
        s.prices = max(0.5, min(3.0, s.prices))

        self._update_firm_financials(consumption)
        deposit_rate, loan_rate, defaults, recoveries = self._banking_and_loans()
        self._government(output)

        total_deposits = sum(self.households.deposits)
        s.deposits = max(1.0, total_deposits)
        s.cash = sum(self.households.cash)

        self._asset_prices(inflation_estimate)
        s.quality_of_life = max(
            0.0,
            1
            - 0.7 * s.unemployment
            - 0.2 * max(0.0, s.prices - 1)
            - 0.2 * s.shortage_index
            - 0.1 * s.market_fear,
        )

        self.record_daily_metrics(inflation_estimate, loan_rate, deposit_rate, defaults, recoveries, payroll, unmet_needs)
        if s.day % 30 == 0:
            self.record_metrics(inflation_estimate, loan_rate, deposit_rate)

        self.check_invariants()
        return s

    def record_daily_metrics(
        self,
        inflation: float,
        loan_rate: float,
        deposit_rate: float,
        defaults: float,
        recoveries: float,
        payroll: float,
        unmet_needs: float,
    ) -> None:
        s = self.state
        avg_firm_price = sum(self.firms.prices) / max(1, len(self.firms.prices))
        capital_ratio = sum(
            b.equity / max(1.0, b.loans + b.securities + b.fixed_assets)
            for b in self.banks
            if not b.failed
        ) / max(1, sum(1 for b in self.banks if not b.failed))
        liquidity_ratio = sum(
            b.reserves / max(1.0, b.deposits)
            for b in self.banks
            if not b.failed
        ) / max(1, sum(1 for b in self.banks if not b.failed))
        inequality_proxy = max(0.0, (max(self.households.deposits) - min(self.households.deposits)) / max(1.0, sum(self.households.deposits) / len(self.households.deposits)))
        s.daily_metrics.append(
            {
                "day": float(s.day),
                "output": s.output,
                "cpi": s.prices,
                "inflation": inflation,
                "unemployment": s.unemployment,
                "wages": s.wages,
                "consumption": s.consumption,
                "deposits": s.deposits,
                "loans": s.loans,
                "credit_growth": s.credit_growth,
                "loan_rate": loan_rate,
                "deposit_rate": deposit_rate,
                "policy_rate": s.policy_rate,
                "defaults": defaults,
                "recoveries": recoveries,
                "capital_ratio": capital_ratio,
                "liquidity_ratio": liquidity_ratio,
                "stocks": s.stocks,
                "gold": s.gold,
                "government_debt": s.government_debt,
                "deficit": s.deficit,
                "shortage_index": s.shortage_index,
                "consumer_confidence": s.consumer_confidence,
                "market_fear": s.market_fear,
                "avg_firm_price": avg_firm_price,
                "payroll": payroll,
                "unmet_needs": unmet_needs,
                "inequality_proxy": inequality_proxy,
                "quality_of_life": s.quality_of_life,
            }
        )

    def record_metrics(self, inflation: float = 0.0, loan_rate: float = 0.0, deposit_rate: float = 0.0) -> None:
        s = self.state
        summary = dict(s.daily_metrics[-1]) if s.daily_metrics else {}
        summary.update(
            {
                "day": float(s.day),
                "inflation": inflation,
                "loan_rate": loan_rate,
                "deposit_rate": deposit_rate,
                "yield_curve_slope": self.treasury.bond_rate - self.treasury.bill_rate,
                "bank_failures": float(s.bank_failures),
            }
        )
        s.metrics.append(summary)

    def check_invariants(self) -> None:
        s = self.state
        if s.deposits < 0 or s.loans < 0 or s.prices <= 0:
            raise ValueError(
                f"Macro invariant failed: deposits={s.deposits}, loans={s.loans}, prices={s.prices}"
            )
        for idx, bank in enumerate(self.banks):
            if bank.deposits < 0:
                raise ValueError(f"Bank {idx} deposits negative: {bank.deposits}")
            if bank.loans < 0:
                raise ValueError(f"Bank {idx} loans negative: {bank.loans}")
            assets = bank.reserves + bank.loans + bank.securities + bank.fixed_assets
            liabilities = bank.deposits + bank.wholesale_funding + bank.cb_borrowing
            residual = assets - liabilities - bank.equity
            if abs(residual) > 2_500_000:
                raise ValueError(
                    f"Bank {idx} balance-sheet mismatch assets-liabilities-equity={residual:.2f}"
                )
            if bank.reserves < -1e-3:
                raise ValueError(f"Bank {idx} reserves below zero: {bank.reserves}")

    def run(self, days: int) -> State:
        for _ in range(days):
            self.step()
        return self.state

    def export_metrics_csv(self, path: str | Path) -> None:
        rows = self.state.metrics
        out_path = Path(path)
        if not rows:
            out_path.write_text("day\n")
            return
        fieldnames = sorted(rows[0].keys())
        with out_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _serialize_rng_state(self) -> str:
        return repr(self.rng.getstate())

    @staticmethod
    def _deserialize_rng_state(serialized_state: str) -> Any:
        return ast.literal_eval(serialized_state)

    def save(self, path: str | Path) -> None:
        data = {
            "config": asdict(self.config),
            "state": asdict(self.state),
            "banks": [asdict(bank) for bank in self.banks],
            "central_bank": asdict(self.central_bank),
            "treasury": asdict(self.treasury),
            "households": asdict(self.households),
            "firms": asdict(self.firms),
            "loans": asdict(self.loans),
            "event_schedule": {str(day): events for day, events in self.event_schedule.items()},
            "rng_state": self._serialize_rng_state(),
        }
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "Simulation":
        data = json.loads(Path(path).read_text())
        config_data = dict(data["config"])
        if "event_schedule" in config_data:
            config_data["event_schedule"] = {
                int(day): list(events) for day, events in config_data["event_schedule"].items()
            }
        sim = cls(Config(**config_data))
        sim.state = State(**data["state"])
        sim.banks = [Bank(**bank_data) for bank_data in data["banks"]]
        sim.central_bank = CentralBank(**data.get("central_bank", {}))
        sim.treasury = Treasury(**data.get("treasury", {}))
        sim.households = HouseholdState(**data["households"])
        sim.firms = FirmState(**data["firms"])
        sim.loans = LoanBook(**data["loans"])
        sim.event_schedule = {
            int(day): list(events)
            for day, events in data.get("event_schedule", {}).items()
        }
        rng_state = data.get("rng_state")
        if rng_state is not None:
            sim.rng.setstate(cls._deserialize_rng_state(rng_state))
        return sim
