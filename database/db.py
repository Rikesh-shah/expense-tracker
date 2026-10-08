import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'spendly.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL NOT NULL,
            category    TEXT NOT NULL,
            date        TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
    ''')
    conn.commit()
    conn.close()


def seed_db():
    from werkzeug.security import generate_password_hash

    conn = get_db()
    if conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] > 0:
        conn.close()
        return

    conn.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        ('Demo User', 'demo@spendly.com', generate_password_hash('demo123')),
    )
    conn.commit()

    demo_id = conn.execute(
        'SELECT id FROM users WHERE email = ?', ('demo@spendly.com',)
    ).fetchone()['id']

    conn.executemany(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        [
            (demo_id, 42.50,  'Food',          '2026-10-01', 'Grocery run'),
            (demo_id, 28.00,  'Transport',      '2026-10-03', 'Monthly bus pass'),
            (demo_id, 120.00, 'Bills',          '2026-10-05', 'Electricity bill'),
            (demo_id, 35.00,  'Health',         '2026-10-07', 'Pharmacy'),
            (demo_id, 12.99,  'Entertainment',  '2026-10-10', 'Streaming subscription'),
            (demo_id, 65.00,  'Shopping',       '2026-10-14', 'New clothing'),
            (demo_id, 8.50,   'Other',          '2026-10-18', 'Stationery'),
            (demo_id, 18.75,  'Food',           '2026-10-21', 'Restaurant lunch'),
        ],
    )
    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password):
    from werkzeug.security import generate_password_hash
    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        return conn.execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()
    finally:
        conn.close()


def get_expenses_for_user(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        conditions = ['user_id = ?']
        params = [user_id]
        if date_from:
            conditions.append('date >= ?')
            params.append(date_from)
        if date_to:
            conditions.append('date <= ?')
            params.append(date_to)
        # conditions holds only hardcoded string literals — user input flows
        # through params as ? placeholders, never into the clause structure.
        sql = 'SELECT * FROM expenses WHERE {} ORDER BY date DESC'.format(
            ' AND '.join(conditions)
        )
        return conn.execute(sql, tuple(params)).fetchall()
    finally:
        conn.close()


def get_stats_for_user(user_id):
    conn = get_db()
    try:
        return conn.execute(
            '''
            SELECT
                COALESCE(SUM(amount), 0.0) AS total_spent,
                COUNT(*)                    AS transaction_count,
                (SELECT category
                 FROM   expenses
                 WHERE  user_id = ?
                 GROUP  BY category
                 ORDER  BY SUM(amount) DESC
                 LIMIT  1)                  AS top_category
            FROM expenses
            WHERE user_id = ?
            ''',
            (user_id, user_id)
        ).fetchone()
    finally:
        conn.close()


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        return conn.execute(
            '''
            SELECT category, SUM(amount) AS total
            FROM   expenses
            WHERE  user_id = ?
            GROUP  BY category
            ORDER  BY total DESC
            ''',
            (user_id,)
        ).fetchall()
    finally:
        conn.close()


def insert_expense(user_id, amount, category, date, description):
    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
