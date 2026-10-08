from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "CHANGE-ME-IN-PRODUCTION"
DB = "schooltech.db"

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        topic TEXT NOT NULL,
        score REAL NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        due_date TEXT,
        status TEXT NOT NULL DEFAULT 'À faire',
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or len(password) < 6:
            flash("Remplis tous les champs. Le mot de passe doit avoir au moins 6 caractères.")
            return redirect(url_for("register"))

        conn = db()
        try:
            conn.execute(
                "INSERT INTO users (name,email,password) VALUES (?,?,?)",
                (name, email, generate_password_hash(password))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Cette adresse e-mail est déjà utilisée.")
            return redirect(url_for("register"))

        conn.close()
        flash("Compte créé. Tu peux maintenant te connecter.")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))

        flash("E-mail ou mot de passe incorrect.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = db()
    results = conn.execute(
        "SELECT * FROM results WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    weak = [r for r in results if r["score"] < 10]
    avg = round(sum(r["score"] for r in results) / len(results), 2) if results else None

    return render_template(
        "dashboard.html",
        results=results,
        tasks=tasks,
        weak=weak,
        average=avg
    )

@app.route("/result/add", methods=["POST"])
@login_required
def add_result():
    subject = request.form["subject"].strip()
    topic = request.form["topic"].strip()
    try:
        score = float(request.form["score"])
    except ValueError:
        flash("La note doit être un nombre.")
        return redirect(url_for("dashboard"))

    if not subject or not topic or not 0 <= score <= 20:
        flash("Vérifie les informations saisies.")
        return redirect(url_for("dashboard"))

    conn = db()
    conn.execute(
        "INSERT INTO results (user_id,subject,topic,score) VALUES (?,?,?,?)",
        (session["user_id"], subject, topic, score)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/task/add", methods=["POST"])
@login_required
def add_task():
    title = request.form["title"].strip()
    due_date = request.form["due_date"].strip()

    if title:
        conn = db()
        conn.execute(
            "INSERT INTO tasks (user_id,title,due_date) VALUES (?,?,?)",
            (session["user_id"], title, due_date)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("dashboard"))

@app.route("/task/<int:task_id>/done")
@login_required
def task_done(task_id):
    conn = db()
    conn.execute(
        "UPDATE tasks SET status='Terminé' WHERE id=? AND user_id=?",
        (task_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
