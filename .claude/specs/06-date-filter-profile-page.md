# Spec: Date Filter for Profile Page

## Overview
This feature adds a date range filter to the "Recent Transactions" section on the
profile page. Users can enter an optional start date and/or end date; the transaction
table then shows only expenses that fall within the specified range. Filter values are
passed as query-string parameters so the filtered URL is bookmarkable and the page
remains a plain GET with no JavaScript required. When no filter is applied the page
behaves exactly as it does today.

## Depends on
- Step 01 — Database Setup (expenses table with `date TEXT` column in `YYYY-MM-DD` format)
- Step 05 — Backend Routes / Profile Page (the `/profile` route and `get_expenses_for_user` helper)

## Routes
No new routes. The existing `GET /profile` route gains two optional query parameters:
- `date_from` — ISO date string `YYYY-MM-DD`, lower bound (inclusive)
- `date_to`   — ISO date string `YYYY-MM-DD`, upper bound (inclusive)

## Database changes
No new tables or columns. The existing `get_expenses_for_user(user_id)` helper in
`database/db.py` gains two optional keyword arguments (`date_from`, `date_to`) and
conditionally appends `AND date >= ?` / `AND date <= ?` clauses. Parameterised
queries only — no f-string interpolation.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter form above the transactions table.
  - The form submits via `GET` to `url_for('profile')` so filter values appear in the URL.
  - Two `<input type="date">` fields: `name="date_from"` and `name="date_to"`.
  - A submit button ("Filter") and a "Clear" link that navigates to the bare `/profile` URL.
  - Pre-populate fields with the current filter values so they persist after submit.
  - Show a short "Showing results from … to …" label when a filter is active.

## Files to change
- `database/db.py` — extend `get_expenses_for_user` with optional `date_from`/`date_to` params
- `app.py` — read `request.args.get('date_from')` and `request.args.get('date_to')` in the
  `/profile` route and pass them to the updated DB helper
- `templates/profile.html` — add the filter form above the transactions table

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with werkzeug (not relevant here, but left for consistency)
- Use CSS variables — never hardcode hex values in any new CSS
- All templates extend `base.html`
- Do not break the existing unfiltered behaviour — `date_from` and `date_to` are both optional
- Input values that fail basic format checks (non-date strings) should be silently ignored
  rather than crashing; a try/except around `datetime.strptime` is sufficient
- The filter form must use `method="get"` and `action="{{ url_for('profile') }}"` — no POST,
  no JavaScript fetch
- Do not add the filter form to `base.html`; it belongs only in `profile.html`

## Definition of done
- [ ] Visiting `/profile` with no query params shows all transactions (unchanged behaviour)
- [ ] Visiting `/profile?date_from=2026-10-05` shows only transactions on or after 5 Oct 2026
- [ ] Visiting `/profile?date_to=2026-10-07` shows only transactions on or before 7 Oct 2026
- [ ] Visiting `/profile?date_from=2026-10-05&date_to=2026-10-10` shows only transactions
      between 5 Oct and 10 Oct 2026 inclusive (Bills and Pharmacy from seed data)
- [ ] The filter form fields are pre-populated with the submitted values after filtering
- [ ] A "Showing results from … to …" label is visible when at least one bound is set
- [ ] The "Clear" link navigates to `/profile` and removes the filter
- [ ] An invalid date string in `date_from` or `date_to` does not crash the app
