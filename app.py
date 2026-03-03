from flask import Flask, render_template, request, redirect, session
import sqlite3
import datetime
import os 

print("python starting")

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- DATABASE CONNECTION ----------------
def connect_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- INITIALIZE DATABASE ----------------
def init_db():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT,
            password TEXT,
            role TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reset_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status TEXT,
            request_date TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect("/login")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = connect_db()
        conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email, password, "user")
        )
        conn.commit()
        conn.close()
        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = connect_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin")
            else:
                return redirect("/dashboard")

        return "Invalid Credentials"

    return render_template("login.html")

# ---------------- USER DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = connect_db()
    requests = conn.execute(
        "SELECT * FROM reset_requests WHERE user_id=?",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("dashboard.html", requests=requests)

# ---------------- REQUEST PASSWORD RESET ----------------
@app.route("/request-reset")
def request_reset():
    if "user_id" not in session:
        return redirect("/login")

    conn = connect_db()
    conn.execute(
        "INSERT INTO reset_requests (user_id, status, request_date) VALUES (?, ?, ?)",
        (session["user_id"], "Pending", str(datetime.datetime.now()))
    )
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = connect_db()
    requests = conn.execute('''
        SELECT reset_requests.id, users.username, reset_requests.status, reset_requests.request_date
        FROM reset_requests
        JOIN users ON reset_requests.user_id = users.id
    ''').fetchall()
    conn.close()

    return render_template("admin_dashboard.html", requests=requests)

# ---------------- APPROVE REQUEST (ADMIN ONLY APPROVES) ----------------
@app.route("/approve/<int:id>")
def approve(id):
    if session.get("role") != "admin":
        return redirect("/login")

    conn = connect_db()
    conn.execute(
        "UPDATE reset_requests SET status='Approved' WHERE id=?",
        (id,)
    )
    conn.commit()
    conn.close()

    return redirect("/admin")

# ---------------- USER SETS NEW PASSWORD ----------------
@app.route("/user-reset/<int:request_id>", methods=["GET", "POST"])
def user_reset(request_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = connect_db()

    request_data = conn.execute(
        "SELECT * FROM reset_requests WHERE id=? AND user_id=?",
        (request_id, session["user_id"])
    ).fetchone()

    if not request_data or request_data["status"] != "Approved":
        conn.close()
        return "Not Authorized"

    if request.method == "POST":
        new_password = request.form["new_password"]

        conn.execute(
            "UPDATE users SET password=? WHERE id=?",
            (new_password, session["user_id"])
        )

        conn.execute(
            "UPDATE reset_requests SET status='Completed' WHERE id=?",
            (request_id,)
        )

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    conn.close()
    return render_template("user_reset.html")

# ---------------- REJECT REQUEST ----------------
@app.route("/reject/<int:id>")
def reject(id):
    if session.get("role") != "admin":
        return redirect("/login")

    conn = connect_db()
    conn.execute(
        "UPDATE reset_requests SET status='Rejected' WHERE id=?",
        (id,)
    )
    conn.commit()
    conn.close()

    return redirect("/admin")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))