Welcome to the Personal Finance Tracker, a simple and intuitive web application built using Flask and MySQL. This project helps users manage their income and expenses in a structured way. Whether you're tracking your monthly salary, daily spending, or managing a budget — this app gives you a clean interface and essential features to stay financially organized.

Features :
 User Signup – Register with a unique user_id, name, email, and phone number.
 Add Income – Log your income entries with categories (e.g., Salary, Freelance).
 Record Expenses – Track your spending with real-time balance check.
 View Transactions – Get a timeline of all your transactions.
 User Profile – Update your name or delete your account (and all transactions).
 Balance Check – Prevents overspending by checking if the user has enough balance before withdrawal.

Tech Stack:
  Frontend: HTML, CSS, Bootstrap (optional for styling)
  Backend: Python with Flask
  Database: MySQL (via mysql-connector-python)

PROJECT STRUCTURE:
finance-tracker/
│
├── app.py                 # Main Flask app
├── templates/             # HTML templates (home, signup, withdraw, etc.)
│   └── home.html
│   └── signup.html
│   └── transaction.html
│   └── view_transactions.html
│   └── profile.html
│   └── withdraw.html
├── static/                # CSS/JS/static files (if any)
└── README.md              # This file!
