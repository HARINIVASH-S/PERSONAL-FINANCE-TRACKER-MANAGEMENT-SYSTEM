from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector

app = Flask(__name__,static_folder='static')
app.secret_key = 'your_secret_key'

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  
    database="finance_tracker"
)
cursor = db.cursor()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_id = request.form['user_id']
        user_name = request.form['user_name']
        email = request.form['email']
        phone = request.form['phone']

        if not db.is_connected():
            db.reconnect()
        cursor = db.cursor()

        cursor.execute("INSERT INTO users (user_id, user_name, email, phone) VALUES (%s, %s, %s, %s)",
                       (user_id, user_name, email, phone))
        db.commit()
        cursor.close()

        flash('✅ Signup successful!')
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/transaction', methods=['GET', 'POST'])
def transaction():
    if request.method == 'POST':
        user_id = request.form['user_id']
        category = request.form['category']
        amount = request.form['amount']

        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        user_exists = cursor.fetchone()

        if not user_exists:
            flash("❌ User does not exist. Please sign up first.")
            return redirect(url_for('home'))

        cursor.execute("INSERT INTO transactions (user_id, category, amount, type) VALUES (%s, %s, %s, 'entry')",
                       (user_id, category, amount))
        db.commit()
        flash("✅ Income added successfully.")
        return redirect(url_for('view_transactions'))
    return render_template('transaction.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        user_id = request.form['user_id']
        action = request.form['action']

        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            flash('❌ User does not exist. Please sign up first.')
            return redirect(url_for('profile'))

        if action == 'update':
            user_name = request.form['user_name']
            cursor.execute("UPDATE users SET user_name = %s WHERE user_id = %s", (user_name, user_id))
            db.commit()
            flash('✅ Profile updated successfully!')

        elif action == 'delete':
            cursor.execute("DELETE FROM transactions WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            db.commit()
            flash('✅ User deleted successfully!')

        return redirect(url_for('profile'))
    return render_template('profile.html')

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if request.method == 'POST':
        user_id = request.form['user_id']
        category = request.form['category']
        amount = float(request.form['amount'])

        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        user_exists = cursor.fetchone()

        if not user_exists:
            flash("❌ User does not exist. Please sign up first.")
            return redirect(url_for('home'))

        # Calculate current balance
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN type = 'entry' THEN amount ELSE 0 END) -
                SUM(CASE WHEN type = 'withdraw' THEN amount ELSE 0 END)
            FROM transactions
            WHERE user_id = %s
        """, (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result[0] else 0.0

        if amount > balance:
            flash(f"❌ Insufficient balance. Available balance: ₹{balance:.2f}")
            return redirect(url_for('view_transactions'))  # Redirect to transaction view page

        # Proceed with withdrawal
        cursor.execute("INSERT INTO transactions (user_id, category, amount, type) VALUES (%s, %s, %s, 'withdraw')",
                       (user_id, category, amount))
        db.commit()
        flash("✅ Expense recorded successfully.")
        return redirect(url_for('view_transactions'))
    return render_template('withdraw.html')

@app.route('/view_transactions', methods=['GET', 'POST'])
def view_transactions():
    try:
        if not db.is_connected():
            db.reconnect()

        if request.method == 'POST':
            user_id = request.form['user_id']
            cursor = db.cursor()

            # Updated JOIN query to include user_name
            cursor.execute("""
                SELECT u.user_name, t.category, t.amount, t.type, t.timestamp
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.user_id = %s
                ORDER BY t.timestamp DESC
            """, (user_id,))
            transactions = cursor.fetchall()

            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN type='entry' THEN amount ELSE 0 END) - 
                    SUM(CASE WHEN type='withdraw' THEN amount ELSE 0 END)
                FROM transactions WHERE user_id = %s
            """, (user_id,))
            balance = cursor.fetchone()[0] or 0.0

            cursor.close()
            return render_template('view_transactions.html', transactions=transactions, balance=balance, user_id=user_id)

        return render_template('view_transactions.html', transactions=None)

    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        return "A database error occurred."


    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        return "A database error occurred."




if __name__ == '__main__':
    app.run(debug=True)
