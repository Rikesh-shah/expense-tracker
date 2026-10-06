# Spec: Login and Logout

## Overview
This step implements the login and logout flows for Spendly. The `GET /login` route already renders the form; this step adds the `POST /login` handler that verifies credentials against the `users` table, writes the authenticated user's `id` into the Flask session, and redirects to the dashboard (or a stub page for now). It also implements `GET /logout` to clear the session and redirect to the landing page. A `get_user_by_email()` DB helper is introduced. Together, these two routes give Spendly a working, session-based auth layer that all future protected routes will depend on.

## Depends on
- Step 1 — Database Setup (`get_db()`, `users` table, `password_hash` column)
- Step 2 — Registration (`create_user()`, flash pattern, `login.html` template)

## Routes
- `POST /login` — process login form, verify credentials, write session — public
- `GET /logout` — clear session, redirect to landing — public (no login required to call)

## Database changes
No new tables or columns. A new helper is added to `database/db.py`:

```
get_user_by_email(email) -> sqlite3.Row | None
```

Returns the full user row (id, name, email, password_hash) or `None` if not found.

## Templates
- **Modify:** `templates/login.html` — add `method="POST"` and `action="{{ url_for('login') }}"` to the `<form>` tag; add `name` attributes to email and password inputs; display flash messages at the top of the form.
- **Modify:** `templates/base.html` — update the logout link/button to use `url_for('logout')` if it exists (check first — only change if a logout link is already present).

## Files to change
- `app.py` — implement `POST /login` handler; implement `GET /logout`; import `session` from Flask; import `get_user_by_email` from `database.db`
- `database/db.py` — add `get_user_by_email()` helper
- `templates/login.html` — wire up the form and flash message display

## Files to create
None.

## New dependencies
No new pip packages. Uses:
- `werkzeug.security.check_password_hash` (already installed)
- `flask.session` (already installed)

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plain text
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `get_user_by_email()` must live in `database/db.py`, not inline in the route
- On successful login: set `session['user_id']` to the user's integer `id` and `session['user_name']` to their name; then redirect to `url_for('profile')` (the existing stub is fine for now)
- On failed login (bad email or wrong password): flash a single generic error — "Invalid email or password." — do not reveal which field is wrong
- Input validation: both email and password fields must be non-empty; flash an error if either is missing
- `GET /logout` must call `session.clear()`, flash a brief success message ("You have been signed out."), then `redirect(url_for('landing'))`
- Do not implement any `@login_required` decorator in this step — that belongs to a later step

## Definition of done
- [ ] Submitting valid credentials sets `session['user_id']` and redirects to `/profile`
- [ ] Submitting an unknown email flashes "Invalid email or password." and re-renders the form
- [ ] Submitting a wrong password flashes "Invalid email or password." and re-renders the form
- [ ] Submitting with any empty field shows a validation error flash message
- [ ] Visiting `/logout` clears the session and redirects to `/`
- [ ] A "You have been signed out." flash message is visible on the landing page after logout
- [ ] Flash error messages are visible on the login page on failure
- [ ] `GET /login` still works (renders the empty form)
- [ ] The demo user (`demo@spendly.com` / `demo123`) can log in successfully
- [ ] App starts without errors
