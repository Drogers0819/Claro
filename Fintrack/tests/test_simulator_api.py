class TestProjectGoalAPI:

    def test_project_single_goal(self, auth_client):
        auth_client.post("/api/profile/factfind", json={
            "monthly_income": 1700,
            "rent_amount": 800,
            "bills_amount": 0
        })

        create = auth_client.post("/api/goals", json={
            "name": "House deposit",
            "type": "savings_target",
            "target_amount": 10000,
            "current_amount": 2400,
            "monthly_allocation": 412,
            "priority_rank": 1
        })
        goal_id = create.get_json()["goal"]["id"]

        response = auth_client.get(f"/api/simulator/project/{goal_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["reachable"] is True
        assert data["goal_name"] == "House deposit"
        assert "completion_date_human" in data
        assert "milestones" in data

    def test_project_nonexistent_goal(self, auth_client):
        response = auth_client.get("/api/simulator/project/9999")
        assert response.status_code == 404

    def test_project_all_goals(self, auth_client):
        auth_client.post("/api/profile/factfind", json={
            "monthly_income": 1700,
            "rent_amount": 800,
            "bills_amount": 0
        })

        auth_client.post("/api/goals", json={
            "name": "Goal 1", "type": "savings_target",
            "target_amount": 5000, "monthly_allocation": 200,
            "priority_rank": 1
        })
        auth_client.post("/api/goals", json={
            "name": "Goal 2", "type": "savings_target",
            "target_amount": 3000, "monthly_allocation": 150,
            "priority_rank": 2
        })

        response = auth_client.get("/api/simulator/project-all")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_goals"] == 2
        assert data["reachable_goals"] == 2

    def test_project_without_auth(self, client):
        response = client.get("/api/simulator/project/1")
        assert response.status_code == 401


class TestHabitCostAPI:

    def test_habit_cost(self, auth_client):
        response = auth_client.post("/api/simulator/habit-cost", json={
            "monthly_spend": 340,
            "description": "Deliveroo"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "horizons" in data
        assert data["horizons"]["10_year"]["simple_cost"] == 40800
        assert data["horizons"]["10_year"]["opportunity_cost"] > 40800
        assert data["description"] == "Deliveroo"

    def test_habit_cost_missing_spend(self, auth_client):
        response = auth_client.post("/api/simulator/habit-cost", json={})
        assert response.status_code == 400

    def test_habit_cost_zero(self, auth_client):
        response = auth_client.post("/api/simulator/habit-cost", json={
            "monthly_spend": 0
        })
        assert response.status_code == 400

    def test_habit_cost_without_auth(self, client):
        response = client.post("/api/simulator/habit-cost", json={
            "monthly_spend": 100
        })
        assert response.status_code == 401


class TestScenarioAPI:

    def test_run_scenario(self, auth_client):
        auth_client.post("/api/profile/factfind", json={
            "monthly_income": 1700,
            "rent_amount": 800,
            "bills_amount": 0
        })

        create = auth_client.post("/api/goals", json={
            "name": "House deposit",
            "type": "savings_target",
            "target_amount": 10000,
            "current_amount": 2400,
            "monthly_allocation": 412,
            "priority_rank": 1
        })
        goal_id = str(create.get_json()["goal"]["id"])

        response = auth_client.post("/api/simulator/scenario", json={
            "spending_changes": {goal_id: 600}
        })
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["comparison"]) == 1
        assert data["comparison"][0]["months_saved"] > 0
        assert data["summary"]["goals_accelerated"] == 1

    def test_scenario_without_factfind(self, auth_client):
        response = auth_client.post("/api/simulator/scenario", json={})
        assert response.status_code == 400

    def test_scenario_without_auth(self, client):
        response = client.post("/api/simulator/scenario", json={})
        assert response.status_code == 401


class TestMultiHorizonAPI:

    def test_multi_horizon(self, auth_client):
        create = auth_client.post("/api/goals", json={
            "name": "Long term", "type": "savings_target",
            "target_amount": 100000, "monthly_allocation": 500,
            "priority_rank": 1
        })
        goal_id = create.get_json()["goal"]["id"]

        response = auth_client.get(f"/api/simulator/multi-horizon/{goal_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "5_year" in data
        assert "10_year" in data
        assert "20_year" in data
        assert data["10_year"]["optimistic"]["final_balance"] > data["10_year"]["conservative"]["final_balance"]

    def test_multi_horizon_not_found(self, auth_client):
        response = auth_client.get("/api/simulator/multi-horizon/9999")
        assert response.status_code == 404
