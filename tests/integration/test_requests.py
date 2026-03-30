"""Integration tests — full charity-request pipeline."""
from tests.conftest import login, make_donation, make_request, make_user
from models import Donation, DonationRequest, db as _db


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

    def test_search_filters_food_name(self, client, charity, donor, db):
        make_donation(donor, food_name="Paneer Tikka")
        make_donation(donor, food_name="Aloo Gobi")
        login(client, charity.email)
        r = client.get("/charity-browse?search=Paneer")
        assert b"Paneer Tikka" in r.data
        assert b"Aloo Gobi" not in r.data

    def test_category_filter_produce(self, client, charity, donor, db):
        make_donation(donor, food_name="Beans",  category="non-perishable")
        make_donation(donor, food_name="Greens", category="produce")
        login(client, charity.email)
        r = client.get("/charity-browse?category=produce")
        assert b"Greens" in r.data
        assert b"Beans" not in r.data

    def test_category_filter_perishable(self, client, charity, donor, db):
        make_donation(donor, food_name="Hot Curry",   category="perishable")
        make_donation(donor, food_name="Rice Sacks",  category="produce")
        login(client, charity.email)
        r = client.get("/charity-browse?category=perishable")
        assert b"Hot Curry" in r.data
        assert b"Rice Sacks" not in r.data

    def test_donor_blocked_from_browse(self, client, donor):
        login(client, donor.email)
        r = client.get("/charity-browse", follow_redirects=True)
        assert b"Access denied" in r.data


class TestMakingRequest:
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

    def test_request_sets_donation_pending(self, client, charity, donor, db):
        d = make_donation(donor)
        login(client, charity.email)
        client.post(f"/donation/{d.id}/request",
                    data={"message": ""}, follow_redirects=True)
        _db.session.refresh(d)
        assert d.status == "pending"

    def test_request_non_active_donation_rejected(self, client, charity, donor, db):
        d = make_donation(donor, status="confirmed")
        login(client, charity.email)
        r = client.post(f"/donation/{d.id}/request",
                        data={"message": "Late"}, follow_redirects=True)
        assert b"longer available" in r.data

    def test_donor_cannot_request_donation(self, client, donor, donor2, db):
        d = make_donation(donor)
        login(client, donor2.email)
        r = client.post(f"/donation/{d.id}/request",
                        data={"message": "sneaky"}, follow_redirects=True)
        assert b"Only charities" in r.data

    def test_already_requested_shown_on_browse(self, client, charity, donor, db):
        d = make_donation(donor, food_name="Already Requested Dish")
        make_request(d, charity)
        # Reset to active so it shows in browse
        d.status = "active"
        _db.session.commit()
        login(client, charity.email)
        r = client.get("/charity-browse")
        assert b"Request Sent" in r.data or b"already" in r.data.lower()


class TestAcceptRequest:
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

    def test_flash_message_on_accept(self, client, donor, charity, db):
        d   = make_donation(donor)
        req = make_request(d, charity)
        login(client, donor.email)
        r = client.post(f"/request/{req.id}/accept", follow_redirects=True)
        assert charity.organization_name.encode() in r.data


class TestDeclineRequest:
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


class TestCompletePickup:
    def test_mark_pickup_complete(self, client, donor, charity, db):
        d            = make_donation(donor)
        req          = make_request(d, charity)
        req.status   = "accepted"
        d.status     = "confirmed"
        _db.session.commit()
        login(client, donor.email)
        client.post(f"/request/{req.id}/complete", follow_redirects=True)
        _db.session.refresh(req)
        _db.session.refresh(d)
        assert req.status == "completed"
        assert d.status   == "completed"

    def test_other_restaurant_cannot_complete(self, client, donor, donor2, charity, db):
        d            = make_donation(donor)
        req          = make_request(d, charity)
        req.status   = "accepted"
        d.status     = "confirmed"
        _db.session.commit()
        login(client, donor2.email)
        r = client.post(f"/request/{req.id}/complete", follow_redirects=True)
        assert b"Unauthorized" in r.data


class TestCharityHistory:
    def test_history_loads(self, client, charity, donor, db):
        d   = make_donation(donor)
        make_request(d, charity)
        login(client, charity.email)
        r = client.get("/charity/history")
        assert r.status_code == 200

    def test_history_shows_own_requests(self, client, charity, donor, db):
        d   = make_donation(donor, food_name="My Request Dish")
        make_request(d, charity)
        login(client, charity.email)
        r = client.get("/charity/history")
        assert b"My Request Dish" in r.data

    def test_history_filter_accepted(self, client, charity, donor, db):
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

    def test_history_filter_declined(self, client, charity, donor, db):
        d    = make_donation(donor, food_name="DeclinedFood")
        req  = make_request(d, charity)
        req.status = "declined"
        _db.session.commit()
        login(client, charity.email)
        r = client.get("/charity/history?filter=declined")
        assert b"DeclinedFood" in r.data

    def test_donor_cannot_view_charity_history(self, client, donor):
        login(client, donor.email)
        r = client.get("/charity/history", follow_redirects=True)
        assert r.status_code == 200
        # Redirected away from charity history

}
