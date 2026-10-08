from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from database.db import (
    create_user, get_db, get_user_by_email, init_db, seed_db,
    get_user_by_id, get_expenses_for_user, get_stats_for_user, get_category_breakdown,
    insert_expense,
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


def _build_filter_label(date_from, date_to):
    fmt = lambda d: datetime.strptime(d, '%Y-%m-%d').strftime('%-d %b %Y')
    if date_from and date_to:
        return 'Showing results from {} to {}'.format(fmt(date_from), fmt(date_to))
    if date_from:
        return 'Showing results from {} onwards'.format(fmt(date_from))
    if date_to:
        return 'Showing results up to {}'.format(fmt(date_to))
    return None


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    date_from = date_to = None
    raw_from = request.args.get('date_from', '').strip()
    raw_to = request.args.get('date_to', '').strip()
    if raw_from:
        try:
            datetime.strptime(raw_from, '%Y-%m-%d')
            date_from = raw_from
        except ValueError:
            pass
    if raw_to:
        try:
            datetime.strptime(raw_to, '%Y-%m-%d')
            date_to = raw_to
        except ValueError:
            pass

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
        for row in get_expenses_for_user(user_id, date_from=date_from, date_to=date_to)
    ]

    filter_label = _build_filter_label(date_from, date_to)

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
        date_from=date_from or '',
        date_to=date_to or '',
        filter_label=filter_label,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


# Single source of truth for valid expense categories.
# The insert route validates against this list before writing to the DB.
CATEGORIES = ['Food', 'Transport', 'Bills', 'Health', 'Entertainment', 'Shopping', 'Other']


def _validate_expense_form(raw_amount, raw_category, raw_date, raw_description):
    """Return (error_string_or_None, parsed_amount_or_None)."""
    try:
        amount = float(raw_amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return "Amount must be a number greater than 0.", None

    if raw_category not in CATEGORIES:
        return "Please select a valid category.", None

    try:
        datetime.strptime(raw_date, "%Y-%m-%d")
    except ValueError:
        return "Please enter a valid date.", None

    if len(raw_description) > 200:
        return "Description must be 200 characters or fewer.", None

    return None, amount


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        raw_amount      = request.form.get("amount", "").strip()
        raw_category    = request.form.get("category", "").strip()
        raw_date        = request.form.get("date", "").strip()
        raw_description = request.form.get("description", "").strip()

        error, amount = _validate_expense_form(raw_amount, raw_category, raw_date, raw_description)
        if error:
            return render_template(
                "add_expense.html",
                error=error,
                categories=CATEGORIES,
                form={"amount": raw_amount, "category": raw_category,
                      "date": raw_date, "description": raw_description},
            )

        insert_expense(session["user_id"], amount, raw_category, raw_date, raw_description or None)
        flash("Expense added.", "success")
        return redirect(url_for("profile"))

    today = datetime.today().strftime("%Y-%m-%d")
    return render_template("add_expense.html", categories=CATEGORIES, today=today, form={})


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
