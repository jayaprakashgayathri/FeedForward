"""
Shared pytest fixtures — uses in-memory SQLite so tests
run instantly without a running PostgreSQL instance.
"""
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from models import db as _db, User, Donation, DonationRequest


# ── App ───────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    cfg = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret",
        "LOGIN_DISABLED": False,
    }
    application = create_app(cfg)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    """Wrap each test in a savepoint; roll back after."""
    with app.app_context():
        connection  = _db.engine.connect()
        transaction = connection.begin()
        _db.session.bind = connection
        yield _db
        _db.session.remove()
        transaction.rollback()
        connection.close()
        _db.session.bind = None


@pytest.fixture(scope="function")
def client(app):
    with app.test_client() as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(role, email, org, password="pass1234"):
    u = User(
        email=email,
        password_hash=generate_password_hash(password),
        organization_name=org,
        role=role,
        phone="", address="123 Test St", license_num="", reg_num="",
    )
    _db.session.add(u)
    _db.session.commit()
    return u


def make_donation(donor, food_name="Test Food", qty=10, unit="items",
                  category="perishable", deadline="18:00",
                  status="active", notes=""):
    d = Donation(
        donor_id=donor.id, food_name=food_name,
        food_category=category, quantity=qty,
        unit=unit, pickup_deadline=deadline,
        notes=notes, status=status,
    )
    _db.session.add(d)
    _db.session.commit()
    return d


def make_request(donation, charity, message="Need this", status="pending"):
    r = DonationRequest(
        donation_id=donation.id, charity_id=charity.id,
        message=message, status=status,
    )
    _db.session.add(r)
    donation.status = "pending"
    _db.session.commit()
    return r


def login(client, email, password="pass1234"):
    return client.post("/login",
                       data={"email": email, "password": password},
                       follow_redirects=True)


# ── User fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def donor(db):
    return make_user("donor", "restaurant@test.com", "Test Restaurant")


@pytest.fixture
def donor2(db):
    return make_user("donor", "restaurant2@test.com", "Second Restaurant")


@pytest.fixture
def charity(db):
    return make_user("charity", "charity@test.com", "Test Charity NGO")


@pytest.fixture
def charity2(db):
    return make_user("charity", "charity2@test.com", "Second Charity")
