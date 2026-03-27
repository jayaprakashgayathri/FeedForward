"""Integration tests — donation CRUD by restaurants."""
from tests.conftest import login, make_donation, make_request
from models import Donation, DonationRequest


class TestPostDonation:
    def test_create_donation_success(self, client, donor):
        login(client, donor.email)
        r = client.post("/donation/new", data={
            "food_name": "Leftover Biryani", "food_category": "perishable",
            "quantity": "20", "unit": "items", "pickup_deadline": "20:00",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert Donation.query.filter_by(food_name="Leftover Biryani").first() is not None

    def test_donation_default_status_active(self, client, donor):
        login(client, donor.email)
        client.post("/donation/new", data={
            "food_name": "Samosas", "food_category": "perishable",
            "quantity": "30", "unit": "items", "pickup_deadline": "18:00",
        }, follow_redirects=True)
        d = Donation.query.filter_by(food_name="Samosas").first()
        assert d is not None
        assert d.status == "active"

    def test_missing_fields_rejected(self, client, donor):
        login(client, donor.email)
        r = client.post("/donation/new", data={"food_name": "Incomplete"},
                        follow_redirects=True)
        assert b"required" in r.data
        assert Donation.query.filter_by(food_name="Incomplete").first() is None

    def test_negative_quantity_rejected(self, client, donor):
        login(client, donor.email)
        r = client.post("/donation/new", data={
            "food_name": "Bad Qty", "food_category": "produce",
            "quantity": "-5", "unit": "kgs", "pickup_deadline": "10:00",
        }, follow_redirects=True)
        assert b"positive" in r.data
        assert Donation.query.filter_by(food_name="Bad Qty").first() is None

    def test_charity_cannot_post_donation(self, client, charity):
        login(client, charity.email)
        r = client.post("/donation/new", data={
            "food_name": "Sneaky", "food_category": "perishable",
            "quantity": "5", "unit": "items", "pickup_deadline": "19:00",
        }, follow_redirects=True)
        assert b"Only restaurants" in r.data
        assert Donation.query.filter_by(food_name="Sneaky").first() is None

    def test_unauthenticated_cannot_post(self, client, db):
        r = client.post("/donation/new", data={
            "food_name": "Ghost", "food_category": "perishable",
            "quantity": "5", "unit": "items", "pickup_deadline": "19:00",
        }, follow_redirects=True)
        assert Donation.query.filter_by(food_name="Ghost").first() is None

    def test_produce_category_stores_kgs(self, client, donor):
        login(client, donor.email)
        client.post("/donation/new", data={
            "food_name": "Rice Sacks", "food_category": "produce",
            "quantity": "50", "unit": "kgs", "pickup_deadline": "12:00",
        }, follow_redirects=True)
        d = Donation.query.filter_by(food_name="Rice Sacks").first()
        assert d is not None
        assert d.unit == "kgs"


class TestDeleteDonation:
    def test_owner_can_delete(self, client, donor, db):
        d = make_donation(donor, food_name="ToDelete")
        login(client, donor.email)
        r = client.post(f"/donation/{d.id}/delete", follow_redirects=True)
        assert r.status_code == 200
        assert Donation.query.get(d.id) is None

    def test_other_donor_cannot_delete(self, client, donor, donor2, db):
        d = make_donation(donor, food_name="Protected")
        login(client, donor2.email)
        r = client.post(f"/donation/{d.id}/delete", follow_redirects=True)
        assert b"Unauthorized" in r.data
        assert Donation.query.get(d.id) is not None

    def test_delete_cascades_to_requests(self, client, donor, charity, db):
        from models import db as _db
        d = make_donation(donor, food_name="WithRequests")
        req = make_request(d, charity)
        req_id = req.id
        login(client, donor.email)
        client.post(f"/donation/{d.id}/delete", follow_redirects=True)
        assert DonationRequest.query.get(req_id) is None


class TestRestaurantDashboard:
    def test_dashboard_shows_active_listings(self, client, donor, db):
        make_donation(donor, food_name="Visible Soup")
        login(client, donor.email)
        r = client.get("/restaurant-dashboard")
        assert b"Visible Soup" in r.data

    def test_dashboard_shows_org_name(self, client, donor):
        login(client, donor.email)
        r = client.get("/restaurant-dashboard")
        assert donor.organization_name.encode() in r.data

    def test_completed_donations_not_in_active_list(self, client, donor, db):
        make_donation(donor, food_name="Done Dish", status="completed")
        login(client, donor.email)
        r = client.get("/restaurant-dashboard")
        # completed should not be in active listings section
        assert b"Done Dish" not in r.data


class TestRestaurantHistory:
    def test_history_page_loads(self, client, donor, db):
        make_donation(donor, food_name="Historical Rice")
        login(client, donor.email)
        r = client.get("/restaurant/history")
        assert r.status_code == 200
        assert b"Historical Rice" in r.data

    def test_history_shows_completed_count(self, client, donor, db):
        make_donation(donor, food_name="Done1", status="completed")
        make_donation(donor, food_name="Done2", status="completed")
        login(client, donor.email)
        r = client.get("/restaurant/history")
        assert r.status_code == 200

    def test_filter_completed(self, client, donor, db):
        make_donation(donor, food_name="CompletedCurry", status="completed")
        make_donation(donor, food_name="ActiveDahl",     status="active")
        login(client, donor.email)
        r = client.get("/restaurant/history?filter=completed")
        assert b"CompletedCurry" in r.data
        assert b"ActiveDahl" not in r.data

    def test_filter_active(self, client, donor, db):
        make_donation(donor, food_name="ActiveRoti",      status="active")
        make_donation(donor, food_name="CompletedNaan",   status="completed")
        login(client, donor.email)
        r = client.get("/restaurant/history?filter=active")
        assert b"ActiveRoti" in r.data
        assert b"CompletedNaan" not in r.data

    def test_charity_cannot_view_restaurant_history(self, client, charity):
        login(client, charity.email)
        r = client.get("/restaurant/history", follow_redirects=True)
        assert r.status_code == 200
        # Should be redirected to charity browse, not restaurant history
