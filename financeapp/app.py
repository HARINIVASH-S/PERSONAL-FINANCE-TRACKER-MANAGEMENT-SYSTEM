"""
FinanceOS - Professional Personal Finance Management App
Rewritten to use Firebase Firestore instead of MySQL
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta, timezone
import os, json, calendar
print("NEW APP VERSION LOADED")

# ─── Firebase Setup ────────────────────────────────────────────────────────────
import firebase_admin
from firebase_admin import credentials, firestore

import json

firebase_key = os.environ.get("FIREBASE_KEY")

if firebase_key:
    cred_dict = json.loads(firebase_key)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate("key.json")

firebase_admin.initialize_app(cred)
db = firestore.client()

# ─── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder='static')
app.secret_key = 'financeos_secret_key_change_in_production'

# ─── Config ───────────────────────────────────────────────────────────────────
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


CURRENCIES = {
    'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£',
    'JPY': '¥', 'CAD': 'C$', 'AUD': 'A$', 'SGD': 'S$'
}

CATEGORY_ICONS = {
    'salary': 'bi-briefcase-fill', 'freelance': 'bi-laptop-fill',
    'investment': 'bi-graph-up-arrow', 'business': 'bi-building',
    'food': 'bi-cup-hot-fill', 'transport': 'bi-car-front-fill',
    'shopping': 'bi-bag-fill', 'entertainment': 'bi-film',
    'health': 'bi-heart-pulse-fill', 'education': 'bi-book-fill',
    'utilities': 'bi-lightning-fill', 'rent': 'bi-house-fill',
    'travel': 'bi-airplane-fill', 'gym': 'bi-bicycle',
    'subscriptions': 'bi-credit-card-fill', 'other': 'bi-three-dots'
}

# ─── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_datetime(ts):
    if ts is None:
        return None

    # Firestore Timestamp -> datetime
    if hasattr(ts, "to_datetime"):
        ts = ts.to_datetime()

    # Make timezone-aware
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return ts

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_user(uid):
    """Fetch user document from Firestore."""
    doc = db.collection('users').document(uid).get()
    return doc.to_dict() if doc.exists else None

def get_transactions(uid):
    """Fetch all transactions for a user, sorted by date descending."""
    docs = db.collection('transactions')\
             .where('user_id', '==', uid)\
             .order_by('created_at', direction=firestore.Query.DESCENDING)\
             .stream()
    txns = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        # Convert Firestore timestamp to datetime if needed
        if hasattr(d.get('created_at'), 'seconds'):
            d['created_at'] = d['created_at'].astimezone(None).replace(tzinfo=None) if hasattr(d['created_at'], 'astimezone') else datetime.fromtimestamp(d['created_at'].seconds)
        txns.append(d)
    return txns

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Find user by email
        users = db.collection('users').where('email', '==', email).stream()
        user = None
        uid  = None
        for doc in users:
            user = doc.to_dict()
            uid  = doc.id
            break

        if user and check_password_hash(user.get('password_hash', ''), password):
            session['user_id']   = uid
            session['user_name'] = user.get('name', '')
            session['currency']  = user.get('currency', 'INR')
            session['theme']     = user.get('theme', 'dark')
            flash(f"Welcome back, {user['name']}! 👋", 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone    = request.form.get('phone', '').strip()

        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return render_template('signup.html')

        # Check if email already exists
        existing = db.collection('users').where('email', '==', email).stream()
        if any(True for _ in existing):
            flash('Email already registered.', 'danger')
            return render_template('signup.html')

        # Create user document
        pw_hash = generate_password_hash(password)
        new_user = {
            'name':          name,
            'email':         email,
            'password_hash': pw_hash,
            'phone':         phone,
            'currency':      'INR',
            'theme':         'dark',
            'avatar':        None,
            'created_at':    firestore.SERVER_TIMESTAMP
        }
        db.collection('users').add(new_user)
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Fetch all transactions
    all_txns = get_transactions(uid)

    # ── Stats ──
    balance = 0.0
    monthly_income = 0.0
    monthly_expense = 0.0
    for t in all_txns:
        amt = float(t.get('amount', 0))
        t_type = t.get('type', '')

        created = safe_datetime(t.get('created_at'))
        in_month = created and created >= month_start

        if t_type == 'income':
            balance += amt
            if in_month:
                monthly_income += amt
        elif t_type == 'expense':
            balance -= amt
            if in_month:
                monthly_expense += amt

    stats = {
        'balance':         round(balance, 2),
        'monthly_income':  round(monthly_income, 2),
        'monthly_expense': round(monthly_expense, 2),
        'savings':         round(monthly_income - monthly_expense, 2)
    }

    # ── Recent transactions (last 7) ──
    recent = all_txns[:7]

    # ── 6-month chart ──
    chart_labels, chart_income, chart_expense = [], [], []
    for i in range(5, -1, -1):
        d = now - timedelta(days=30 * i)
        ms = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        me_day = calendar.monthrange(d.year, d.month)[1]
        me = d.replace(day=me_day, hour=23, minute=59, second=59, microsecond=0)
        inc = sum(float(t['amount']) for t in all_txns
                  if t.get('type') == 'income' and isinstance(t.get('created_at'), datetime)
                  and ms <= t['created_at'] <= me)
        exp = sum(float(t['amount']) for t in all_txns
                  if t.get('type') == 'expense' and isinstance(t.get('created_at'), datetime)
                  and ms <= t['created_at'] <= me)
        chart_labels.append(d.strftime('%b'))
        chart_income.append(round(inc, 2))
        chart_expense.append(round(exp, 2))

    # ── Category breakdown (this month, expenses) ──
    cat_totals = {}
    for t in all_txns:
        if t.get('type') == 'expense':
            created = t.get('created_at')
            if isinstance(created, datetime) and created >= month_start:
                cat = t.get('category', 'other')
                cat_totals[cat] = cat_totals.get(cat, 0) + float(t.get('amount', 0))
    sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:6]
    cat_labels = [c[0].title() for c in sorted_cats]
    cat_data   = [round(c[1], 2) for c in sorted_cats]

    # ── Goals (latest 3) ──
    goal_docs = db.collection('goals').where('user_id', '==', uid)\
                  .order_by('created_at', direction=firestore.Query.DESCENDING)\
                  .limit(3).stream()
    goals = []
    for doc in goal_docs:
        g = doc.to_dict(); g['id'] = doc.id
        goals.append(g)

    # ── Budget alerts ──
    budget_docs = db.collection('budgets').where('user_id', '==', uid).stream()
    budget_alerts = []
    for doc in budget_docs:
        b = doc.to_dict(); b['id'] = doc.id
        cat = b.get('category', '')
        limit = float(b.get('limit_amount', 0))
        spent = sum(float(t['amount']) for t in all_txns
                    if t.get('type') == 'expense' and t.get('category') == cat
                    and isinstance(t.get('created_at'), datetime)
                    and t['created_at'] >= month_start)
        pct = (spent / limit * 100) if limit else 0
        if pct >= 80:
            budget_alerts.append({'category': cat, 'pct': round(pct, 1),
                                  'spent': spent, 'limit': limit})

    currency = CURRENCIES.get(session.get('currency', 'INR'), '₹')
    return render_template('dashboard.html',
        stats=stats, recent=recent, goals=goals,
        budget_alerts=budget_alerts, currency=currency,
        cat_icons=CATEGORY_ICONS,
        chart_data=json.dumps({'labels': chart_labels, 'income': chart_income, 'expense': chart_expense}),
        cat_chart=json.dumps({'labels': cat_labels, 'data': cat_data})
    )

# ── Transactions ──────────────────────────────────────────────────────────────

@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    uid = session['user_id']

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            t_type   = request.form.get('type')
            category = request.form.get('category', '').lower().strip()
            amount   = float(request.form.get('amount', 0))
            note     = request.form.get('note', '')
            date_str = request.form.get('date', '')

            if amount <= 0:
                flash('Amount must be positive.', 'danger')
                return redirect(url_for('transactions'))

            # Check balance for expense
            if t_type == 'expense':
                all_txns = get_transactions(uid)
                bal = sum(float(t['amount']) if t.get('type') == 'income'
                          else -float(t['amount']) for t in all_txns)
                if amount > bal:
                    sym = CURRENCIES.get(session.get('currency', 'INR'), '₹')
                    flash(f'Insufficient balance. Available: {sym}{bal:.2f}', 'danger')
                    return redirect(url_for('transactions'))

            ts = datetime.strptime(date_str, '%Y-%m-%dT%H:%M') if date_str else datetime.now()
            db.collection('transactions').add({
                'user_id':    uid,
                'type':       t_type,
                'category':   category,
                'amount':     amount,
                'note':       note,
                'created_at': ts
            })
            flash(f'{"💰 Income" if t_type == "income" else "💸 Expense"} of {amount:.2f} added!', 'success')

        elif action == 'delete':
            tid = request.form.get('tid')
            db.collection('transactions').document(tid).delete()
            flash('Transaction deleted.', 'info')

        elif action == 'edit':
            tid      = request.form.get('tid')
            category = request.form.get('category', '').lower().strip()
            amount   = float(request.form.get('amount', 0))
            note     = request.form.get('note', '')
            db.collection('transactions').document(tid).update({
                'category': category,
                'amount':   amount,
                'note':     note
            })
            flash('Transaction updated.', 'success')

        return redirect(url_for('transactions'))

    # ── GET: filters + pagination ──
    search  = request.args.get('search', '')
    f_type  = request.args.get('type', '')
    f_cat   = request.args.get('category', '')
    f_from  = request.args.get('from', '')
    f_to    = request.args.get('to', '')
    page    = int(request.args.get('page', 1))
    per_page = 15

    all_txns = get_transactions(uid)

    # Apply filters in Python (Firestore has limited multi-filter support on free tier)
    filtered = []
    for t in all_txns:
        if search and search.lower() not in t.get('note', '').lower() \
                  and search.lower() not in t.get('category', '').lower():
            continue
        if f_type and t.get('type') != f_type:
            continue
        if f_cat and t.get('category') != f_cat:
            continue
        created = t.get('created_at')
        if f_from and isinstance(created, datetime):
            if created.date() < datetime.strptime(f_from, '%Y-%m-%d').date():
                continue
        if f_to and isinstance(created, datetime):
            if created.date() > datetime.strptime(f_to, '%Y-%m-%d').date():
                continue
        filtered.append(t)

    total = len(filtered)
    paginated = filtered[(page - 1) * per_page: page * per_page]

    balance = sum(float(t['amount']) if t.get('type') == 'income'
                  else -float(t['amount']) for t in all_txns)
    categories = list({t.get('category') for t in all_txns if t.get('category')})

    currency = CURRENCIES.get(session.get('currency', 'INR'), '₹')
    return render_template('transactions.html',
        transactions=paginated, balance=round(balance, 2),
        currency=currency, categories=sorted(categories),
        cat_icons=CATEGORY_ICONS, total=total, page=page, per_page=per_page,
        search=search, f_type=f_type, f_cat=f_cat, f_from=f_from, f_to=f_to
    )

# ── Analytics ─────────────────────────────────────────────────────────────────

@app.route('/analytics')
@login_required
def analytics():
    uid = session['user_id']
    

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    all_txns = get_transactions(uid)

    # 12-month trend
    months, inc_data, exp_data = [], [], []
    for i in range(11, -1, -1):
        d = now - timedelta(days=30 * i)
        ms = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        me_day = calendar.monthrange(d.year, d.month)[1]
        me = d.replace(day=me_day, hour=23, minute=59, second=59, microsecond=0)
        inc = sum(float(t['amount']) for t in all_txns
                  if t.get('type') == 'income' and isinstance(t.get('created_at'), datetime)
                  and ms <= t['created_at'] <= me)
        exp = sum(float(t['amount']) for t in all_txns
                  if t.get('type') == 'expense' and isinstance(t.get('created_at'), datetime)
                  and ms <= t['created_at'] <= me)
        months.append(d.strftime('%b %Y'))
        inc_data.append(round(inc, 2))
        exp_data.append(round(exp, 2))

    # Category breakdown (all time)
    cat_map = {}
    for t in all_txns:
        key = (t.get('category', 'other'), t.get('type', 'expense'))
        cat_map[key] = cat_map.get(key, 0) + float(t.get('amount', 0))
    cat_rows = [{'cat': k[0], 'type': k[1], 'total': round(v, 2)} for k, v in cat_map.items()]

    # Daily spending last 30 days
    cutoff = now - timedelta(days=30)
    daily_map = {}
    for t in all_txns:
        if t.get('type') == 'expense' and isinstance(t.get('created_at'), datetime):
            if t['created_at'] >= cutoff:
                day = t['created_at'].strftime('%Y-%m-%d')
                daily_map[day] = daily_map.get(day, 0) + float(t.get('amount', 0))
    daily = [{'day': k, 'total': round(v, 2)} for k, v in sorted(daily_map.items())]

    currency = CURRENCIES.get(session.get('currency', 'INR'), '₹')
    return render_template('analytics.html',
        currency=currency,
        trend=json.dumps({'months': months, 'income': inc_data, 'expense': exp_data}),
        cat_data=json.dumps(cat_rows),
        daily=json.dumps(daily)
    )

# ── Budget Planner ─────────────────────────────────────────────────────────────

@app.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    uid = session['user_id']
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'set':
            category     = request.form.get('category', '').lower().strip()
            limit_amount = float(request.form.get('limit_amount', 0))
            # Check if budget exists for this category
            existing = db.collection('budgets')\
                         .where('user_id', '==', uid)\
                         .where('category', '==', category).stream()
            existing_doc = next(existing, None)
            if existing_doc:
                db.collection('budgets').document(existing_doc.id).update({'limit_amount': limit_amount})
            else:
                db.collection('budgets').add({
                    'user_id':      uid,
                    'category':     category,
                    'limit_amount': limit_amount,
                    'created_at':   firestore.SERVER_TIMESTAMP
                })
            flash(f'Budget set for {category.title()}.', 'success')

        elif action == 'delete':
            bid = request.form.get('bid')
            db.collection('budgets').document(bid).delete()
            flash('Budget deleted.', 'info')

        return redirect(url_for('budget'))

    # GET
    all_txns = get_transactions(uid)
    budget_docs = db.collection('budgets').where('user_id', '==', uid).stream()
    budget_data = []
    for doc in budget_docs:
        b = doc.to_dict(); b['id'] = doc.id
        cat   = b.get('category', '')
        limit = float(b.get('limit_amount', 0))
        spent = sum(float(t['amount']) for t in all_txns
                    if t.get('type') == 'expense' and t.get('category') == cat
                    and isinstance(t.get('created_at'), datetime)
                    and t['created_at'] >= month_start)
        pct = min((spent / limit) * 100, 100) if limit else 0
        budget_data.append({**b, 'spent': round(spent, 2),
                             'pct': round(pct, 1),
                             'remaining': round(max(limit - spent, 0), 2)})

    currency = CURRENCIES.get(session.get('currency', 'INR'), '₹')
    return render_template('budget.html', budgets=budget_data,
                           currency=currency, cat_icons=CATEGORY_ICONS)

# ── Goals ─────────────────────────────────────────────────────────────────────

@app.route('/goals', methods=['GET', 'POST'])
@login_required
def goals():
    uid = session['user_id']

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name     = request.form.get('name', '')
            target   = float(request.form.get('target_amount', 0))
            deadline = request.form.get('deadline', '')
            db.collection('goals').add({
                'user_id':       uid,
                'name':          name,
                'target_amount': target,
                'saved_amount':  0.0,
                'deadline':      deadline or None,
                'created_at':    firestore.SERVER_TIMESTAMP
            })
            flash(f'Goal "{name}" created!', 'success')

        elif action == 'contribute':
            gid    = request.form.get('gid')
            amount = float(request.form.get('amount', 0))
            ref    = db.collection('goals').document(gid)
            goal   = ref.get().to_dict()
            new_saved = float(goal.get('saved_amount', 0)) + amount
            ref.update({'saved_amount': new_saved})
            flash(f'{CURRENCIES.get(session.get("currency","INR"),"₹")}{amount:.0f} added to goal!', 'success')

        elif action == 'delete':
            gid = request.form.get('gid')
            db.collection('goals').document(gid).delete()
            flash('Goal deleted.', 'info')

        return redirect(url_for('goals'))

    goal_docs = db.collection('goals').where('user_id', '==', uid)\
                  .order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    goals_data = []
    for doc in goal_docs:
        g = doc.to_dict(); g['id'] = doc.id
        target = float(g.get('target_amount', 0))
        saved  = float(g.get('saved_amount', 0))
        pct    = min((saved / target) * 100, 100) if target else 0
        remaining_days = None
        if g.get('deadline'):
            try:
                dl = datetime.strptime(g['deadline'], '%Y-%m-%d').date()
                remaining_days = (dl - datetime.now().date()).days
            except Exception:
                pass
        goals_data.append({**g, 'pct': round(pct, 1), 'remaining_days': remaining_days})

    currency = CURRENCIES.get(session.get('currency', 'INR'), '₹')
    return render_template('goals.html', goals=goals_data, currency=currency)

# ── Settings ──────────────────────────────────────────────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    uid = session['user_id']

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            name     = request.form.get('name', '').strip()
            phone    = request.form.get('phone', '').strip()
            currency = request.form.get('currency', 'INR')
            theme    = request.form.get('theme', 'dark')

            update_data = {'name': name, 'phone': phone,
                           'currency': currency, 'theme': theme}

            # Avatar upload
            if 'avatar' in request.files:
                f = request.files['avatar']
                if f and f.filename and allowed_file(f.filename):
                    fname = secure_filename(f'{uid}_{f.filename}')
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    update_data['avatar'] = f'images/avatars/{fname}'

            db.collection('users').document(uid).update(update_data)
            session['user_name'] = name
            session['currency']  = currency
            session['theme']     = theme
            flash('Profile updated!', 'success')

        elif action == 'change_password':
            old_pw = request.form.get('old_password', '')
            new_pw = request.form.get('new_password', '')
            user   = get_user(uid)
            if user and check_password_hash(user.get('password_hash', ''), old_pw):
                db.collection('users').document(uid).update({
                    'password_hash': generate_password_hash(new_pw)
                })
                flash('Password changed successfully!', 'success')
            else:
                flash('Old password incorrect.', 'danger')

        return redirect(url_for('settings'))

    user = get_user(uid)
    return render_template('settings.html', user=user, currencies=CURRENCIES)

# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.route('/api/spending-tip')
@login_required
def spending_tip():
    uid = session['user_id']
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    all_txns = get_transactions(uid)
    cat_totals = {}
    for t in all_txns:
        if t.get('type') == 'expense' and isinstance(t.get('created_at'), datetime):
            if t['created_at'] >= month_start:
                cat = t.get('category', 'other')
                cat_totals[cat] = cat_totals.get(cat, 0) + float(t.get('amount', 0))

    top_cat = max(cat_totals, key=cat_totals.get) if cat_totals else None

    tips = [
        "Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings.",
        "Set up automatic transfers to your savings account on payday.",
        "Review your subscriptions monthly — cancel unused ones.",
        "Cook at home 3 more days a week to cut food costs significantly.",
        "Before any purchase over ₹500, wait 24 hours. You'll often skip it.",
        "Track every rupee — awareness alone reduces spending by 15%.",
        "Build a 3-month emergency fund before investing.",
    ]
    cat_tips = {
        'food':          'Your top expense is food. Meal prepping can save up to 40%!',
        'shopping':      'Shopping is your biggest expense. Try a 30-day no-buy challenge!',
        'entertainment': 'Entertainment is leading. Consider free alternatives like parks or libraries.',
        'transport':     'Transport costs are high. Can you carpool or use public transit more?',
        'subscriptions': 'You have high subscription costs. Audit them monthly!',
    }
    tip = cat_tips.get(top_cat, tips[datetime.now().day % len(tips)]) if top_cat else tips[datetime.now().day % len(tips)]
    return jsonify({'tip': tip, 'category': top_cat.title() if top_cat else None})


@app.route('/api/toggle-theme', methods=['POST'])
@login_required
def toggle_theme():
    current   = session.get('theme', 'dark')
    new_theme = 'light' if current == 'dark' else 'dark'
    session['theme'] = new_theme
    db.collection('users').document(session['user_id']).update({'theme': new_theme})
    return jsonify({'theme': new_theme})

# ── Error Handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('404.html', error="Server error"), 500







# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# ── AI BUDGET ADVISOR
# ══════════════════════════════════════════════════════════════════════════════

from groq import Groq
import os

def _build_financial_context(uid):
    """Build live financial snapshot to inject into every AI prompt."""
    now  = datetime.now(timezone.utc)
    ms   = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    txns = get_transactions(uid)
    user = get_user(uid)
    cur  = CURRENCIES.get(user.get('currency', 'INR'), '₹') if user else '₹'

    balance = sum(float(t['amount']) if t.get('type') == 'income' else -float(t['amount']) for t in txns)
    m_inc   = sum(float(t['amount']) for t in txns if t.get('type') == 'income'
                  and isinstance(t.get('created_at'), datetime) and t['created_at'] >= ms)
    m_exp   = sum(float(t['amount']) for t in txns if t.get('type') == 'expense'
                  and isinstance(t.get('created_at'), datetime) and t['created_at'] >= ms)

    cat_exp = {}
    for t in txns:
        if t.get('type') == 'expense' and isinstance(t.get('created_at'), datetime) and t['created_at'] >= ms:
            c = t.get('category', 'other')
            cat_exp[c] = cat_exp.get(c, 0) + float(t.get('amount', 0))

    cat_lines = '\n'.join(f"  • {c.title()}: {cur}{v:,.2f}"
                          for c, v in sorted(cat_exp.items(), key=lambda x: -x[1])[:8])

    budget_docs  = db.collection('budgets').where('user_id', '==', uid).stream()
    budget_lines = []
    for doc in budget_docs:
        b   = doc.to_dict()
        cat = b.get('category', '')
        lim = float(b.get('limit_amount', 0))
        sp  = cat_exp.get(cat, 0)
        pct = (sp / lim * 100) if lim else 0
        budget_lines.append(f"  • {cat.title()}: {cur}{sp:,.0f} / {cur}{lim:,.0f} ({pct:.0f}%)")

    goal_docs  = db.collection('goals').where('user_id', '==', uid).stream()
    goal_lines = []
    for doc in goal_docs:
        g  = doc.to_dict()
        sa = float(g.get('saved_amount', 0))
        ta = float(g.get('target_amount', 1))
        goal_lines.append(f"  • {g.get('name')}: {cur}{sa:,.0f} / {cur}{ta:,.0f} ({sa/ta*100:.0f}%)")

    recent_lines = []
    for t in txns[:5]:
        sign = '+' if t.get('type') == 'income' else '-'
        dt   = t['created_at'].strftime('%d %b') if isinstance(t.get('created_at'), datetime) else '—'
        recent_lines.append(f"  {sign}{cur}{float(t.get('amount',0)):,.2f}  {t.get('category','?').title()}  ({dt})")

    savings_rate = ((m_inc - m_exp) / m_inc * 100) if m_inc > 0 else 0

    return f"""=== USER FINANCIAL SNAPSHOT (live) ===
Name: {user.get('name','User') if user else 'User'} | Currency: {cur}
Total Balance: {cur}{balance:,.2f}
This Month — Income: {cur}{m_inc:,.2f} | Expenses: {cur}{m_exp:,.2f} | Savings: {cur}{m_inc-m_exp:,.2f} ({savings_rate:.1f}%)

TOP EXPENSE CATEGORIES (this month):
{cat_lines if cat_lines else '  (no expenses yet)'}

BUDGET STATUS:
{chr(10).join(budget_lines) if budget_lines else '  (no budgets set)'}

GOALS:
{chr(10).join(goal_lines) if goal_lines else '  (no goals set)'}

RECENT TRANSACTIONS:
{chr(10).join(recent_lines) if recent_lines else '  (none)'}
======================================""".strip()


ADVISOR_SYSTEM = """You are FinanceOS AI — a brilliant, warm personal finance advisor embedded in a finance app. You have the user's LIVE financial data in every message.

Personality: warm, non-judgmental, highly specific — always reference the user's ACTUAL numbers.

You help with: budget analysis, spending patterns, goal planning, savings strategies, debt/EMI management, investment readiness, tax-saving (India: 80C, NPS, HRA), "what if" scenarios, emergency fund sizing, monthly health scores, retirement basics.

ALWAYS reference real numbers from the snapshot. NEVER give generic advice like "spend less" without tying it to their data.
Format responses with **bold**, bullet points, and clear sections. End with 1-2 follow-up questions."""


@app.route('/ai-advisor', methods=['GET'])
@login_required
def ai_advisor():
    uid      = session['user_id']
    ctx      = _build_financial_context(uid)
    currency = CURRENCIES.get(session.get('currency', 'INR'), '₹')
    return render_template('ai_advisor.html', financial_context=ctx, currency=currency)


@app.route('/api/ai-chat', methods=['POST'])
@login_required
def ai_chat():
    from flask import Response, stream_with_context

    data    = request.get_json(force=True)
    history = data.get('messages', [])
    new_msg = data.get('message', '').strip()

    if not new_msg:
        return jsonify({'error': 'Empty message'}), 400

    uid    = session['user_id']
    ctx    = _build_financial_context(uid)
    system = ADVISOR_SYSTEM + "\n\n" + ctx

    # Build messages with full conversation history
    messages = [{"role": "system", "content": system}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": new_msg})

    ai_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def generate():
        try:
            stream = ai_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1500,
                stream=True
            )
            for chunk in stream:
                text = chunk.choices[0].delta.content
                if text:
                    yield text
        except Exception as e:
            print("Groq error:", e)
            yield "⚠️ AI temporarily unavailable. Please try again."

    return Response(stream_with_context(generate()), mimetype='text/plain')


@app.route('/api/ai-quick-insight', methods=['GET'])
@login_required
def ai_quick_insight():
    try:
        uid    = session['user_id']
        ctx    = _build_financial_context(uid)
        system = ADVISOR_SYSTEM + "\n\n" + ctx

        ai_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response  = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": "Give ONE sharp financial insight in 2-3 sentences using actual numbers. End with one actionable suggestion. No intro or sign-off."}
            ],
            max_tokens=200
        )
        text = response.choices[0].message.content.strip()
        return jsonify({'insight': text})

    except Exception as e:
        print("AI insight error:", e)
        return jsonify({'insight': 'Add more transactions to unlock AI insights.'})


if __name__ == '__main__':
    app.run()