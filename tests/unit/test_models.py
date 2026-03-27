"""Unit tests — model properties, defaults, relationships."""
from tests.conftest import make_user, make_donation, make_request
from models import User, Donation, DonationRequest, db as _db
from werkzeug.security import check_password_hash


class TestUserModel:
    def test_fields_stored_correctly(self, donor):
        assert donor.email == "restaurant@test.com"
        assert donor.role  == "donor"
        assert donor.organization_name == "Test Restaurant"

    def test_password_is_hashed(self, donor):
        assert donor.password_hash != "pass1234"
        assert check_password_hash(donor.password_hash, "pass1234")

    def test_donor_has_donations_relationship(self, donor, db):
        d = make_donation(donor)
        assert d in donor.donations

    def test_charity_has_requests_relationship(self, charity, donor, db):
        d = make_donation(donor)
        r = make_request(d, charity)
        assert r in charity.charity_requests

    def test_role_values(self, donor, charity):
        assert donor.role  == "donor"
        assert charity.role == "charity"


class TestDonationModel:
    def test_default_status_active(self, donor, db):
        d = make_donation(donor)
        assert d.status == "active"

    def test_category_label_perishable(self, donor, db):
        d = make_donation(donor, category="perishable")
        assert d.category_label == "Perishable"

    def test_category_label_produce(self, donor, db):
        d = make_donation(donor, category="produce")
        assert d.category_label == "Produce"

    def test_category_label_non_perishable(self, donor, db):
        d = make_donation(donor, category="non-perishable")
        assert d.category_label == "Non-Perishable"

    def test_time_ago_is_string(self, donor, db):
        d = make_donation(donor)
        assert isinstance(d.time_ago, str)
        assert "ago" in d.time_ago

    def test_donor_backref(self, donor, db):
        d = make_donation(donor)
        assert d.donor.id == donor.id

    def test_requests_relationship(self, donor, charity, db):
        d = make_donation(donor)
        r = make_request(d, charity)
        assert r in d.requests

    def test_quantity_is_integer(self, donor, db):
        d = make_donation(donor, qty=25)
        assert d.quantity == 25
        assert isinstance(d.quantity, int)


class TestDonationRequestModel:
    def test_default_status_pending(self, donor, charity, db):
        d = make_donation(donor)
        r = DonationRequest(donation_id=d.id, charity_id=charity.id)
        _db.session.add(r)
        _db.session.commit()
        assert r.status == "pending"

    def test_time_ago_string(self, donor, charity, db):
        d = make_donation(donor)
        r = make_request(d, charity)
        assert "ago" in r.time_ago

    def test_charity_backref(self, donor, charity, db):
        d = make_donation(donor)
        r = make_request(d, charity)
        assert r.charity.id == charity.id

    def test_donation_backref(self, donor, charity, db):
        d = make_donation(donor)
        r = make_request(d, charity)
        assert r.donation.id == d.id
