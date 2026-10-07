from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from database.db import (
    create_user, get_db, get_user_by_email, init_db, seed_db,
    get_user_by_id, get_expenses_for_user, get_stats_for_user, get_category_breakdown,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name",     "").strip()
        email    = request.form.get("email",    "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")

        user_id = create_user(name, email, password)
        if user_id is None:
            return render_template("register.html", error="An account with that email already exists.")

        flash("Account created! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email",    "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("All fields are required.", "danger")
            return render_template("login.html")

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        session["user_id"]   = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    raw_user = get_user_by_id(user_id)

    parts = raw_user["name"].split()
    initials = "".join(p[0].upper() for p in parts if p)[:2]
    member_since = datetime.strptime(raw_user["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")

    user = {
        "name":         raw_user["name"],
        "email":        raw_user["email"],
        "initials":     initials,
        "member_since": member_since,
    }

    raw_stats = get_stats_for_user(user_id)
    stats = {
        "total_spent":       "{:,.2f}".format(raw_stats["total_spent"]),
        "transaction_count": raw_stats["transaction_count"],
        "top_category":      raw_stats["top_category"] or "N/A",
    }

    transactions = [
        {
            "date":          datetime.strptime(row["date"], "%Y-%m-%d").strftime("%-d %b %Y"),
            "description":   row["description"] or "",
            "category":      row["category"],
            "category_slug": row["category"].lower().replace(" ", "-"),
            "amount":        "{:,.2f}".format(row["amount"]),
        }
        for row in get_expenses_for_user(user_id)
    ]

    raw_cats = get_category_breakdown(user_id)
    grand_total = sum(r["total"] for r in raw_cats)
    categories = [
        {
            "name":    row["category"],
            "slug":    row["category"].lower().replace(" ", "-"),
            "amount":  "{:,.2f}".format(row["total"]),
            "percent": int(round(row["total"] / grand_total * 100)) if grand_total > 0 else 0,
        }
        for row in raw_cats
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
