"""Integration tests — auth flows and role-based routing."""
from tests.conftest import login, make_user
from models import User


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.get_json()["status"] == "ok"


class TestIndexPage:
    def test_index_loads(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"FeedForward" in r.data

    def test_index_has_login_link(self, client):
        r = client.get("/")
        assert b"Login" in r.data or b"login" in r.data


class TestRegistration:
    def test_register_page_loads(self, client):
        r = client.get("/register")
        assert r.status_code == 200
        assert b"Get Started" in r.data or b"Register" in r.data

    def test_register_donor_creates_user(self, client, db):
        r = client.post("/register", data={
            "email": "new_donor@test.com", "password": "pass1234",
            "organization_name": "New Grill", "role": "donor",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert User.query.filter_by(email="new_donor@test.com").first() is not None

    def test_register_charity_creates_user(self, client, db):
        r = client.post("/register", data={
            "email": "new_charity@test.com", "password": "pass1234",
            "organization_name": "Hope NGO", "role": "charity",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert User.query.filter_by(email="new_charity@test.com").first() is not None

    def test_duplicate_email_rejected(self, client, donor):
        r = client.post("/register", data={
            "email": donor.email, "password": "pass1234",
            "organization_name": "Another", "role": "donor",
        }, follow_redirects=True)
        assert b"already exists" in r.data

    def test_missing_required_fields_rejected(self, client, db):
        r = client.post("/register", data={"email": "x@x.com"},
                        follow_redirects=True)
        assert b"required" in r.data

    def test_invalid_role_rejected(self, client, db):
        r = client.post("/register", data={
            "email": "bad@test.com", "password": "pass1234",
            "organization_name": "Bad", "role": "superadmin",
        }, follow_redirects=True)
        assert b"Invalid role" in r.data

    def test_password_stored_hashed(self, client, db):
        client.post("/register", data={
            "email": "hashed@test.com", "password": "mypassword",
            "organization_name": "Org", "role": "donor",
        }, follow_redirects=True)
        u = User.query.filter_by(email="hashed@test.com").first()
        assert u is not None
        assert u.password_hash != "mypassword"


class TestLogin:
    def test_login_page_loads(self, client):
        r = client.get("/login")
        assert r.status_code == 200
        assert b"Welcome Back" in r.data

    def test_valid_login_succeeds(self, client, donor):
        r = login(client, donor.email)
        assert r.status_code == 200

    def test_wrong_password_rejected(self, client, donor):
        r = client.post("/login", data={
            "email": donor.email, "password": "wrongpass",
        }, follow_redirects=True)
        assert b"Incorrect" in r.data

    def test_unknown_email_rejected(self, client, db):
        r = client.post("/login", data={
            "email": "nobody@nowhere.com", "password": "pass",
        }, follow_redirects=True)
        assert b"Incorrect" in r.data

    def test_logout_redirects_home(self, client, donor):
        login(client, donor.email)
        r = client.get("/logout", follow_redirects=True)
        assert r.status_code == 200
        assert b"FeedForward" in r.data


class TestRoleRouting:
    def test_donor_redirected_to_restaurant_dashboard(self, client, donor):
        login(client, donor.email)
        r = client.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert "restaurant-dashboard" in r.headers["Location"]

    def test_charity_redirected_to_browse(self, client, charity):
        login(client, charity.email)
        r = client.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert "charity-browse" in r.headers["Location"]

    def test_unauthenticated_redirected_to_login(self, client):
        r = client.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert "login" in r.headers["Location"]

    def test_charity_blocked_from_restaurant_dashboard(self, client, charity):
        login(client, charity.email)
        r = client.get("/restaurant-dashboard", follow_redirects=True)
        assert b"Access denied" in r.data

    def test_donor_blocked_from_charity_browse(self, client, donor):
        login(client, donor.email)
        r = client.get("/charity-browse", follow_redirects=True)
        assert b"Access denied" in r.data

    def test_unauthenticated_blocked_from_dashboard(self, client):
        r = client.get("/restaurant-dashboard", follow_redirects=False)
        assert r.status_code == 302

    def test_unauthenticated_blocked_from_charity_browse(self, client):
        r = client.get("/charity-browse", follow_redirects=False)
        assert r.status_code == 302
