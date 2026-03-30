import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Donation, DonationRequest, CharityBroadcast, BroadcastResponse

login_manager = LoginManager()

def create_app(config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        if os.environ.get("POSTGRES_HOST"):
            u  = os.environ.get("POSTGRES_USER",     "feedforward")
            pw = os.environ.get("POSTGRES_PASSWORD", "feedforward")
            h  = os.environ.get("POSTGRES_HOST",     "db")
            p  = os.environ.get("POSTGRES_PORT",     "5432")
            d  = os.environ.get("POSTGRES_DB",       "feedforward")
            db_url = f"postgresql://{u}:{pw}@{h}:{p}/{d}"
        else:
            db_url = "sqlite:///feedforward.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    if config:
        app.config.update(config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    _register_routes(app)
    return app

@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))

def _register_routes(app):  # noqa: C901

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email       = request.form.get("email","").strip().lower()
            password    = request.form.get("password","")
            org_name    = request.form.get("organization_name","").strip()
            role        = request.form.get("role","")
            phone       = request.form.get("phone","").strip()
            address     = request.form.get("address","").strip()
            license_num = request.form.get("license_num","").strip()
            reg_num     = request.form.get("reg_num","").strip()

            if not email or not password or not org_name or not role:
                flash("Please fill in all required fields.")
                return redirect(url_for("register"))
            
            # FIXED: Catch invalid roles before checking for existing accounts
            if role not in ("donor", "charity"):
                flash("Invalid role selected.")
                return redirect(url_for("register"))
                
            if User.query.filter_by(email=email).first():
                flash("An account with this email already exists.")
                return redirect(url_for("register"))

            user = User(email=email, password_hash=generate_password_hash(password),
                        organization_name=org_name, role=role, phone=phone,
                        address=address, license_num=license_num, reg_num=reg_num)
            db.session.add(user)
            db.session.commit()
            flash("Account created! Please log in.")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email    = request.form.get("email","").strip().lower()
            password = request.form.get("password","")
            user     = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for("dashboard"))
            flash("Incorrect email or password.")
            return redirect(url_for("login"))
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        if current_user.role == "donor":
            return redirect(url_for("restaurant_dashboard"))
        return redirect(url_for("charity_browse"))

    @app.route("/restaurant-dashboard")
    @login_required
    def restaurant_dashboard():
        if current_user.role != "donor":
            flash("Access denied. Restaurants only.")
            return redirect(url_for("charity_browse"))

        active_donations = (Donation.query
            .filter_by(donor_id=current_user.id)
            .filter(Donation.status.in_(["active","pending"]))
            .order_by(Donation.created_at.desc()).all())

        pending_requests = (DonationRequest.query.join(Donation)
            .filter(Donation.donor_id==current_user.id, DonationRequest.status=="pending")
            .order_by(DonationRequest.created_at.desc()).all())

        confirmed = (DonationRequest.query.join(Donation)
            .filter(Donation.donor_id==current_user.id, DonationRequest.status=="accepted")
            .order_by(DonationRequest.created_at.desc()).limit(5).all())

        community_requests = (CharityBroadcast.query
            .filter_by(status="open")
            .order_by(CharityBroadcast.created_at.desc()).all())

        my_response_ids = {r.broadcast_id for r in
                           BroadcastResponse.query.filter_by(donor_id=current_user.id).all()}

        total_donations = Donation.query.filter_by(donor_id=current_user.id).count()
        completed       = Donation.query.filter_by(donor_id=current_user.id, status="completed").count()

        return render_template("restaurant_dashboard.html",
            active_donations=active_donations,
            pending_requests=pending_requests,
            confirmed=confirmed,
            community_requests=community_requests,
            my_response_ids=my_response_ids,
            total_donations=total_donations,
            completed=completed)

    @app.route("/donation/new", methods=["POST"])
    @login_required
    def new_donation():
        if current_user.role != "donor":
            flash("Only restaurants can post donations.")
            return redirect(url_for("charity_browse"))
        food_name       = request.form.get("food_name","").strip()
        food_category   = request.form.get("food_category","").strip()
        quantity        = request.form.get("quantity","")
        unit            = request.form.get("unit","items")
        pickup_deadline = request.form.get("pickup_deadline","").strip()
        notes           = request.form.get("notes","").strip()
        if not food_name or not food_category or not quantity or not pickup_deadline:
            flash("Please fill in all required donation fields.")
            return redirect(url_for("restaurant_dashboard"))
        try:
            qty = int(quantity)
            if qty <= 0: raise ValueError
        except ValueError:
            flash("Quantity must be a positive number.")
            return redirect(url_for("restaurant_dashboard"))
        d = Donation(donor_id=current_user.id, food_name=food_name,
                     food_category=food_category, quantity=qty, unit=unit,
                     pickup_deadline=pickup_deadline, notes=notes, status="active")
        db.session.add(d)
        db.session.commit()
        flash("Donation listed successfully!")
        return redirect(url_for("restaurant_dashboard"))

    @app.route("/donation/<int:did>/delete", methods=["POST"])
    @login_required
    def delete_donation(did):
        d = db.session.get(Donation, did)
        if not d:
            flash("Donation not found.")
            return redirect(url_for("restaurant_dashboard"))
        if d.donor_id != current_user.id:
            flash("Unauthorized.")
            return redirect(url_for("restaurant_dashboard"))
        DonationRequest.query.filter_by(donation_id=did).delete()
        db.session.delete(d)
        db.session.commit()
        flash("Donation removed.")
        return redirect(url_for("restaurant_dashboard"))

    @app.route("/request/<int:rid>/accept", methods=["POST"])
    @login_required
    def accept_request(rid):
        r = db.session.get(DonationRequest, rid)
        if not r or r.donation.donor_id != current_user.id:
            flash("Unauthorized.")
            return redirect(url_for("restaurant_dashboard"))
        r.status = "accepted"
        r.donation.status = "confirmed"
        for other in DonationRequest.query.filter(
            DonationRequest.donation_id==r.donation_id,
            DonationRequest.id!=rid,
            DonationRequest.status=="pending").all():
            other.status = "declined"
        db.session.commit()
        flash(f"Request from {r.charity.organization_name} accepted!")
        return redirect(url_for("restaurant_dashboard"))

    @app.route("/request/<int:rid>/decline", methods=["POST"])
    @login_required
    def decline_request(rid):
        r = db.session.get(DonationRequest, rid)
        if not r or r.donation.donor_id != current_user.id:
            flash("Unauthorized.")
            return redirect(url_for("restaurant_dashboard"))
        r.status = "declined"
        if not DonationRequest.query.filter_by(donation_id=r.donation_id, status="pending").count():
            r.donation.status = "active"
        db.session.commit()
        flash("Request declined.")
        return redirect(url_for("restaurant_dashboard"))

    @app.route("/request/<int:rid>/complete", methods=["POST"])
    @login_required
    def complete_pickup(rid):
        r = db.session.get(DonationRequest, rid)
        if not r or r.donation.donor_id != current_user.id:
            flash("Unauthorized.")
            return redirect(url_for("restaurant_dashboard"))
        r.status = "completed"
        r.donation.status = "completed"
        db.session.commit()
        flash("Marked as picked up!")
        return redirect(url_for("restaurant_dashboard"))

    @app.route("/broadcast/<int:bid>/respond", methods=["POST"])
    @login_required
    def respond_to_broadcast(bid):
        if current_user.role != "donor":
            flash("Only restaurants can respond to community requests.")
            return redirect(url_for("charity_browse"))
        bc = db.session.get(CharityBroadcast, bid)
        if not bc or bc.status != "open":
            flash("This request is no longer open.")
            return redirect(url_for("restaurant_dashboard"))
        if BroadcastResponse.query.filter_by(broadcast_id=bid, donor_id=current_user.id).first():
            flash("You have already responded to this request.")
            return redirect(url_for("restaurant_dashboard"))
        message = request.form.get("message","").strip()
        resp = BroadcastResponse(broadcast_id=bid, donor_id=current_user.id,
                                  message=message, status="pending")
        db.session.add(resp)
        db.session.commit()
        flash(f"Your offer has been sent to {bc.charity_user.organization_name}!")
        return redirect(url_for("restaurant_dashboard"))

    @app.route("/restaurant/history")
    @login_required
    def restaurant_history():
        if current_user.role != "donor":
            return redirect(url_for("charity_browse"))
        f               = request.args.get("filter","all")
        q               = Donation.query.filter_by(donor_id=current_user.id)
        if f == "completed":
            q = q.filter_by(status="completed")
        elif f == "active":
            q = q.filter(Donation.status.in_(["active","pending","confirmed"]))
        donations       = q.order_by(Donation.created_at.desc()).all()
        total           = Donation.query.filter_by(donor_id=current_user.id).count()
        completed_count = Donation.query.filter_by(donor_id=current_user.id, status="completed").count()
        my_responses = (BroadcastResponse.query
            .filter_by(donor_id=current_user.id)
            .order_by(BroadcastResponse.created_at.desc()).all())
        return render_template("restaurant_history.html",
            donations=donations, filter_status=f,
            total=total, completed_count=completed_count,
            my_responses=my_responses)

    @app.route("/charity-browse")
    @login_required
    def charity_browse():
        if current_user.role != "charity":
            flash("Access denied. Charities only.")
            return redirect(url_for("restaurant_dashboard"))
        search   = request.args.get("search","").strip()
        category = request.args.get("category","all")
        q = Donation.query.filter_by(status="active")
        if search:
            q = q.filter(db.or_(
                Donation.food_name.ilike(f"%{search}%"),
                Donation.notes.ilike(f"%{search}%")))
        if category != "all":
            q = q.filter_by(food_category=category)
        listings = q.order_by(Donation.created_at.desc()).all()
        my_req_ids = {r.donation_id for r in
                      DonationRequest.query.filter_by(charity_id=current_user.id).all()}
        my_broadcasts = (CharityBroadcast.query
            .filter_by(charity_id=current_user.id)
            .order_by(CharityBroadcast.created_at.desc()).all())
        return render_template("charity_browse.html",
            listings=listings, my_req_ids=my_req_ids,
            search=search, category=category,
            my_broadcasts=my_broadcasts)

    @app.route("/donation/<int:did>/request", methods=["POST"])
    @login_required
    def request_donation(did):
        if current_user.role != "charity":
            flash("Only charities can request donations.")
            return redirect(url_for("restaurant_dashboard"))
        
        d = db.session.get(Donation, did)
        if not d or d.status != "active":
            flash("This donation is no longer available.")
            return redirect(url_for("charity_browse"))
        
        # FIXED: Ensure flash message exactly matches test expectation
        if DonationRequest.query.filter_by(donation_id=did, charity_id=current_user.id).first():
            flash("You have already requested this donation.")
            return redirect(url_for("charity_browse"))
        
        r = DonationRequest(donation_id=did, charity_id=current_user.id,
                            message=request.form.get("message","").strip(),
                            status="pending")
        d.status = "pending"
        db.session.add(r)
        db.session.commit()
        flash("Request sent! The restaurant will review it shortly.")
        return redirect(url_for("charity_browse"))

    @app.route("/broadcast/new", methods=["POST"])
    @login_required
    def new_broadcast():
        if current_user.role != "charity":
            flash("Only charities can post food requests.")
            return redirect(url_for("restaurant_dashboard"))
        food_name     = request.form.get("food_name","").strip()
        food_category = request.form.get("food_category","").strip()
        quantity      = request.form.get("quantity","")
        unit          = request.form.get("unit","items")
        needed_by     = request.form.get("needed_by","").strip()
        notes         = request.form.get("notes","").strip()
        if not food_name or not food_category or not quantity or not needed_by:
            flash("Please fill in all required fields for your food request.")
            return redirect(url_for("charity_browse"))
        try:
            qty = int(quantity)
            if qty <= 0: raise ValueError
        except ValueError:
            flash("Quantity must be a positive number.")
            return redirect(url_for("charity_browse"))
        bc = CharityBroadcast(charity_id=current_user.id, food_name=food_name,
                               food_category=food_category, quantity=qty, unit=unit,
                               needed_by=needed_by, notes=notes, status="open")
        db.session.add(bc)
        db.session.commit()
        flash("Your food request has been broadcast to all restaurants!")
        return redirect(url_for("charity_browse"))

    @app.route("/broadcast/<int:bid>/delete", methods=["POST"])
    @login_required
    def delete_broadcast(bid):
        bc = db.session.get(CharityBroadcast, bid)
        if not bc or bc.charity_id != current_user.id:
            flash("Unauthorized.")
            return redirect(url_for("charity_browse"))
        BroadcastResponse.query.filter_by(broadcast_id=bid).delete()
        db.session.delete(bc)
        db.session.commit()
        flash("Food request removed.")
        return redirect(url_for("charity_browse"))

    @app.route("/broadcast-response/<int:resp_id>/accept", methods=["POST"])
    @login_required
    def accept_broadcast_response(resp_id):
        resp = db.session.get(BroadcastResponse, resp_id)
        if not resp or resp.broadcast.charity_id != current_user.id:
            flash("Unauthorized.")
            return redirect(url_for("charity_browse"))
        resp.status = "accepted"
        resp.broadcast.status = "fulfilled"
        for other in BroadcastResponse.query.filter(
            BroadcastResponse.broadcast_id==resp.broadcast_id,
            BroadcastResponse.id!=resp_id,
            BroadcastResponse.status=="pending").all():
            other.status = "declined"
        db.session.commit()
        flash(f"Accepted offer from {resp.restaurant_user.organization_name}!")
        return redirect(url_for("charity_browse"))

    @app.route("/broadcast-response/<int:resp_id>/decline", methods=["POST"])
    @login_required
    def decline_broadcast_response(resp_id):
        resp = db.session.get(BroadcastResponse, resp_id)
        if not resp or resp.broadcast.charity_id != current_user.id:
            flash("Unauthorized.")
            return redirect(url_for("charity_browse"))
        resp.status = "declined"
        db.session.commit()
        flash("Offer declined.")
        return redirect(url_for("charity_browse"))

    @app.route("/charity/history")
    @login_required
    def charity_history():
        if current_user.role != "charity":
            return redirect(url_for("restaurant_dashboard"))
        f    = request.args.get("filter","all")
        q    = DonationRequest.query.filter_by(charity_id=current_user.id)
        if f != "all":
            q = q.filter_by(status=f)
        reqs      = q.order_by(DonationRequest.created_at.desc()).all()
        total     = DonationRequest.query.filter_by(charity_id=current_user.id).count()
        accepted  = DonationRequest.query.filter_by(charity_id=current_user.id, status="accepted").count()
        completed = DonationRequest.query.filter_by(charity_id=current_user.id, status="completed").count()
        my_broadcasts = (CharityBroadcast.query
            .filter_by(charity_id=current_user.id)
            .order_by(CharityBroadcast.created_at.desc()).all())
        return render_template("charity_history.html",
            my_requests=reqs, filter_status=f,
            total=total, accepted=accepted, completed=completed,
            my_broadcasts=my_broadcasts)

if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        db.create_all()
    application.run(host="0.0.0.0",
                    port=int(os.environ.get("PORT",5000)),
                    debug=os.environ.get("FLASK_DEBUG","false").lower()=="true")
