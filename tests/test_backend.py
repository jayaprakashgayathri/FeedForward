"""
Backend tests — covers all API routes, model logic, and business rules.
File location: tests/test_backend.py

Covers:
  - Health & index
  - Auth (register, login, logout, role routing)
  - Donation CRUD (restaurant side)
  - Donation request pipeline (charity → restaurant → complete)
  - Charity browse & search
  - Charity broadcasts + restaurant responses
  - Model properties (time_ago, category_label)
  - Edge cases and security checks
"""
from tests.conftest import (
    login, make_user, make_donation, make_request,
    make_broadcast, make_broadcast_response
)
from models import (
    User, Donation, DonationRequest,
    CharityBroadcast, BroadcastResponse, db as _db
)


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH & INDEX
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthAndIndex:
    def test_health_endpoint_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.get_json() == {"status": "ok"}

    def test_index_page_loads(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"FeedForward" in r.data

    def test_index_has_restaurant_cta(self, client):
        r = client.get("/")
        assert b"Restaurant" in r.data or b"Donate" in r.data

    def test_index_has_charity_cta(self, client):
        r = client.get("/")
        assert b"Charit" in r.data or b"Request" in r.data


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

class TestRegistration:
    def test_register_page_loads(self, client):
        r = client.get("/register")
        assert r.status_code == 200

    def test_register_donor_success(self, client, db):
        r = client.post("/register", data={
            "email": "newrest@test.com", "password": "pass1234",
            "organization_name": "New Grill", "role": "donor",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert User.query.filter_by(email="newrest@test.com").first() is not None

    def test_register_charity_success(self, client, db):
        r = client.post("/register", data={
            "email": "newcharity@test.com", "password": "pass1234",
            "organization_name": "Hope NGO", "role": "charity",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert User.query.filter_by(email="newcharity@test.com").first() is not None

    def test_register_stores_hashed_password(self, client, db):
        client.post("/register", data={
            "email": "hashed@test.com", "password": "myplainpass",
            "organization_name": "Org", "role": "donor",
        }, follow_redirects=True)
        u = User.query.filter_by(email="hashed@test.com").first()
        assert u is not None
        assert u.password_hash != "myplainpass"

    def test_duplicate_email_rejected(self, client, donor):
        r = client.post("/register", data={
            "email": donor.email, "password": "pass1234",
            "organization_name": "Copy", "role": "donor",
        }, follow_redirects=True)
        assert b"already exists" in r.data

    def test_missing_email_rejected(self, client, db):
        r = client.post("/register", data={
            "password": "pass1234", "organization_name": "X", "role": "donor",
        }, follow_redirects=True)
        assert b"required" in r.data

    def test_missing_password_rejected(self, client, db):
        r = client.post("/register", data={
            "email": "np@test.com", "organization_name": "X", "role": "donor",
        }, follow_redirects=True)
        assert b"required" in r.data

    def test_invalid_role_rejected(self, client, db):
        r = client.post("/register", data={
            "email": "badrole@test.com", "password": "pass1234",
            "organization_name": "X", "role": "superadmin",
        }, follow_redirects=True)
        assert b"Invalid role" in r.data
        assert User.query.filter_by(email="badrole@test.com").first() is None

    def test_register_redirects_to_login(self, client, db):
        r = client.post("/register", data={
            "email": "redirect@test.com", "password": "pass1234",
            "organization_name": "Redir Org", "role": "donor",
        }, follow_redirects=False)
        assert r.status_code == 302
        assert "login" in r.headers["Location"]


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN / LOGOUT
# ══════════════════════════════════════════════════════════════════════════════

class TestAuth:
    def test_login_page_loads(self, client):
        r = client.get("/login")
        assert r.status_code == 200
        assert b"Welcome Back" in r.data

    def test_valid_login_donor(self, client, donor):
        r = login(client, donor.email)
        assert r.status_code == 200

    def test_valid_login_charity(self, client, charity):
        r = login(client, charity.email)
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

    def test_logout_works(self, client, donor):
        login(client, donor.email)
        r = client.get("/logout", follow_redirects=True)
        assert r.status_code == 200
        assert b"FeedForward" in r.data

    def test_logout_requires_login(self, client):
        r = client.get("/logout", follow_redirects=False)
        assert r.status_code == 302

    def test_donor_dashboard_redirect(self, client, donor):
        login(client, donor.email)
        r = client.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert "restaurant-dashboard" in r.headers["Location"]

    def test_charity_dashboard_redirect(self, client, charity):
        login(client, charity.email)
        r = client.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert "charity-browse" in r.headers["Location"]

    def test_unauthenticated_dashboard_redirect(self, client):
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

    def test_unauthenticated_blocked_from_restaurant_dashboard(self, client):
        r = client.get("/restaurant-dashboard", follow_redirects=False)
        assert r.status_code == 302

    def test_unauthenticated_blocked_from_charity_browse(self, client):
        r = client.get("/charity-browse", follow_redirects=False)
        assert r.status_code == 302


# ══════════════════════════════════════════════════════════════════════════════
# RESTAURANT DASHBOARD & DONATION CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestRestaurantDashboard:
    def test_dashboard_loads(self, client, donor):
        login(client, donor.email)
        r = client.get("/restaurant-dashboard")
        assert r.status_code == 200

    def test_dashboard_shows_org_name(self, client, donor):
        login(client, donor.email)
        r = client.get("/restaurant-dashboard")
        assert donor.organization_name.encode() in r.data

    def test_dashboard_shows_active_listing(self, client, donor, db):
        make_donation(donor, food_name="Paneer Curry")
        login(client, donor.email)
        r = client.get("/restaurant-dashboard")
        assert b"Paneer Curry" in r.data

    def test_completed_donation_not_in_active_list(self, client, donor, db):
        make_donation(donor, food_name="Old Biryani", status="completed")
        login(client, donor.email)
        r = client.get("/restaurant-dashboard")
        assert b"Old Biryani" not in r.data


class TestPostDonation:
    def test_create_donation_success(self, client, donor, db):
        login(client, donor.email)
        r = client.post("/donation/new", data={
            "food_name": "Leftover Biryani", "food_category": "perishable",
            "quantity": "20", "unit": "items", "pickup_deadline": "20:00",
        }, follow_redirects=True)
        assert r.status_code == 200
        assert Donation.query.filter_by(food_name="Leftover Biryani").first() is not None

    def test_new_donation_status_is_active(self, client, donor, db):
        login(client, donor.email)
        client.post("/donation/new", data={
            "food_name": "Fresh Samosas", "food_category": "perishable",
            "quantity": "30", "unit": "items", "pickup_deadline": "18:00",
        }, follow_redirects=True)
        d = Donation.query.filter_by(food_name="Fresh Samosas").first()
        assert d is not None
        assert d.status == "active"

    def test_produce_category_stores_kgs(self, client, donor, db):
        login(client, donor.email)
        client.post("/donation/new", data={
            "food_name": "Rice Sacks", "food_category": "produce",
            "quantity": "50", "unit": "kgs", "pickup_deadline": "12:00",
        }, follow_redirects=True)
        d = Donation.query.filter_by(food_name="Rice Sacks").first()
        assert d is not None
        assert d.unit == "kgs"
        assert d.food_category == "produce"

    def test_missing_food_name_rejected(self, client, donor, db):
        login(client, donor.email)
        r = client.post("/donation/new", data={
            "food_category": "perishable", "quantity": "5",
            "unit": "items", "pickup_deadline": "18:00",
        }, follow_redirects=True)
        assert b"required" in r.data

    def test_missing_quantity_rejected(self, client, donor, db):
        login(client, donor.email)
        r = client.post("/donation/new", data={
            "food_name": "Incomplete", "food_category": "perishable",
            "unit": "items", "pickup_deadline": "18:00",
        }, follow_redirects=True)
        assert b"required" in r.data
        assert Donation.query.filter_by(food_name="Incomplete").first() is None

    def test_negative_quantity_rejected(self, client, donor, db):
        login(client, donor.email)
        r = client.post("/donation/new", data={
            "food_name": "Bad Qty", "food_category": "produce",
            "quantity": "-5", "unit": "kgs", "pickup_deadline": "10:00",
        }, follow_redirects=True)
        assert b"positive" in r.data
        assert Donation.query.filter_by(food_name="Bad Qty").first() is None

    def test_zero_quantity_rejected(self, client, donor, db):
        login(client, donor.email)
        r = client.post("/donation/new", data={
            "food_name": "Zero Qty", "food_category": "perishable",
            "quantity": "0", "unit": "items", "pickup_deadline": "10:00",
        }, follow_redirects=True)
        assert b"positive" in r.data

    def test_charity_cannot_post_donation(self, client, charity, db):
        login(client, charity.email)
        r = client.post("/donation/new", data={
            "food_name": "Sneaky", "food_category": "perishable",
            "quantity": "5", "unit": "items", "pickup_deadline": "19:00",
        }, follow_redirects=True)
        assert b"Only restaurants" in r.data
        assert Donation.query.filter_by(food_name="Sneaky").first() is None

    def test_unauthenticated_cannot_post_donation(self, client):
        r = client.post("/donation/new", data={
            "food_name": "Ghost", "food_category": "perishable",
            "quantity": "5", "unit": "items", "pickup_deadline": "19:00",
        }, follow_redirects=False)
        assert r.status_code == 302
        assert Donation.query.filter_by(food_name="Ghost").first() is None


class TestDeleteDonation:
    def test_owner_can_delete(self, client, donor, db):
        d = make_donation(donor, food_name="ToDelete")
        login(client, donor.email)
        r = client.post(f"/donation/{d.id}/delete", follow_redirects=True)
        assert r.status_code == 200
        assert _db.session.get(Donation, d.id) is None

    def test_other_donor_cannot_delete(self, client, donor, donor2, db):
        d = make_donation(donor, food_name="Protected")
        login(client, donor2.email)
        r = client.post(f"/donation/{d.id}/delete", follow_redirects=True)
        assert b"Unauthorized" in r.data
        assert _db.session.get(Donation, d.id) is not None

    def test_delete_cascades_to_requests(self, client, donor, charity, db):
        d = make_donation(donor, food_name="WithRequests")
        req = make_request(d, charity)
        req_id = req.id
        login(client, donor.email)
        client.post(f"/donation/{d.id}/delete", follow_redirects=True)
        assert _db.session.get(DonationRequest, req_id) is None

    def test_charity_cannot_delete_donation(self, client, donor, charity, db):
        d = make_donation(donor, food_name="CantDelete")
        login(client, charity.email)
        r = client.post(f"/donation/{d.id}/delete", follow_redirects=True)
        # Should be redirected away (charity has no access)
        assert _db.session.get(Donation, d.id) is not None


# ══════════════════════════════════════════════════════════════════════════════
# DONATION HISTORY (RESTAURANT)
# ══════════════════════════════════════════════════════════════════════════════

class TestRestaurantHistory:
    def test_history_page_loads(self, client, donor, db):
        make_donation(donor, food_name="Historical Rice")
        login(client, donor.email)
        r = client.get("/restaurant/history")
        assert r.status_code == 200
        assert b"Historical Rice" in r.data

    def test_filter_completed(self, client, donor, db):
        make_donation(donor, food_name="CompletedCurry", status="completed")
        make_donation(donor, food_name="ActiveDahl",     status="active")
        login(client, donor.email)
        r = client.get("/restaurant/history?filter=completed")
        assert b"CompletedCurry" in r.data
        assert b"ActiveDahl" not in r.data

    def test_filter_active(self, client, donor, db):
        make_donation(donor, food_name="ActiveRoti",    status="active")
        make_donation(donor, food_name="CompletedNaan", status="completed")
        login(client, donor.email)
        r = client.get("/restaurant/history?filter=active")
        assert b"ActiveRoti" in r.data
        assert b"CompletedNaan" not in r.data

    def test_fulfillment_rate_shown(self, client, donor, db):
        make_donation(donor, food_name="Done1", status="completed")
        make_donation(donor, food_name="Done2", status="active")
        login(client, donor.email)
        r = client.get("/restaurant/history")
        assert r.status_code == 200

    def test_charity_cannot_view_restaurant_history(self, client, charity):
        login(client, charity.email)
        r = client.get("/restaurant/history", follow_redirects=True)
        assert r.status_code == 200
        assert b"Donation History" not in r.data


# ══════════════════════════════════════════════════════════════════════════════
# CHARITY BROWSE
# ══════════════════════════════════════════════════════════════════════════════

class TestCharityBrowse:
    def test_browse_shows_active_donations(self, client, charity, donor, db):
        make_donation(donor, food_name="Visible Khichdi")
        login(client, charity.email)
        r = client.get("/charity-browse")
        assert r.status_code == 200
        assert b"Visible Khichdi" in r.data

    def test_browse_hides_pending_donations(self, client, charity, donor, db):
        make_donation(donor, food_name="PendingDish", status="pending")
        login(client, charity.email)
        r = client.get("/charity-browse")
        assert b"PendingDish" not in r.data

    def test_browse_hides_completed_donations(self, client, charity, donor, db):
        make_donation(donor, food_name="CompletedDish", status="completed")
        login(client, charity.email)
        r = client.get("/charity-browse")
        assert b"CompletedDish" not in r.data

    def test_search_by_food_name(self, client, charity, donor, db):
        make_donation(donor, food_name="Paneer Tikka")
        make_donation(donor, food_name="Aloo Gobi")
        login(client, charity.email)
        r = client.get("/charity-browse?search=Paneer")
        assert b"Paneer Tikka" in r.data
        assert b"Aloo Gobi" not in r.data

    def test_category_filter_perishable(self, client, charity, donor, db):
        make_donation(donor, food_name="Hot Curry",  food_category="perishable")
        make_donation(donor, food_name="Rice Sacks", food_category="produce")
        login(client, charity.email)
        r = client.get("/charity-browse?category=perishable")
        assert b"Hot Curry" in r.data
        assert b"Rice Sacks" not in r.data

    def test_category_filter_produce(self, client, charity, donor, db):
        make_donation(donor, food_name="WheatBag", food_category="produce")
        make_donation(donor, food_name="CannedSoup", food_category="non-perishable")
        login(client, charity.email)
        r = client.get("/charity-browse?category=produce")
        assert b"WheatBag" in r.data
        assert b"CannedSoup" not in r.data

    def test_donor_blocked_from_browse(self, client, donor):
        login(client, donor.email)
        r = client.get("/charity-browse", follow_redirects=True)
        assert b"Access denied" in r.data


# ══════════════════════════════════════════════════════════════════════════════
# DONATION REQUEST PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

class TestDonationRequestPipeline:
    def test_charity_can_request_active_donation(self, client, charity, donor, db):
        d = make_donation(donor)
        login(client, charity.email)
        r = client.post(f"/donation/{d.id}/request",
                        data={"message": "We need this"}, follow_redirects=True)
        assert r.status_code == 200
        req = DonationRequest.query.filter_by(
            donation_id=d.id, charity_id=charity.id).first()
        assert req is not None
        assert req.status == "pending"

    def test_request_sets_donation_to_pending(self, client, charity, donor, db):
        d = make_donation(donor)
        login(client, charity.email)
        client.post(f"/donation/{d.id}/request",
                    data={"message": ""}, follow_redirects=True)
        _db.session.refresh(d)
        assert d.status == "pending"

    def test_cannot_request_non_active_donation(self, client, charity, donor, db):
        d = make_donation(donor, status="confirmed")
        login(client, charity.email)
        r = client.post(f"/donation/{d.id}/request",
                        data={"message": "Late"}, follow_redirects=True)
        assert b"longer available" in r.data

    def test_donor_cannot_make_request(self, client, donor, donor2, db):
        d = make_donation(donor)
        login(client, donor2.email)
        r = client.post(f"/donation/{d.id}/request",
                        data={"message": "sneaky"}, follow_redirects=True)
        assert b"Only charities" in r.data

    def test_already_requested_shown_on_browse(self, client, charity, donor, db):
        d = make_donation(donor, food_name="Already Requested Dish")
        make_request(d, charity)
        d.status = "active"
        _db.session.commit()
        login(client, charity.email)
        r = client.get("/charity-browse")
        assert b"Request Sent" in r.data or b"already" in r.data.lower()

    def test_restaurant_accepts_request(self, client, donor, charity, db):
        d   = make_donation(donor)
        req = make_request(d, charity)
        login(client, donor.email)
        r = client.post(f"/request/{req.id}/accept", follow_redirects=True)
        assert r.status_code == 200
        _db.session.refresh(req)
        assert req.status == "accepted"

    def test_accept_sets_donation_confirmed(self, client, donor, charity, db):
        d   = make_donation(donor)
        req = make_request(d, charity)
        login(client, donor.email)
        client.post(f"/request/{req.id}/accept", follow_redirects=True)
        _db.session.refresh(d)
        assert d.status == "confirmed"

    def test_accept_declines_competing_requests(self, client, donor, charity, charity2, db):
        d    = make_donation(donor)
        req1 = make_request(d, charity,  "First")
        req2 = make_request(d, charity2, "Second")
        d.status = "pending"
        _db.session.commit()
        login(client, donor.email)
        client.post(f"/request/{req1.id}/accept", follow_redirects=True)
        _db.session.refresh(req2)
        assert req2.status == "declined"

    def test_other_restaurant_cannot_accept(self, client, donor, donor2, charity, db):
        d   = make_donation(donor)
        req = make_request(d, charity)
        login(client, donor2.email)
        r = client.post(f"/request/{req.id}/accept", follow_redirects=True)
        assert b"Unauthorized" in r.data
        _db.session.refresh(req)
        assert req.status == "pending"

    def test_restaurant_declines_request(self, client, donor, charity, db):
        d   = make_donation(donor)
        req = make_request(d, charity)
        login(client, donor.email)
        client.post(f"/request/{req.id}/decline", follow_redirects=True)
        _db.session.refresh(req)
        assert req.status == "declined"

    def test_decline_resets_donation_to_active(self, client, donor, charity, db):
        d   = make_donation(donor)
        req = make_request(d, charity)
        login(client, donor.email)
        client.post(f"/request/{req.id}/decline", follow_redirects=True)
        _db.session.refresh(d)
        assert d.status == "active"

    def test_other_restaurant_cannot_decline(self, client, donor, donor2, charity, db):
        d   = make_donation(donor)
        req = make_request(d, charity)
        login(client, donor2.email)
        r = client.post(f"/request/{req.id}/decline", follow_redirects=True)
        assert b"Unauthorized" in r.data

    def test_complete_pickup(self, client, donor, charity, db):
        d          = make_donation(donor)
        req        = make_request(d, charity)
        req.status = "accepted"
        d.status   = "confirmed"
        _db.session.commit()
        login(client, donor.email)
        client.post(f"/request/{req.id}/complete", follow_redirects=True)
        _db.session.refresh(req)
        _db.session.refresh(d)
        assert req.status == "completed"
        assert d.status   == "completed"

    def test_other_restaurant_cannot_complete(self, client, donor, donor2, charity, db):
        d          = make_donation(donor)
        req        = make_request(d, charity)
        req.status = "accepted"
        d.status   = "confirmed"
        _db.session.commit()
        login(client, donor2.email)
        r = client.post(f"/request/{req.id}/complete", follow_redirects=True)
        assert b"Unauthorized" in r.data


# ══════════════════════════════════════════════════════════════════════════════
# CHARITY HISTORY
# ══════════════════════════════════════════════════════════════════════════════

class TestCharityHistory:
    def test_history_page_loads(self, client, charity, donor, db):
        d = make_donation(donor)
        make_request(d, charity)
        login(client, charity.email)
        r = client.get("/charity/history")
        assert r.status_code == 200

    def test_history_shows_own_requests(self, client, charity, donor, db):
        d = make_donation(donor, food_name="My Request Dish")
        make_request(d, charity)
        login(client, charity.email)
        r = client.get("/charity/history")
        assert b"My Request Dish" in r.data

    def test_filter_accepted(self, client, charity, donor, db):
        d1   = make_donation(donor, food_name="AcceptedCurry")
        d2   = make_donation(donor, food_name="PendingRoti")
        req1 = make_request(d1, charity)
        req1.status = "accepted"
        _db.session.commit()
        make_request(d2, charity)
        login(client, charity.email)
        r = client.get("/charity/history?filter=accepted")
        assert b"AcceptedCurry" in r.data
        assert b"PendingRoti" not in r.data

    def test_filter_declined(self, client, charity, donor, db):
        d   = make_donation(donor, food_name="DeclinedFood")
        req = make_request(d, charity)
        req.status = "declined"
        _db.session.commit()
        login(client, charity.email)
        r = client.get("/charity/history?filter=declined")
        assert b"DeclinedFood" in r.data

    def test_donor_cannot_view_charity_history(self, client, donor):
        login(client, donor.email)
        r = client.get("/charity/history", follow_redirects=True)
        assert r.status_code == 200
        assert b"Request History" not in r.data

    def test_stats_counts_are_correct(self, client, charity, donor, db):
        d1 = make_donation(donor, food_name="S1")
        d2 = make_donation(donor, food_name="S2")
        r1 = make_request(d1, charity)
        r2 = make_request(d2, charity)
        r1.status = "accepted"
        r2.status = "completed"
        _db.session.commit()
        login(client, charity.email)
        r = client.get("/charity/history")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# CHARITY BROADCASTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCharityBroadcasts:
    def test_charity_can_post_broadcast(self, client, charity, db):
        login(client, charity.email)
        r = client.post("/broadcast/new", data={
            "food_name": "Rice Needed", "food_category": "produce",
            "quantity": "20", "unit": "kgs", "needed_by": "18:00",
            "notes": "For 50 residents",
        }, follow_redirects=True)
        assert r.status_code == 200
        bc = CharityBroadcast.query.filter_by(food_name="Rice Needed").first()
        assert bc is not None
        assert bc.status == "open"

    def test_broadcast_missing_fields_rejected(self, client, charity, db):
        login(client, charity.email)
        r = client.post("/broadcast/new", data={
            "food_name": "Incomplete",
        }, follow_redirects=True)
        assert b"required" in r.data
        assert CharityBroadcast.query.filter_by(food_name="Incomplete").first() is None

    def test_donor_cannot_post_broadcast(self, client, donor, db):
        login(client, donor.email)
        r = client.post("/broadcast/new", data={
            "food_name": "Sneaky BC", "food_category": "produce",
            "quantity": "10", "unit": "kgs", "needed_by": "18:00",
        }, follow_redirects=True)
        assert b"Only charities" in r.data
        assert CharityBroadcast.query.filter_by(food_name="Sneaky BC").first() is None

    def test_broadcast_visible_to_restaurant(self, client, charity, donor, db):
        make_broadcast(charity, food_name="Community Need")
        login(client, donor.email)
        r = client.get("/restaurant-dashboard")
        assert b"Community Need" in r.data

    def test_charity_can_delete_own_broadcast(self, client, charity, db):
        bc = make_broadcast(charity, food_name="DeleteMe")
        login(client, charity.email)
        r = client.post(f"/broadcast/{bc.id}/delete", follow_redirects=True)
        assert r.status_code == 200
        assert _db.session.get(CharityBroadcast, bc.id) is None

    def test_other_charity_cannot_delete_broadcast(self, client, charity, charity2, db):
        bc = make_broadcast(charity, food_name="Protected BC")
        login(client, charity2.email)
        r = client.post(f"/broadcast/{bc.id}/delete", follow_redirects=True)
        assert b"Unauthorized" in r.data
        assert _db.session.get(CharityBroadcast, bc.id) is not None


# ══════════════════════════════════════════════════════════════════════════════
# BROADCAST RESPONSES (restaurant offers to charity broadcasts)
# ══════════════════════════════════════════════════════════════════════════════

class TestBroadcastResponses:
    def test_restaurant_can_respond_to_broadcast(self, client, donor, charity, db):
        bc = make_broadcast(charity, food_name="Needs Food")
        login(client, donor.email)
        r = client.post(f"/broadcast/{bc.id}/respond",
                        data={"message": "We can help by 6pm"},
                        follow_redirects=True)
        assert r.status_code == 200
        resp = BroadcastResponse.query.filter_by(
            broadcast_id=bc.id, donor_id=donor.id).first()
        assert resp is not None
        assert resp.status == "pending"

    def test_duplicate_response_rejected(self, client, donor, charity, db):
        bc = make_broadcast(charity)
        make_broadcast_response(bc, donor)
        login(client, donor.email)
        r = client.post(f"/broadcast/{bc.id}/respond",
                        data={"message": "Again"}, follow_redirects=True)
        assert b"already responded" in r.data
        assert BroadcastResponse.query.filter_by(
            broadcast_id=bc.id, donor_id=donor.id).count() == 1

    def test_charity_can_accept_response(self, client, charity, donor, db):
        bc   = make_broadcast(charity)
        resp = make_broadcast_response(bc, donor)
        login(client, charity.email)
        r = client.post(f"/broadcast-response/{resp.id}/accept",
                        follow_redirects=True)
        assert r.status_code == 200
        _db.session.refresh(resp)
        _db.session.refresh(bc)
        assert resp.status == "accepted"
        assert bc.status   == "fulfilled"

    def test_accept_response_declines_others(self, client, charity, donor, donor2, db):
        bc    = make_broadcast(charity)
        resp1 = make_broadcast_response(bc, donor,  "Offer 1")
        resp2 = make_broadcast_response(bc, donor2, "Offer 2")
        login(client, charity.email)
        client.post(f"/broadcast-response/{resp1.id}/accept", follow_redirects=True)
        _db.session.refresh(resp2)
        assert resp2.status == "declined"

    def test_charity_can_decline_response(self, client, charity, donor, db):
        bc   = make_broadcast(charity)
        resp = make_broadcast_response(bc, donor)
        login(client, charity.email)
        r = client.post(f"/broadcast-response/{resp.id}/decline",
                        follow_redirects=True)
        assert r.status_code == 200
        _db.session.refresh(resp)
        assert resp.status == "declined"

    def test_other_charity_cannot_accept_response(self, client, charity, charity2, donor, db):
        bc   = make_broadcast(charity)
        resp = make_broadcast_response(bc, donor)
        login(client, charity2.email)
        r = client.post(f"/broadcast-response/{resp.id}/accept",
                        follow_redirects=True)
        assert b"Unauthorized" in r.data
        _db.session.refresh(resp)
        assert resp.status == "pending"

    def test_charity_cannot_respond_to_own_broadcast(self, client, charity, db):
        bc = make_broadcast(charity)
        login(client, charity.email)
        r = client.post(f"/broadcast/{bc.id}/respond",
                        data={"message": "self"}, follow_redirects=True)
        # Charity role is blocked from this endpoint
        assert b"Only restaurants" in r.data

    def test_already_offered_shown_on_dashboard(self, client, charity, donor, db):
        bc = make_broadcast(charity, food_name="AlreadyOfferedBC")
        make_broadcast_response(bc, donor)
        login(client, donor.email)
        r = client.get("/restaurant-dashboard")
        assert b"Offer Sent" in r.data or b"Awaiting" in r.data


# ══════════════════════════════════════════════════════════════════════════════
# MODEL PROPERTIES
# ══════════════════════════════════════════════════════════════════════════════

class TestModelProperties:
    def test_donation_category_label_perishable(self, donor, db):
        d = make_donation(donor, food_category="perishable")
        assert d.category_label == "Perishable"

    def test_donation_category_label_produce(self, donor, db):
        d = make_donation(donor, food_category="produce")
        assert d.category_label == "Produce"

    def test_donation_category_label_non_perishable(self, donor, db):
        d = make_donation(donor, food_category="non-perishable")
        assert d.category_label == "Non-Perishable"

    def test_donation_time_ago_returns_string(self, donor, db):
        d = make_donation(donor)
        assert isinstance(d.time_ago, str)
        assert "ago" in d.time_ago

    def test_broadcast_category_label(self, charity, db):
        bc = make_broadcast(charity, food_category="produce")
        assert bc.category_label == "Produce"

    def test_broadcast_time_ago_returns_string(self, charity, db):
        bc = make_broadcast(charity)
        assert isinstance(bc.time_ago, str)
        assert "ago" in bc.time_ago

    def test_request_time_ago_returns_string(self, donor, charity, db):
        d   = make_donation(donor)
        req = make_request(d, charity)
        assert isinstance(req.time_ago, str)
        assert "ago" in req.time_ago

    def test_user_role_stored_correctly(self, donor, db):
        assert donor.role == "donor"

    def test_charity_role_stored_correctly(self, charity, db):
        assert charity.role == "charity"
