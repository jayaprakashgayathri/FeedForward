"""
Selenium end-to-end tests.

Run locally:
  1. docker compose --profile selenium up -d db web selenium
  2. docker compose --profile selenium run --rm selenium-tests

Or against a locally running app:
  APP_BASE_URL=http://localhost:5000 SELENIUM_HOST=localhost pytest tests/selenium/ -v
"""
import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

BASE_URL      = os.environ.get("APP_BASE_URL",  "http://localhost:5000")
SELENIUM_HOST = os.environ.get("SELENIUM_HOST", "localhost")
SELENIUM_PORT = os.environ.get("SELENIUM_PORT", "4444")

# Unique emails so parallel runs don't clash
import uuid
_uid = uuid.uuid4().hex[:8]
DONOR_EMAIL   = f"selenium_donor_{_uid}@test.com"
CHARITY_EMAIL = f"selenium_charity_{_uid}@test.com"
PASSWORD      = "Selenium123!"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")

    if SELENIUM_HOST != "localhost":
        # Remote Selenium Grid (Docker)
        driver = webdriver.Remote(
            command_executor=f"http://{SELENIUM_HOST}:{SELENIUM_PORT}/wd/hub",
            options=opts,
        )
    else:
        driver = webdriver.Chrome(options=opts)

    driver.implicitly_wait(8)
    yield driver
    driver.quit()


def wait_for(driver, by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def go(driver, path):
    driver.get(BASE_URL + path)


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_user(driver, role, email, org_name):
    go(driver, "/register")
    # Click role box
    role_id = "role-restaurant" if role == "donor" else "role-charity"
    wait_for(driver, By.ID, role_id).click()
    time.sleep(0.4)

    # Fill form
    form_id = "restaurant-reg-form" if role == "donor" else "charity-reg-form"
    form = wait_for(driver, By.ID, form_id)
    form.find_element(By.NAME, "organization_name").send_keys(org_name)
    form.find_element(By.NAME, "email").send_keys(email)
    form.find_element(By.NAME, "password").send_keys(PASSWORD)

    btn_id = "register-restaurant-btn" if role == "donor" else "register-charity-btn"
    driver.find_element(By.ID, btn_id).click()
    time.sleep(1)


def do_login(driver, email):
    go(driver, "/login")
    wait_for(driver, By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.ID, "login-btn").click()
    time.sleep(1)


def do_logout(driver):
    go(driver, "/logout")
    time.sleep(0.5)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestIndexPage:
    def test_homepage_loads(self, driver):
        go(driver, "/")
        assert "FeedForward" in driver.title

    def test_homepage_has_cta_cards(self, driver):
        go(driver, "/")
        assert "For Restaurants" in driver.page_source
        assert "For Charities"   in driver.page_source

    def test_stats_bar_present(self, driver):
        go(driver, "/")
        assert "500+" in driver.page_source or "Meals Saved" in driver.page_source


class TestRegistration:
    def test_register_page_loads(self, driver):
        go(driver, "/register")
        assert "Get Started" in driver.page_source or "Join" in driver.page_source

    def test_role_selection_shows_forms(self, driver):
        go(driver, "/register")
        # Click restaurant role
        wait_for(driver, By.ID, "role-restaurant").click()
        time.sleep(0.3)
        assert driver.find_element(By.ID, "restaurant-form").is_displayed()

    def test_back_link_resets_role(self, driver):
        go(driver, "/register")
        wait_for(driver, By.ID, "role-charity").click()
        time.sleep(0.3)
        driver.find_element(By.CSS_SELECTOR, "#charity-form .back-link").click()
        time.sleep(0.3)
        assert driver.find_element(By.ID, "role-selection").is_displayed()

    def test_register_donor(self, driver):
        register_user(driver, "donor", DONOR_EMAIL, "Selenium Grill")
        # Should land on login page after registration
        assert "/login" in driver.current_url or "log" in driver.page_source.lower()

    def test_register_charity(self, driver):
        register_user(driver, "charity", CHARITY_EMAIL, "Selenium NGO")
        assert "/login" in driver.current_url or "log" in driver.page_source.lower()


class TestLogin:
    def test_login_page_loads(self, driver):
        go(driver, "/login")
        assert "Welcome Back" in driver.page_source

    def test_login_wrong_password(self, driver):
        go(driver, "/login")
        wait_for(driver, By.ID, "email").send_keys(DONOR_EMAIL)
        driver.find_element(By.ID, "password").send_keys("wrongpass")
        driver.find_element(By.ID, "login-btn").click()
        time.sleep(1)
        assert "Incorrect" in driver.page_source

    def test_donor_login_lands_on_dashboard(self, driver):
        do_login(driver, DONOR_EMAIL)
        assert "restaurant-dashboard" in driver.current_url
        do_logout(driver)

    def test_charity_login_lands_on_browse(self, driver):
        do_login(driver, CHARITY_EMAIL)
        assert "charity-browse" in driver.current_url
        do_logout(driver)


class TestRestaurantDashboard:
    def test_dashboard_loads_after_login(self, driver):
        do_login(driver, DONOR_EMAIL)
        assert "Operations Dashboard" in driver.title or "FeedForward" in driver.title
        do_logout(driver)

    def test_post_donation_form_present(self, driver):
        do_login(driver, DONOR_EMAIL)
        assert "Broadcast Donation" in driver.page_source or "List a New Donation" in driver.page_source
        do_logout(driver)

    def test_post_donation_success(self, driver):
        do_login(driver, DONOR_EMAIL)
        wait_for(driver, By.ID, "donation-form")

        driver.find_element(By.NAME, "food_name").send_keys("Selenium Test Curry")
        # Category already selected by default (perishable)
        driver.find_element(By.NAME, "quantity").send_keys("15")
        driver.find_element(By.NAME, "pickup_deadline").send_keys("20:00")
        driver.find_element(By.ID, "broadcast-btn").click()
        time.sleep(1.5)

        assert "Selenium Test Curry" in driver.page_source
        do_logout(driver)

    def test_active_listings_show_after_post(self, driver):
        do_login(driver, DONOR_EMAIL)
        assert "Selenium Test Curry" in driver.page_source
        do_logout(driver)

    def test_unit_updates_on_category_change(self, driver):
        do_login(driver, DONOR_EMAIL)
        sel = Select(wait_for(driver, By.ID, "foodType"))
        sel.select_by_value("produce")
        time.sleep(0.3)
        unit_label = driver.find_element(By.ID, "unitLabel").text
        assert unit_label == "kgs"
        do_logout(driver)

    def test_charity_blocked_from_dashboard(self, driver):
        do_login(driver, CHARITY_EMAIL)
        go(driver, "/restaurant-dashboard")
        time.sleep(1)
        assert "Access denied" in driver.page_source or "charity-browse" in driver.current_url
        do_logout(driver)


class TestCharityBrowse:
    def test_browse_page_loads(self, driver):
        do_login(driver, CHARITY_EMAIL)
        assert "Find Food" in driver.page_source or "Browse" in driver.title
        do_logout(driver)

    def test_active_donations_visible(self, driver):
        do_login(driver, CHARITY_EMAIL)
        assert "Selenium Test Curry" in driver.page_source
        do_logout(driver)

    def test_search_filters_results(self, driver):
        do_login(driver, CHARITY_EMAIL)
        wait_for(driver, By.ID, "search-input").send_keys("Selenium")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(1)
        assert "Selenium Test Curry" in driver.page_source
        do_logout(driver)

    def test_request_modal_opens(self, driver):
        do_login(driver, CHARITY_EMAIL)
        time.sleep(0.5)
        # Find any Request Donation button
        btns = driver.find_elements(By.CSS_SELECTOR, "[id^='request-btn-']")
        if btns:
            btns[0].click()
            time.sleep(0.4)
            modal = driver.find_element(By.ID, "req-modal")
            assert "open" in modal.get_attribute("class")
        do_logout(driver)

    def test_donor_blocked_from_browse(self, driver):
        do_login(driver, DONOR_EMAIL)
        go(driver, "/charity-browse")
        time.sleep(1)
        assert "Access denied" in driver.page_source or "restaurant-dashboard" in driver.current_url
        do_logout(driver)


class TestHistory:
    def test_restaurant_history_loads(self, driver):
        do_login(driver, DONOR_EMAIL)
        go(driver, "/restaurant/history")
        assert "Donation History" in driver.page_source
        do_logout(driver)

    def test_restaurant_history_shows_donation(self, driver):
        do_login(driver, DONOR_EMAIL)
        go(driver, "/restaurant/history")
        assert "Selenium Test Curry" in driver.page_source
        do_logout(driver)

    def test_charity_history_loads(self, driver):
        do_login(driver, CHARITY_EMAIL)
        go(driver, "/charity/history")
        assert "Request History" in driver.page_source
        do_logout(driver)

    def test_history_filter_links_work(self, driver):
        do_login(driver, DONOR_EMAIL)
        go(driver, "/restaurant/history")
        # Click "Completed" filter
        driver.find_element(By.ID, "filter-completed").click()
        time.sleep(0.5)
        assert "filter=completed" in driver.current_url
        do_logout(driver)


class TestLogout:
    def test_logout_redirects_home(self, driver):
        do_login(driver, DONOR_EMAIL)
        do_logout(driver)
        assert "/" == driver.current_url.replace(BASE_URL, "") or "FeedForward" in driver.title

    def test_protected_route_after_logout(self, driver):
        do_logout(driver)
        go(driver, "/restaurant-dashboard")
        time.sleep(0.5)
        assert "login" in driver.current_url
