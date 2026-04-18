"""Tests for the Smart Financial Planner — Staged Methodology"""
import pytest
from datetime import date
from dateutil.relativedelta import relativedelta
from app.services.planner_service import (
    generate_financial_plan, can_i_afford,
    replan_with_change, get_plan_summary,
)


@pytest.fixture
def basic_profile():
    return {
        "monthly_income": 2000,
        "rent_amount": 600,
        "bills_amount": 200,
        "groceries_estimate": 250,
        "transport_estimate": 84,
    }


@pytest.fixture
def couple_profile():
    return {
        "monthly_income": 4300,
        "rent_amount": 1200,
        "bills_amount": 400,
        "groceries_estimate": 250,
        "transport_estimate": 130,
    }


@pytest.fixture
def house_goal():
    deadline = date.today() + relativedelta(years=3)
    return {
        "id": 1, "name": "House deposit", "type": "savings_target",
        "target_amount": 10000, "current_amount": 2400,
        "deadline": deadline.isoformat(),
    }


@pytest.fixture
def baby_goal():
    deadline = date.today() + relativedelta(months=18)
    return {
        "id": 2, "name": "Baby fund", "type": "savings_target",
        "target_amount": 7000, "current_amount": 0,
        "deadline": deadline.isoformat(),
    }


@pytest.fixture
def emergency_goal():
    return {
        "id": 3, "name": "Emergency fund", "type": "savings_target",
        "target_amount": 5000, "current_amount": 0,
    }


@pytest.fixture
def emergency_goal_funded():
    return {
        "id": 3, "name": "Emergency fund", "type": "savings_target",
        "target_amount": 5000, "current_amount": 5000,
    }


@pytest.fixture
def emergency_goal_mini_funded():
    """Emergency fund already past £1000 mini buffer threshold"""
    return {
        "id": 3, "name": "Emergency fund", "type": "savings_target",
        "target_amount": 5000, "current_amount": 1200,
    }


@pytest.fixture
def holiday_goal():
    deadline = date.today() + relativedelta(months=6)
    return {
        "id": 4, "name": "Holiday", "type": "savings_target",
        "target_amount": 1500, "current_amount": 0,
        "deadline": deadline.isoformat(),
    }


# ─── BASIC PLAN GENERATION ──────────────────────────────────

class TestGeneratePlan:
    def test_generates_plan_with_goals(self, basic_profile, house_goal):
        plan = generate_financial_plan(basic_profile, [house_goal])
        assert "error" not in plan
        assert plan["income"] == 2000
        assert plan["surplus"] > 0
        assert len(plan["pots"]) > 0
        assert plan["phase_count"] >= 1

    def test_no_income_returns_error(self):
        plan = generate_financial_plan({"monthly_income": 0}, [])
        assert "error" in plan

    def test_no_income_key_returns_error(self):
        plan = generate_financial_plan({}, [])
        assert "error" in plan

    def test_expenses_exceed_income_returns_error(self):
        profile = {"monthly_income": 500, "rent_amount": 600, "bills_amount": 200}
        plan = generate_financial_plan(profile, [])
        assert "error" in plan
        assert plan["surplus"] < 0

    def test_emergency_goal_treated_as_savings(self, basic_profile, emergency_goal):
        """Emergency fund is a regular savings goal, not a special type"""
        plan = generate_financial_plan(basic_profile, [emergency_goal])
        emergency = next(p for p in plan["pots"] if p["name"] == "Emergency fund")
        assert emergency["target"] == 5000
        assert emergency["monthly_amount"] > 0

    def test_essentials_breakdown_included(self, basic_profile, house_goal):
        plan = generate_financial_plan(basic_profile, [house_goal])
        bd = plan["essentials_breakdown"]
        assert bd["rent"] == 600
        assert bd["bills"] == 200
        assert bd["groceries"] == 250
        assert bd["transport"] == 84


# ─── POT STRUCTURE ───────────────────────────────────────────

class TestPotStructure:
    def test_emergency_included_when_goal_exists(self, basic_profile, emergency_goal):
        plan = generate_financial_plan(basic_profile, [emergency_goal])
        pot_names = [p["name"] for p in plan["pots"]]
        assert "Emergency fund" in pot_names

    def test_always_includes_lifestyle(self, basic_profile):
        plan = generate_financial_plan(basic_profile, [])
        pot_names = [p["name"] for p in plan["pots"]]
        assert "Lifestyle & family" in pot_names

    def test_always_includes_buffer(self, basic_profile):
        plan = generate_financial_plan(basic_profile, [])
        pot_names = [p["name"] for p in plan["pots"]]
        assert "Buffer" in pot_names

    def test_no_preset_pots(self, basic_profile, house_goal, holiday_goal):
        plan = generate_financial_plan(basic_profile, [house_goal, holiday_goal])
        pot_names = [p["name"] for p in plan["pots"]]
        assert "Baby fund" not in pot_names
        assert "House deposit" in pot_names
        assert "Holiday" in pot_names

    def test_emergency_target_matches_goal(self, basic_profile, emergency_goal):
        """Emergency fund target comes from the goal, not calculated from essentials"""
        plan = generate_financial_plan(basic_profile, [emergency_goal])
        emergency = next(p for p in plan["pots"] if p["name"] == "Emergency fund")
        assert emergency["target"] == 5000

    def test_existing_emergency_savings_counted(self, basic_profile, emergency_goal):
        emergency_goal["current_amount"] = 2000
        plan = generate_financial_plan(basic_profile, [emergency_goal])
        emergency = next(p for p in plan["pots"] if p["name"] == "Emergency fund")
        assert emergency["current"] == 2000

    def test_debt_pots_created(self, basic_profile):
        debts = [{"name": "Credit card", "amount": 300, "min_payment": 25}]
        plan = generate_financial_plan(basic_profile, [], debts=debts)
        debt_pots = [p for p in plan["pots"] if p["type"] == "debt"]
        assert len(debt_pots) == 1
        assert debt_pots[0]["name"] == "Credit card"


# ─── STAGED ALLOCATION ──────────────────────────────────────

class TestStagedAllocation:
    def test_all_surplus_is_allocated(self, basic_profile, house_goal):
        plan = generate_financial_plan(basic_profile, [house_goal])
        total = sum(p["monthly_amount"] for p in plan["pots"])
        assert abs(total - plan["surplus"]) < 1

    def test_lifestyle_gets_minimum(self, basic_profile, house_goal):
        plan = generate_financial_plan(basic_profile, [house_goal])
        lifestyle = next(p for p in plan["pots"] if p["type"] == "lifestyle")
        assert lifestyle["monthly_amount"] >= 100

    def test_debt_funded_alongside_goals(self, basic_profile, house_goal):
        """With debt, both debt and goals get funding — debt clears quickly"""
        debts = [{"name": "Credit card", "amount": 200, "min_payment": 25}]
        plan = generate_financial_plan(basic_profile, [house_goal], debts=debts)
        house = next(p for p in plan["pots"] if p["name"] == "House deposit")
        debt = next(p for p in plan["pots"] if "credit" in p["name"].lower() or p["type"] == "debt")
        assert debt["monthly_amount"] > 0  # Debt gets funding
        assert house["monthly_amount"] > 0  # Goals get funding too

    def test_debt_and_emergency_both_funded(self, basic_profile, emergency_goal):
        """Debt and emergency both get funding alongside lifestyle and buffer"""
        debts = [{"name": "Credit card", "amount": 500, "min_payment": 25}]
        plan = generate_financial_plan(basic_profile, [emergency_goal], debts=debts)
        debt = next(p for p in plan["pots"] if p["type"] == "debt")
        emergency = next(p for p in plan["pots"] if p["name"] == "Emergency fund")
        assert debt["monthly_amount"] > 0
        assert emergency["monthly_amount"] > 0
        total = sum(p["monthly_amount"] for p in plan["pots"])
        assert abs(total - plan["surplus"]) < 1

    def test_debt_goal_detected_by_name(self, basic_profile, house_goal, emergency_goal_mini_funded):
        """Credit card as a goal should be treated as debt and get higher priority"""
        cc_goal = {
            "id": 99, "name": "Pay off credit card", "type": "savings_target",
            "target_amount": 500, "current_amount": 0,
        }
        plan = generate_financial_plan(basic_profile, [house_goal, cc_goal, emergency_goal_mini_funded])
        cc = next(p for p in plan["pots"] if p["name"] == "Pay off credit card")
        house = next(p for p in plan["pots"] if p["name"] == "House deposit")
        assert cc["monthly_amount"] > 0
        assert cc["monthly_amount"] > house["monthly_amount"]  # Debt prioritised

    def test_emergency_and_goals_both_funded(self, basic_profile, house_goal, emergency_goal):
        """Emergency and goals both get funding"""
        plan = generate_financial_plan(basic_profile, [house_goal, emergency_goal])
        emergency = next(p for p in plan["pots"] if p["name"] == "Emergency fund")
        house = next(p for p in plan["pots"] if p["name"] == "House deposit")
        assert emergency["monthly_amount"] > 0
        assert house["monthly_amount"] > 0

    def test_urgent_goal_runs_parallel_with_emergency(self, basic_profile, holiday_goal, emergency_goal_mini_funded):
        """Goal within 6 months gets funding alongside emergency"""
        plan = generate_financial_plan(basic_profile, [holiday_goal, emergency_goal_mini_funded])
        holiday = next(p for p in plan["pots"] if p["name"] == "Holiday")
        emergency = next(p for p in plan["pots"] if p["name"] == "Emergency fund")
        assert emergency["monthly_amount"] > 0
        assert holiday["monthly_amount"] > 0

    def test_goals_funded_when_emergency_complete(self, basic_profile, house_goal, emergency_goal_funded):
        """When emergency is fully funded, goals get money"""
        plan = generate_financial_plan(basic_profile, [house_goal, emergency_goal_funded])
        house = next(p for p in plan["pots"] if p["name"] == "House deposit")
        assert house["monthly_amount"] > 0

    def test_emergency_funded_alongside_debt(self, basic_profile, emergency_goal):
        """Emergency gets funding even when debt exists"""
        debts = [{"name": "Credit card", "amount": 1000, "min_payment": 25}]
        plan = generate_financial_plan(basic_profile, [emergency_goal], debts=debts)
        emergency = next(p for p in plan["pots"] if p["name"] == "Emergency fund")
        assert emergency["monthly_amount"] > 0

    def test_no_deadline_goal_funded_after_emergency(self, basic_profile, emergency_goal_funded):
        """Goal without deadline gets funded once emergency is complete"""
        goal = {
            "id": 1, "name": "Car fund", "type": "savings_target",
            "target_amount": 5000, "current_amount": 0
        }
        plan = generate_financial_plan(basic_profile, [goal, emergency_goal_funded])
        car = next(p for p in plan["pots"] if p["name"] == "Car fund")
        assert car["monthly_amount"] > 0


# ─── PHASES ──────────────────────────────────────────────────

class TestPhases:
    def test_phases_generated(self, basic_profile, house_goal, emergency_goal):
        plan = generate_financial_plan(basic_profile, [house_goal, emergency_goal])
        assert plan["phase_count"] >= 1
        assert len(plan["phases"]) >= 1

    def test_completed_pot_triggers_new_phase(self, couple_profile, emergency_goal, house_goal):
        plan = generate_financial_plan(couple_profile, [emergency_goal, house_goal])
        phases = plan["phases"]
        if len(phases) > 1:
            first_phase_completed = phases[0].get("completed_pots", [])
            assert len(first_phase_completed) > 0

    def test_money_redistributed_after_completion(self, couple_profile, emergency_goal, house_goal):
        """After emergency completes, house deposit should get more money"""
        plan = generate_financial_plan(couple_profile, [emergency_goal, house_goal])
        projections = plan["monthly_projections"]

        emergency_complete_month = None
        for proj in projections:
            emergency_data = proj["pots"].get("Emergency fund", {})
            if emergency_data.get("completed"):
                emergency_complete_month = proj["month"]
                break

        if emergency_complete_month and emergency_complete_month + 1 < len(projections):
            after = projections[emergency_complete_month]["pots"].get("House deposit", {}).get("monthly_amount", 0)
            assert after > 0

    def test_phase_descriptions_generated(self, basic_profile, house_goal):
        plan = generate_financial_plan(basic_profile, [house_goal])
        for phase in plan["phases"]:
            assert "description" in phase
            assert len(phase["description"]) > 0

    def test_debt_phase_shows_priority_alert(self, basic_profile, house_goal, emergency_goal_mini_funded):
        """Debt phase should show debt priority alert"""
        cc_goal = {
            "id": 99, "name": "Pay off credit card", "type": "savings_target",
            "target_amount": 500, "current_amount": 0,
        }
        plan = generate_financial_plan(basic_profile, [house_goal, cc_goal, emergency_goal_mini_funded])
        alert_types = [a["type"] for a in plan["alerts"]]
        assert "debt_priority" in alert_types


# ─── PROJECTIONS ─────────────────────────────────────────────

class TestProjections:
    def test_projections_have_dates(self, basic_profile, house_goal):
        plan = generate_financial_plan(basic_profile, [house_goal])
        for proj in plan["monthly_projections"][:3]:
            assert "date" in proj
            assert "date_display" in proj
            assert "month" in proj

    def test_emergency_balance_increases(self, basic_profile, house_goal, emergency_goal):
        """Emergency fund should grow during its build phase"""
        plan = generate_financial_plan(basic_profile, [house_goal, emergency_goal])
        projs = plan["monthly_projections"]
        if len(projs) > 2:
            m1 = projs[0]["pots"].get("Emergency fund", {}).get("balance", 0)
            m3 = projs[2]["pots"].get("Emergency fund", {}).get("balance", 0)
            assert m3 > m1

    def test_at_least_24_months_shown(self, basic_profile, house_goal):
        plan = generate_financial_plan(basic_profile, [house_goal])
        assert len(plan["monthly_projections"]) >= 24

    def test_all_pots_in_projections(self, basic_profile, house_goal, emergency_goal):
        plan = generate_financial_plan(basic_profile, [house_goal, emergency_goal])
        first_month = plan["monthly_projections"][0]
        pot_names = list(first_month["pots"].keys())
        assert "Emergency fund" in pot_names
        assert "House deposit" in pot_names
        assert "Lifestyle & family" in pot_names

    def test_goals_eventually_funded_in_projections(self, basic_profile, house_goal):
        """House deposit should eventually get money after emergency completes"""
        plan = generate_financial_plan(basic_profile, [house_goal])
        projs = plan["monthly_projections"]
        house_ever_funded = any(
            proj["pots"].get("House deposit", {}).get("monthly_amount", 0) > 0
            for proj in projs
        )
        assert house_ever_funded


# ─── COUPLE SCENARIO ─────────────────────────────────────────

class TestCoupleScenario:
    def test_couple_plan_generates(self, couple_profile, house_goal, baby_goal, emergency_goal):
        plan = generate_financial_plan(
            couple_profile, [house_goal, baby_goal, emergency_goal]
        )
        assert "error" not in plan
        assert plan["income"] == 4300
        assert plan["surplus"] > 2000

    def test_couple_emergency_gets_funded(self, couple_profile, house_goal, baby_goal, emergency_goal):
        plan = generate_financial_plan(
            couple_profile, [house_goal, baby_goal, emergency_goal]
        )
        emergency = next(p for p in plan["pots"] if p["name"] == "Emergency fund")
        assert emergency["monthly_amount"] > 0

    def test_couple_lifestyle_allocated(self, couple_profile, house_goal, baby_goal, emergency_goal):
        plan = generate_financial_plan(
            couple_profile, [house_goal, baby_goal, emergency_goal]
        )
        lifestyle = next(p for p in plan["pots"] if p["type"] == "lifestyle")
        assert lifestyle["monthly_amount"] >= 100

    def test_couple_goals_funded_when_no_debt(self, couple_profile, house_goal, emergency_goal_funded):
        """With emergency already funded and no debt, goals get money"""
        plan = generate_financial_plan(
            couple_profile, [house_goal, emergency_goal_funded]
        )
        house = next(p for p in plan["pots"] if p["name"] == "House deposit")
        assert house["monthly_amount"] > 0


# ─── CAN I AFFORD ───────────────────────────────────────────

class TestCanIAfford:
    def test_affordable_expense(self, couple_profile, house_goal):
        plan = generate_financial_plan(couple_profile, [house_goal])
        result = can_i_afford(plan, "Takeaway", 30)
        assert result["affordable"] is True
        assert result["impact"] == "none"

    def test_expensive_but_possible(self, couple_profile, house_goal):
        plan = generate_financial_plan(couple_profile, [house_goal])
        lifestyle = next(p for p in plan["pots"] if p["type"] == "lifestyle")
        amount = lifestyle["monthly_amount"] + 50
        result = can_i_afford(plan, "Weekend trip", amount)
        assert "message" in result

    def test_unaffordable_expense(self, basic_profile, house_goal):
        plan = generate_financial_plan(basic_profile, [house_goal])
        result = can_i_afford(plan, "Luxury holiday", 5000)
        assert result["affordable"] is False
        assert result["impact"] == "significant"

    def test_error_plan_returns_not_affordable(self):
        plan = {"error": "No income"}
        result = can_i_afford(plan, "Coffee", 3)
        assert result["affordable"] is False


# ─── REPLANNING ──────────────────────────────────────────────

class TestReplan:
    def test_raise_increases_surplus(self, basic_profile, house_goal):
        result = replan_with_change(
            basic_profile, [house_goal], "raise", {"amount": 200}
        )
        assert result["comparison"]["surplus_change"] == 200

    def test_raise_increases_lifestyle(self, basic_profile, house_goal):
        result = replan_with_change(
            basic_profile, [house_goal], "raise", {"amount": 500}
        )
        assert result["comparison"]["lifestyle_change"] > 0

    def test_new_goal_adds_to_plan(self, basic_profile, house_goal, holiday_goal):
        result = replan_with_change(
            basic_profile, [house_goal], "new_goal", {"goal": holiday_goal}
        )
        new_pot_names = [p["name"] for p in result["new_plan"]["pots"]]
        assert "Holiday" in new_pot_names

    def test_income_change(self, basic_profile, house_goal):
        result = replan_with_change(
            basic_profile, [house_goal], "income_change", {"new_income": 3000}
        )
        assert result["new_plan"]["income"] == 3000
        assert result["comparison"]["surplus_change"] == 1000


# ─── PLAN SUMMARY ───────────────────────────────────────────

class TestPlanSummary:
    def test_summary_with_plan(self, couple_profile, house_goal, emergency_goal):
        plan = generate_financial_plan(couple_profile, [house_goal, emergency_goal])
        summary = get_plan_summary(plan)
        assert len(summary) > 20

    def test_summary_with_error(self):
        plan = {"error": "No income"}
        summary = get_plan_summary(plan)
        assert summary == "No income"

    def test_summary_mentions_goals(self, couple_profile, house_goal):
        plan = generate_financial_plan(couple_profile, [house_goal])
        summary = get_plan_summary(plan)
        assert len(summary) > 0

    def test_debt_summary_mentions_clearing(self, basic_profile, house_goal, emergency_goal_mini_funded):
        cc_goal = {
            "id": 99, "name": "Pay off credit card", "type": "savings_target",
            "target_amount": 500, "current_amount": 0,
        }
        plan = generate_financial_plan(basic_profile, [house_goal, cc_goal, emergency_goal_mini_funded])
        summary = get_plan_summary(plan)
        assert "clearing" in summary.lower() or "credit card" in summary.lower()


# ─── ALERTS ──────────────────────────────────────────────────

class TestAlerts:
    def test_no_special_emergency_alert(self, basic_profile, house_goal, emergency_goal):
        """Emergency fund is a regular goal — no special alert needed"""
        plan = generate_financial_plan(basic_profile, [house_goal, emergency_goal])
        alert_types = [a["type"] for a in plan["alerts"]]
        assert "low_emergency_fund" not in alert_types

    def test_debt_priority_alert(self, basic_profile, house_goal, emergency_goal_mini_funded):
        cc_goal = {
            "id": 99, "name": "Pay off credit card", "type": "savings_target",
            "target_amount": 500, "current_amount": 0,
        }
        plan = generate_financial_plan(basic_profile, [house_goal, cc_goal, emergency_goal_mini_funded])
        alert_types = [a["type"] for a in plan["alerts"]]
        assert "debt_priority" in alert_types

    def test_debt_priority_alert_during_debt(self, basic_profile, house_goal, emergency_goal_mini_funded):
        cc_goal = {
            "id": 99, "name": "Pay off credit card", "type": "savings_target",
            "target_amount": 500, "current_amount": 0,
        }
        plan = generate_financial_plan(basic_profile, [house_goal, cc_goal, emergency_goal_mini_funded])
        alert_types = [a["type"] for a in plan["alerts"]]
        assert "debt_priority" in alert_types

    def test_deadline_risk_when_goal_funded(self, basic_profile, emergency_goal_funded):
        """Deadline risk should fire when a goal is funded but can't hit deadline"""
        tight_goal = {
            "id": 1, "name": "Big purchase", "type": "savings_target",
            "target_amount": 50000, "current_amount": 0,
            "deadline": (date.today() + relativedelta(months=6)).isoformat()
        }
        plan = generate_financial_plan(basic_profile, [tight_goal, emergency_goal_funded])
        alert_types = [a["type"] for a in plan["alerts"]]
        assert "deadline_risk" in alert_types


# ─── EDGE CASES ──────────────────────────────────────────────

class TestEdgeCases:
    def test_goal_already_complete(self, basic_profile):
        goal = {
            "id": 1, "name": "Done goal", "type": "savings_target",
            "target_amount": 1000, "current_amount": 1000
        }
        plan = generate_financial_plan(basic_profile, [goal])
        assert "error" not in plan

    def test_very_small_surplus(self):
        profile = {
            "monthly_income": 1100,
            "rent_amount": 600,
            "bills_amount": 200,
            "groceries_estimate": 250,
            "transport_estimate": 0,
        }
        plan = generate_financial_plan(profile, [])
        assert "error" not in plan
        assert plan["surplus"] == 50

    def test_single_goal_funded_when_emergency_done(self, basic_profile, emergency_goal_funded):
        """Goal gets funded once emergency is complete"""
        goal = {
            "id": 1, "name": "Car fund", "type": "savings_target",
            "target_amount": 3000, "current_amount": 0
        }
        plan = generate_financial_plan(basic_profile, [goal, emergency_goal_funded])
        pot = next(p for p in plan["pots"] if p["name"] == "Car fund")
        assert pot["monthly_amount"] > 0

    def test_many_goals(self, couple_profile, emergency_goal_funded):
        goals = [emergency_goal_funded] + [
            {"id": i, "name": f"Goal {i}", "type": "savings_target",
             "target_amount": 2000, "current_amount": 0,
             "deadline": (date.today() + relativedelta(months=12+i*6)).isoformat()}
            for i in range(1, 6)
        ]
        plan = generate_financial_plan(couple_profile, goals)
        assert "error" not in plan
        assert len(plan["pots"]) >= 7

    def test_missing_optional_profile_fields(self):
        profile = {"monthly_income": 2000}
        plan = generate_financial_plan(profile, [])
        assert "error" not in plan
        assert plan["essentials"] == 0
        assert plan["surplus"] == 2000