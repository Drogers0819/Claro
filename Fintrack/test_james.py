"""Test scenario: James, 24, Bristol, 4 goals including overdraft"""
from app.services.planner_service import generate_financial_plan, can_i_afford, get_plan_summary

profile = {
    "monthly_income": 1950,
    "rent_amount": 650,
    "bills_amount": 180,
    "groceries_estimate": 200,
    "transport_estimate": 120,
}

goals = [
    {
        "id": 1, "name": "Pay off student overdraft", "type": "savings_target",
        "target_amount": 2000, "current_amount": 0,
    },
    {
        "id": 2, "name": "Holiday Japan", "type": "savings_target",
        "target_amount": 3500, "current_amount": 400,
        "deadline": "2027-07-01",
    },
    {
        "id": 3, "name": "New laptop", "type": "savings_target",
        "target_amount": 1200, "current_amount": 200,
        "deadline": "2026-12-01",
    },
    {
        "id": 4, "name": "House deposit", "type": "savings_target",
        "target_amount": 25000, "current_amount": 0,
    },
]

print("=" * 60)
print("JAMES'S FINANCIAL SCENARIO")
print("=" * 60)

essentials = 650 + 180 + 200 + 120
surplus = 1950 - essentials
print(f"\nIncome:     £{1950}")
print(f"Essentials: £{essentials}")
print(f"Surplus:    £{surplus}")

print("\n" + "=" * 60)
print("TEST 1: Plan generation")
print("=" * 60)

plan = generate_financial_plan(profile, goals)

if plan.get("error"):
    print(f"\nERROR: {plan['error']}")
else:
    print(f"\nSurplus: £{plan['surplus']}")
    print(f"Phases: {plan['phase_count']}")
    print(f"\nPot allocations:")
    total = 0
    for p in plan["pots"]:
        total += p["monthly_amount"]
        status = ""
        if p.get("completed"):
            status = " [DONE]"
        elif p.get("months_to_target"):
            status = f" [{p['months_to_target']} months]"
        print(f"  {p['name']:30s} £{p['monthly_amount']:>7.2f}/mo  "
              f"(£{p.get('current', 0):>8,.0f} of £{p.get('target', 0) or 0:>8,.0f}){status}")

    print(f"\n  {'TOTAL':30s} £{total:>7.2f}/mo")
    print(f"  {'SURPLUS':30s} £{plan['surplus']:>7.2f}/mo")

    print(f"\nPhase details:")
    for phase in plan["phases"]:
        print(f"\n  Phase {phase['phase']} ({phase['duration_months']} months):")
        print(f"    Active: {', '.join(phase['active_pots'])}")
        if phase.get("completed_pots"):
            print(f"    Completed: {', '.join(phase['completed_pots'])}")
        print(f"    {phase['description']}")

    print(f"\nAlerts:")
    if plan["alerts"]:
        for alert in plan["alerts"]:
            print(f"  [{alert['severity'].upper()}] {alert['message']}")
    else:
        print("  None")

print("\n" + "=" * 60)
print("TEST 2: Plan summary (whisper)")
print("=" * 60)

summary = get_plan_summary(plan)
print(f"\n  \"{summary}\"")

print("\n" + "=" * 60)
print("TEST 3: Can James afford a £150 concert ticket?")
print("=" * 60)

afford1 = can_i_afford(plan, "Concert ticket", 150)
print(f"\n  Affordable: {afford1['affordable']}")
print(f"  Impact: {afford1.get('impact', 'N/A')}")
print(f"  Message: {afford1['message']}")

print("\n" + "=" * 60)
print("TEST 4: Can James afford a £800 Amsterdam weekend?")
print("=" * 60)

afford2 = can_i_afford(plan, "Amsterdam weekend", 800)
print(f"\n  Affordable: {afford2['affordable']}")
print(f"  Impact: {afford2.get('impact', 'N/A')}")
print(f"  Message: {afford2['message']}")

print("\n" + "=" * 60)
print("VALIDATION")
print("=" * 60)

debt_pots = [p for p in plan["pots"] if p["name"] == "Pay off student overdraft"]
print(f"\n  Overdraft detected as debt: {'YES' if debt_pots and debt_pots[0]['monthly_amount'] > 0 else 'NO - CHECK'}")

emergency = next((p for p in plan["pots"] if p["type"] == "emergency"), None)
print(f"  Emergency fund: £{emergency['monthly_amount']:.2f}/mo (target £{emergency['target']:.0f})")

laptop = next((p for p in plan["pots"] if p["name"] == "New laptop"), None)
print(f"  Laptop allocation: £{laptop['monthly_amount']:.2f}/mo")

deadline_alerts = [a for a in plan["alerts"] if a["type"] == "deadline_risk"]
print(f"  Deadline risk alerts: {len(deadline_alerts)}")
for a in deadline_alerts:
    print(f"    {a['message']}")

goals_paused = [p for p in plan["pots"] if p["type"] not in ("lifestyle", "buffer", "emergency", "debt")
                and p["monthly_amount"] == 0 and not p.get("completed")]
if goals_paused:
    print(f"  Goals paused (expected during debt): {', '.join(p['name'] for p in goals_paused)}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)