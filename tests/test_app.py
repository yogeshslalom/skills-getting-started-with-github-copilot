"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        activity: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for activity, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for activity, details in original_activities.items():
        activities[activity]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # We have 9 activities
        assert "Chess Club" in data
        assert "Programming Class" in data
    
    def test_get_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        # Check structure of one activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for a non-existent activity returns 404"""
        response = client.post(
            "/activities/Fake Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant(self, client):
        """Test that duplicate signup returns 400"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response2.status_code == 400
        
        data = response2.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=coder@mergington.edu"
        )
        assert response.status_code == 200


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""
    
    def test_remove_participant_successful(self, client):
        """Test successful removal of a participant"""
        # First, add a participant
        email = "toremove@mergington.edu"
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Then remove them
        response = client.delete(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "Removed" in data["message"]
        assert email in data["message"]
        
        # Verify participant was removed
        assert email not in activities["Chess Club"]["participants"]
    
    def test_remove_participant_nonexistent_activity(self, client):
        """Test removing participant from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Fake Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_remove_participant_not_signed_up(self, client):
        """Test removing participant who is not signed up returns 404"""
        response = client.delete(
            "/activities/Chess Club/signup?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "not signed up" in data["detail"].lower()
    
    def test_remove_existing_participant(self, client):
        """Test removing an existing participant from initial data"""
        # Michael is already signed up for Chess Club in the initial data
        email = "michael@mergington.edu"
        assert email in activities["Chess Club"]["participants"]
        
        response = client.delete(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response.status_code == 200
        assert email not in activities["Chess Club"]["participants"]


class TestIntegrationScenarios:
    """Integration tests for common user scenarios"""
    
    def test_full_signup_and_removal_workflow(self, client):
        """Test complete workflow of signup and removal"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Check participant was added
        check_response = client.get("/activities")
        new_count = len(check_response.json()[activity]["participants"])
        assert new_count == initial_count + 1
        assert email in check_response.json()[activity]["participants"]
        
        # Remove participant
        remove_response = client.delete(
            f"/activities/{activity}/signup?email={email}"
        )
        assert remove_response.status_code == 200
        
        # Verify removal
        final_response = client.get("/activities")
        final_count = len(final_response.json()[activity]["participants"])
        assert final_count == initial_count
        assert email not in final_response.json()[activity]["participants"]
    
    def test_multiple_activities_signup(self, client):
        """Test signing up for multiple activities"""
        email = "multitask@mergington.edu"
        activities_list = ["Chess Club", "Programming Class", "Science Club"]
        
        for activity in activities_list:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
            assert email in activities[activity]["participants"]
