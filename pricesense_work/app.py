
import os

from flask import Flask, jsonify, render_template, request
from flask_login import current_user, login_required

from auth import register_auth_routes
from database import Location, db, init_database
from scraper import LOCATIONS, scrape_prices


app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "pricesense-dev-secret-change-me"
)

init_database(app)

register_auth_routes(app)


@app.route("/")
@login_required
def home():

    saved = Location.query.filter_by(
        user_id=current_user.id,
        is_default=True
    ).first()

    return render_template(
        "index.html",
        selected_location=saved.location_key if saved else "bengaluru"
    )


@app.post("/set-location")
@login_required
def set_location():

    payload = request.get_json(silent=True) or {}

    key = payload.get("location", "").strip().lower()

    selected = LOCATIONS.get(key)

    if not selected:
        return jsonify({
            "error": "Invalid location."
        }), 400

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

    return jsonify({
        "success": True,
        "location": selected
    })


@app.route("/search")
@login_required
def search():

    query = request.args.get("q", "").strip()

    saved = Location.query.filter_by(
        user_id=current_user.id,
        is_default=True
    ).first()

    location = saved.location_key if saved else "bengaluru"

    if not query:
        return jsonify({
            "error": "Please enter a product name."
        }), 400

    print("=" * 50)

    print(
        f"SEARCH REQUEST: {query} | "
        f"USER: {current_user.email} | "
        f"LOCATION: {location}"
    )

    print("=" * 50)

    try:

        results = scrape_prices(
            query,
            location=location
        )

        return jsonify(results)

    except Exception as exc:

        print("PriceSense engine error:", exc)

        return jsonify({
            "error": "Unable to collect price data.",
            "details": str(exc)
        }), 500


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=8000,
        debug=True
    )
