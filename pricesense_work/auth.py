
from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for
)

from flask_login import (
    current_user,
    login_user,
    logout_user
)

from database import db, Location, User
from scraper import LOCATIONS


def register_auth_routes(app):

    @app.route("/register", methods=["GET", "POST"])
    def register():

        if current_user.is_authenticated:
            return redirect(url_for("home"))

        if request.method == "POST":

            name = request.form.get("name", "").strip()

            email = request.form.get("email", "").strip().lower()

            password = request.form.get("password", "")

            confirm = request.form.get("confirm_password", "")

            if not name or not email or not password:
                flash("All fields are required.", "error")
                return render_template("register.html")

            if len(password) < 6:
                flash(
                    "Password must contain at least 6 characters.",
                    "error"
                )
                return render_template("register.html")

            if password != confirm:
                flash("Passwords do not match.", "error")
                return render_template("register.html")

            if User.query.filter_by(email=email).first():
                flash(
                    "An account with this email already exists.",
                    "error"
                )
                return render_template("register.html")

            user = User(
                name=name,
                email=email
            )

            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            login_user(user)

            return redirect(url_for("location"))

        return render_template("register.html")


    @app.route("/login", methods=["GET", "POST"])
    def login():

        if current_user.is_authenticated:
            return redirect(url_for("home"))

        if request.method == "POST":

            email = request.form.get("email", "").strip().lower()

            password = request.form.get("password", "")

            user = User.query.filter_by(
                email=email
            ).first()

            if not user or not user.check_password(password):

                flash("Invalid email or password.", "error")

                return render_template("login.html")

            login_user(user)

            next_page = request.args.get("next")

            if next_page and next_page.startswith("/"):
                return redirect(next_page)

            return redirect(url_for("location"))

        return render_template("login.html")


    @app.route("/logout")
    def logout():

        logout_user()

        return redirect(url_for("login"))


    @app.route("/location", methods=["GET", "POST"])
    def location():

        if not current_user.is_authenticated:
            return redirect(url_for("login"))

        if request.method == "POST":

            key = request.form.get(
                "location",
                ""
            ).strip().lower()

            selected = LOCATIONS.get(key)

            if not selected:

                flash(
                    "Please select a valid location.",
                    "error"
                )

                return render_template(
                    "location.html",
                    locations=LOCATIONS,
                    selected_key=""
                )

            Location.query.filter_by(
                user_id=current_user.id
            ).update({
                "is_default": False
            })

            saved = Location(
                user_id=current_user.id,
                location_key=key,
                city=selected["name"],
                pincode=selected["pincode"],
                latitude=selected["lat"],
                longitude=selected["lng"],
                is_default=True
            )

            db.session.add(saved)

            db.session.commit()

            return redirect(url_for("home"))

        saved = Location.query.filter_by(
            user_id=current_user.id,
            is_default=True
        ).first()

        return render_template(
            "location.html",
            locations=LOCATIONS,
            selected_key=saved.location_key if saved else ""
        )
