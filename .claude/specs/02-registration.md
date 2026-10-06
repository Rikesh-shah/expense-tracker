# Spec: Registration

## Overview
This step wires up user registration for Spendly. The `GET /register` route already renders the form template; this step adds the `POST /register` handler that validates the submitted data, hashes the password, inserts the new user into the `users` table, and redirects to the login page on success. It also introduces the `create_user()` DB helper and a flash-message pattern that all future auth steps will reuse.

## Depends on
- Step 1 — Database Setup (`get_db()`, `init_db()`, `users` table schema must exist)

## Routes
- `POST /register` — process registration form — public

## Database changes
No new tables or columns. The `users` table already has all required columns (`name`, `email`, `password_hash`, `created_at`). A new helper function is added to `database/db.py`:

```
create_user(name, email, password) -> int | None
```

Returns the new user's `id` on success, or `None` if the email already exists.

## Templates
- **Modify:** `templates/register.html` — add `method="POST"` and `action="{{ url_for('register') }}"` to the `<form>` tag; add `name` attributes to all inputs; display flash messages at the top of the form.

## Files to change
- `app.py` — add `POST /register` handler; import `flash`, `redirect`, `request` from Flask; import `create_user` from `database.db`; set `app.secret_key`
- `database/db.py` — add `create_user()` helper
- `templates/register.html` — wire up the form and flash message display

## Files to create
None.

## New dependencies
No new pip packages. Uses:
- `werkzeug.security.generate_password_hash` (already installed)
- `sqlite3` (standard library)
- `flask.flash`, `flask.redirect`, `flask.request` (already installed)

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `create_user()` must live in `database/db.py`, not inline in the route
- Duplicate email must be caught gracefully — flash an error, re-render the form (do not let a raw `sqlite3.IntegrityError` bubble up to the user)
- `app.secret_key` must be set before `flash()` will work; use a hard-coded dev string for now (e.g. `"dev-secret-key"`)
- After successful registration redirect to `url_for('login')` with a success flash message
- Input validation: name, email, and password fields must all be non-empty; flash an error if any are missing
- Do not log the user in automatically after registration — that is a later step

## Definition of done
- [ ] Submitting the form with valid data creates a new row in the `users` table
- [ ] The stored password is a hash, not plain text
- [ ] Submitting with a duplicate email shows a flash error and does not crash
- [ ] Submitting with any empty field shows a validation error flash message
- [ ] Successful registration redirects to `/login`
- [ ] A success flash message is visible on the login page after redirect
- [ ] Flash error messages are visible on the register page on failure
- [ ] `GET /register` still works (renders the empty form)
- [ ] App starts without errors
