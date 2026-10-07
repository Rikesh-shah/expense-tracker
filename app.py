from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from database.db import create_user, get_db, get_user_by_email, init_db, seed_db

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

    user = {
        "name":         "Priya Sharma",
        "email":        "priya.sharma@example.com",
        "initials":     "PS",
        "member_since": "January 2024",
    }
    stats = {
        "total_spent":       "12,450",
        "transaction_count": 38,
        "top_category":      "Food",
    }
    transactions = [
        {"date": "2 Oct 2024",  "description": "Swiggy – dinner",    "category": "Food",      "category_slug": "food",      "amount": "640"},
        {"date": "1 Oct 2024",  "description": "Metro card recharge", "category": "Transport", "category_slug": "transport", "amount": "500"},
        {"date": "30 Sep 2024", "description": "Amazon – headphones", "category": "Shopping",  "category_slug": "shopping",  "amount": "2,199"},
        {"date": "29 Sep 2024", "description": "Electricity bill",    "category": "Utilities", "category_slug": "utilities", "amount": "1,120"},
    ]
    categories = [
        {"name": "Food",      "slug": "food",      "amount": "4,800", "percent": 38},
        {"name": "Shopping",  "slug": "shopping",  "amount": "3,600", "percent": 29},
        {"name": "Utilities", "slug": "utilities", "amount": "2,400", "percent": 19},
        {"name": "Transport", "slug": "transport", "amount": "1,650", "percent": 13},
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
