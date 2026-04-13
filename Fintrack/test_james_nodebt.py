# Save as test_james_nodebt.py
from app.services.planner_service import generate_financial_plan

profile = {
    "monthly_income": 1950,
    "rent_amount": 650,
    "bills_amount": 180,
    "groceries_estimate": 200,
    "transport_estimate": 120,
}

# Same goals but no debt, emergency already funded
goals = [
    {"id": 3, "name": "Emergency fund", "type": "savings_target",
     "target_amount": 3450, "current_amount": 3450},
    {"id": 2, "name": "Holiday Japan", "type": "savings_target",
     "target_amount": 3500, "current_amount": 400, "deadline": "2027-07-01"},
    {"id": 3, "name": "New laptop", "type": "savings_target",
     "target_amount": 1200, "current_amount": 200, "deadline": "2026-12-01"},
    {"id": 4, "name": "House deposit", "type": "savings_target",
     "target_amount": 25000, "current_amount": 0},
]

plan = generate_financial_plan(profile, goals)
print("Post-debt, post-emergency allocation:")
for p in plan["pots"]:
    if p["monthly_amount"] > 0:
        print(f"  {p['name']:25s} £{p['monthly_amount']:>7.2f}/mo")