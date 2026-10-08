# Spendly

A lightweight personal expense tracker built with **Flask** and **SQLite**. Users sign up, log their expenses, filter them by date, and edit or delete them from their profile.

**Live demo:** https://expense-tracker-production-c502.up.railway.app
Demo login: `demo@spendly.com` / `demo123`

---

## Features

- Account registration, login, and logout (passwords hashed with Werkzeug)
- Profile dashboard with spending stats and a per-category breakdown
- Transaction list with a date-range filter
- Add, edit, and delete expenses (only your own expenses, with ownership checks)
- Amounts shown in ₹, across seven categories: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- Analytics page (placeholder, coming soon)

## Tech stack

| Layer    | Choice                                         |
|----------|------------------------------------------------|
| Backend  | Python 3.10+, Flask 3.1                        |
| Database | SQLite through the built-in `sqlite3` module (no ORM) |
| Frontend | Jinja2 templates, plain CSS, vanilla JavaScript |
| Tests    | pytest, pytest-flask                           |
| Hosting  | Railway                                        |

## Project structure

```
expense-tracker/
├── app.py                # All routes (single file, no blueprints)
├── database/
│   └── db.py             # get_db(), init_db(), seed_db(), and all queries
├── templates/            # One Jinja2 template per page, all extend base.html
├── static/
│   ├── css/              # style.css (global), landing.css, profile.css
│   └── js/main.js        # Vanilla JS
├── tests/                # pytest suite
├── requirements.txt
└── spendly.db            # Created automatically on first run (git-ignored)
```

## Routes

| Method     | Route                   | Description                      | Login required |
|------------|-------------------------|----------------------------------|:-:|
| GET        | `/`                     | Landing page                     |   |
| GET, POST  | `/register`             | Create an account                |   |
| GET, POST  | `/login`                | Log in                           |   |
| GET        | `/logout`               | Log out                          | ✓ |
| GET        | `/profile`              | Dashboard, stats, transactions   | ✓ |
| GET        | `/analytics`            | Analytics (coming soon)          | ✓ |
| GET, POST  | `/expenses/add`         | Add an expense                   | ✓ |
| GET, POST  | `/expenses/<id>/edit`   | Edit an expense                  | ✓ |
| POST       | `/expenses/<id>/delete` | Delete an expense                | ✓ |
| GET        | `/terms`, `/privacy`    | Static legal pages               |   |

---

## Running locally

### Prerequisites

- Python 3.10 or newer
- git

### 1. Clone the repository

```bash
git clone https://github.com/Rikesh-shah/expense-tracker.git
cd expense-tracker
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the app

```bash
python app.py
```

Open **http://localhost:5001** in your browser.

On startup the app creates `spendly.db`, sets up the tables, and seeds a demo user with sample expenses:

- Email: `demo@spendly.com`
- Password: `demo123`

To start with a fresh database, stop the server, delete `spendly.db`, and run `python app.py` again.

### Running tests

```bash
pytest                                   # whole suite
pytest tests/test_delete_expense.py      # one file
pytest -k "test_name"                    # tests matching a name
pytest -s                                # show print output
```

### Environment variables

| Variable              | Default         | Purpose                                                   |
|-----------------------|-----------------|-----------------------------------------------------------|
| `PORT`                | `5001`          | Port the server listens on                                |
| `RAILWAY_ENVIRONMENT` | unset           | Set automatically by Railway. When present, Flask debug mode is turned off |

---

## Deploying to Railway

The app runs on Railway as-is. It reads `PORT` from the environment, binds to `0.0.0.0`, and turns off debug mode on Railway. Railway detects `requirements.txt` and starts the app with `python app.py`.

### Option A: Deploy with the Railway CLI

**1. Install the CLI**

```bash
# macOS / Linux / WSL
bash <(curl -fsSL https://railway.com/install.sh)

# or with npm (Node 16+)
npm i -g @railway/cli

# or with Homebrew (macOS)
brew install railway
```

**2. Log in**

```bash
railway login
```

**3. Create a project and deploy from the repo root**

```bash
railway up
```

The first run creates a new project and service, uploads the current directory, and starts a build. Later runs of `railway up` redeploy to the same service.

**4. Generate a public URL**

```bash
railway domain
```

This prints a URL such as `https://expense-tracker-production-xxxx.up.railway.app`.

**5. Check that it works**

```bash
railway deployment list      # wait for status SUCCESS
railway logs                 # should show "Debug mode: off"
```

Open the URL and log in with the demo account.

### Option B: Deploy from GitHub (auto-deploy on push)

1. Push the repository to GitHub.
2. In the [Railway dashboard](https://railway.com), click **New Project**, choose **Deploy from GitHub repo**, and select this repository.
3. Railway builds and deploys it. Each push to `main` triggers a new deploy.
4. Open the service, go to **Settings**, then **Networking**, and click **Generate Domain** to get a public URL.

### Redeploying after changes

```bash
railway up            # from the project root
```

With the GitHub integration, pushing to `main` redeploys.

### Production notes

- **Data does not persist across deploys.** SQLite writes `spendly.db` to the container's filesystem, which is wiped on every redeploy or restart. The demo user is re-seeded each time, but registered users and their expenses are lost. To keep data, attach a [Railway Volume](https://docs.railway.com/guides/volumes) and point `DB_PATH` in `database/db.py` at the volume's mount path.
- **The secret key is hardcoded.** `app.secret_key` in `app.py` is set to a dev value. For a real deployment, load it from an environment variable (for example `SECRET_KEY`) and set it with `railway variable set SECRET_KEY=<random-string>`.
- **The app uses Flask's development server.** That's fine for a demo. For real traffic, use a production WSGI server such as gunicorn. Note that gunicorn isn't in `requirements.txt` yet.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Address already in use` on port 5001 | Stop the other process, or run `PORT=5002 python app.py` |
| Railway URL returns **502** | Check `railway logs`. The app must listen on `0.0.0.0:$PORT`, which `app.py` already does |
| Registered account gone after a deploy | Expected. The database resets on every redeploy (see production notes above) |
| `railway: command not found` | Run `source ~/.railway/env` or restart your shell after installing |
