# Save this as debug_plan.py in your Fintrack folder
from app import create_app, db
from app.models.user import User
from app.models.goal import Goal
from app.services.planner_service import generate_financial_plan

app = create_app()
with app.app_context():
    user = User.query.first()
    goals = [g.to_dict() for g in Goal.query.filter_by(user_id=user.id, status="active").all()]
    
    print("=== PROFILE ===")
    print(user.profile_dict())
    
    print("\n=== GOALS ===")
    for g in goals:
        print(f"  {g['name']}: target={g['target_amount']}, current={g['current_amount']}, allocation={g['monthly_allocation']}, deadline={g['deadline']}")
    
    print("\n=== PLAN ===")
    plan = generate_financial_plan(user.profile_dict(), goals)
    
    if plan.get("error"):
        print(f"ERROR: {plan['error']}")
    else:
        print(f"Surplus: £{plan['surplus']}")
        print(f"Phases: {plan['phase_count']}")
        print(f"\nPots:")
        for p in plan["pots"]:
            print(f"  {p['name']}: £{p['monthly_amount']}/mo (target: {p.get('target')}, current: {p.get('current')})")