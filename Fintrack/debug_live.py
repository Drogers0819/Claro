# Save as debug_live.py
from app import create_app, db
from app.models.user import User
from app.models.goal import Goal
from app.services.planner_service import generate_financial_plan

app = create_app()
with app.app_context():
    user = User.query.first()
    goals = [g.to_dict() for g in Goal.query.filter_by(user_id=user.id, status="active").all()]
    
    print("Profile:", user.profile_dict())
    print("\nGoals:")
    for g in goals:
        print(f"  {g['name']}: target={g['target_amount']}, current={g['current_amount']}, deadline={g.get('deadline')}")
    
    plan = generate_financial_plan(user.profile_dict(), goals)
    print("\nAllocations:")
    for p in plan["pots"]:
        print(f"  {p['name']:25s} £{p['monthly_amount']:>7.2f}/mo")