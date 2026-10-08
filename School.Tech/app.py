import os
import sqlite3
from functools import wraps

from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from jinja2 import DictLoader
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "school-tech-change-me")
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "school_tech.db")

# ---------------------------------------------------------------- Templates
BASE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{% block title %}School.Tech{% endblock %}</title>
<style>
:root{--bg:#0b1020;--card:#141b34;--line:#232c4d;--tx:#e8ecf8;--mut:#8f9ac0;--ac:#5b8cff;--red:#ff5d6c;--org:#ffb347;--grn:#3ddc97}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--tx);line-height:1.5}
a{color:var(--ac);text-decoration:none}
nav{display:flex;justify-content:space-between;align-items:center;padding:14px 22px;border-bottom:1px solid var(--line)}
nav b{font-size:20px;letter-spacing:.5px}nav span{color:var(--mut);margin-right:14px}
main{max-width:900px;margin:0 auto;padding:22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin-bottom:18px}
h1,h2{margin:0 0 12px}h1{font-size:26px}h2{font-size:18px}
input{width:100%;padding:11px 13px;margin:6px 0 12px;border-radius:10px;border:1px solid var(--line);background:#0e1427;color:var(--tx);font-size:15px}
button{background:var(--ac);color:#fff;border:0;border-radius:10px;padding:11px 18px;font-size:15px;cursor:pointer}
button.del{background:transparent;color:var(--red);padding:4px 8px}
.row{display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:10px;align-items:end}
.msg{padding:11px 14px;border-radius:10px;background:#2a1d3a;border:1px solid #5b3a7a;margin-bottom:14px}
.big{font-size:38px;font-weight:700}.mut{color:var(--mut)}
.sub{display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-top:1px solid var(--line)}
.tag{padding:3px 10px;border-radius:99px;font-size:13px;font-weight:600}
.red{background:#3b1a22;color:var(--red)}.orange{background:#3b2e17;color:var(--org)}.green{background:#12342a;color:var(--grn)}
.bar{height:6px;border-radius:9px;background:var(--line);margin-top:6px;overflow:hidden}.bar i{display:block;height:100%}
table{width:100%;border-collapse:collapse}td{padding:8px 4px;border-top:1px solid var(--line)}
.auth{max-width:420px;margin:50px auto}
@media(max-width:640px){.row{grid-template-columns:1fr 1fr}}
</style></head><body>
<nav><b>School.<span style="color:var(--ac);margin:0">Tech</span></b>
<div>{% if session.uid %}<span>{{ session.name }}</span><a href="{{ url_for('logout') }}">Déconnexion</a>
{% else %}<a href="{{ url_for('login') }}">Connexion</a>{% endif %}</div></nav>
<main>
{% for m in get_flashed_messages() %}<div class="msg">{{ m }}</div>{% endfor %}
{% block body %}{% endblock %}
</main></body></html>"""

HOME = """{% extends 'base.html' %}{% block body %}
<div class="card" style="margin-top:40px;text-align:center">
<h1>Voir ses lacunes avant qu'elles ne coûtent des points.</h1>
<p class="mut">School.Tech aide l'élève à repérer ses points faibles, savoir quoi réviser en priorité et suivre son évolution.
Il ne remplace pas le professeur : il aide à comprendre où progresser.</p>
<p><a href="{{ url_for('register') }}"><button>Créer mon compte</button></a>
&nbsp; <a href="{{ url_for('login') }}">J'ai déjà un compte</a></p></div>{% endblock %}"""

REGISTER = """{% extends 'base.html' %}{% block body %}
<div class="card auth"><h1>Créer un compte</h1>
<form method="post">
<label>Nom</label><input name="name" required maxlength="60">
<label>Email</label><input name="email" type="email" required>
<label>Mot de passe (6 caractères minimum)</label><input name="password" type="password" required minlength="6">
<button>S'inscrire</button></form>
<p class="mut">Déjà inscrit ? <a href="{{ url_for('login') }}">Connexion</a></p></div>{% endblock %}"""

LOGIN = """{% extends 'base.html' %}{% block body %}
<div class="card auth"><h1>Connexion</h1>
<form method="post">
<label>Email</label><input name="email" type="email" required>
<label>Mot de passe</label><input name="password" type="password" required>
<button>Se connecter</button></form>
<p class="mut">Pas de compte ? <a href="{{ url_for('register') }}">Inscription</a></p></div>{% endblock %}"""

DASH = """{% extends 'base.html' %}{% block body %}
<div class="card"><h2>Ma moyenne générale</h2>
{% if subjects %}
<div class="big">{{ '%.2f'|format(overall) }}<span class="mut" style="font-size:18px"> / 20</span></div>
{% if focus %}<p>🎯 <b>À réviser en priorité : {{ focus.subject }}</b> (moyenne {{ '%.1f'|format(focus.avg) }}).</p>{% endif %}
{% for s in declining %}<p style="color:var(--org)">⚠ {{ s.subject }} est en baisse ({{ s.trend }} pts sur la dernière note).</p>{% endfor %}
{% if not focus and not declining %}<p style="color:var(--grn)">✔ Aucune matière en difficulté pour le moment. Continue !</p>{% endif %}
{% else %}<p class="mut">Ajoute ta première note pour voir ton analyse.</p>{% endif %}
</div>

<div class="card"><h2>Ajouter une note</h2>
<form method="post" action="{{ url_for('add_grade') }}" class="row">
<div><label>Matière</label><input name="subject" required maxlength="40" placeholder="Maths"></div>
<div><label>Note /20</label><input name="score" type="number" step="0.25" min="0" max="20" required></div>
<div><label>Coef</label><input name="coef" type="number" step="0.5" min="0.5" value="1" required></div>
<div><button>Ajouter</button></div></form></div>

{% if subjects %}
<div class="card"><h2>Mes matières (des plus faibles aux plus fortes)</h2>
{% for s in subjects %}
<div class="sub"><div style="flex:1"><b>{{ s.subject }}</b> <span class="mut">· {{ s.n }} note(s) · dernière : {{ s.last }}</span>
<div class="bar"><i style="width:{{ s.avg * 5 }}%;background:var(--{{ {'red':'red','orange':'org','green':'grn'}[s.level] }})"></i></div></div>
<div style="text-align:right;margin-left:16px"><b>{{ '%.1f'|format(s.avg) }}</b>
{% if s.trend is not none %}<span class="mut"> {{ '▲' if s.trend >= 0 else '▼' }} {{ s.trend|abs }}</span>{% endif %}<br>
<span class="tag {{ s.level }}">{{ {'red':'Priorité haute','orange':'À renforcer','green':'Solide'}[s.level] }}</span></div></div>
{% endfor %}</div>

<div class="card"><h2>Historique</h2><table>
{% for g in history %}<tr><td>{{ g.subject }}</td><td><b>{{ g.score }}</b>/20</td><td class="mut">coef {{ g.coef }}</td>
<td class="mut">{{ g.created[:10] }}</td>
<td style="text-align:right"><form method="post" action="{{ url_for('delete_grade', gid=g.id) }}"><button class="del">Supprimer</button></form></td></tr>
{% endfor %}</table></div>
{% endif %}{% endblock %}"""

app.jinja_loader = DictLoader({
    "base.html": BASE, "home.html": HOME, "register.html": REGISTER,
    "login.html": LOGIN, "dash.html": DASH,
})


# ----------------------------------------------------------------- Base SQLite
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS grades(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        score REAL NOT NULL,
        coef REAL NOT NULL DEFAULT 1,
        created TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    conn.commit()
    conn.close()


init_db()  # exécuté aussi sous gunicorn (corrige "no such table: users")


# --------------------------------------------------------------------- Outils
def login_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if not session.get("uid"):
            return redirect(url_for("login"))
        return f(*a, **k)
    return wrapper


def analyse(uid):
    rows = db().execute("SELECT * FROM grades WHERE user_id=? ORDER BY id", (uid,)).fetchall()
    by_subject = {}
    for r in rows:
        by_subject.setdefault(r["subject"], []).append(r)
    subjects = []
    for name, rs in by_subject.items():
        total = sum(r["coef"] for r in rs)
        avg = sum(r["score"] * r["coef"] for r in rs) / total
        trend = None
        if len(rs) >= 2:
            prev = rs[:-1]
            ptot = sum(r["coef"] for r in prev)
            trend = round(rs[-1]["score"] - sum(r["score"] * r["coef"] for r in prev) / ptot, 1)
        level = "red" if avg < 10 else "orange" if avg < 12 else "green"
        subjects.append(dict(subject=name, avg=avg, n=len(rs), last=rs[-1]["score"],
                             trend=trend, level=level))
    subjects.sort(key=lambda s: s["avg"])
    tot = sum(r["coef"] for r in rows)
    overall = sum(r["score"] * r["coef"] for r in rows) / tot if tot else 0
    focus = subjects[0] if subjects and subjects[0]["avg"] < 12 else None
    declining = [s for s in subjects if s["trend"] is not None and s["trend"] <= -2]
    return subjects, overall, focus, declining, list(reversed(rows))[:15]


# --------------------------------------------------------------------- Routes
@app.route("/")
def home():
    if session.get("uid"):
        return redirect(url_for("dashboard"))
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or "@" not in email or len(password) < 6:
            flash("Remplis tous les champs (mot de passe : 6 caractères minimum).")
            return render_template("register.html")
        try:
            db().execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                         (name, email, generate_password_hash(password)))
            db().commit()
        except sqlite3.IntegrityError:
            flash("Cet email est déjà utilisé.")
            return render_template("register.html")
        flash("Compte créé. Connecte-toi.")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], request.form.get("password", "")):
            session.clear()
            session["uid"], session["name"] = user["id"], user["name"]
            return redirect(url_for("dashboard"))
        flash("Email ou mot de passe incorrect.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    subjects, overall, focus, declining, history = analyse(session["uid"])
    return render_template("dash.html", subjects=subjects, overall=overall,
                           focus=focus, declining=declining, history=history)


@app.route("/grade", methods=["POST"])
@login_required
def add_grade():
    subject = request.form.get("subject", "").strip()[:40]
    try:
        score = float(request.form.get("score", ""))
        coef = float(request.form.get("coef", "1"))
    except ValueError:
        flash("Note ou coefficient invalide.")
        return redirect(url_for("dashboard"))
    if not subject or not 0 <= score <= 20 or coef <= 0:
        flash("Matière, note (0 à 20) et coefficient (> 0) requis.")
        return redirect(url_for("dashboard"))
    db().execute("INSERT INTO grades (user_id,subject,score,coef) VALUES (?,?,?,?)",
                 (session["uid"], subject.capitalize(), score, coef))
    db().commit()
    return redirect(url_for("dashboard"))


@app.route("/grade/<int:gid>/delete", methods=["POST"])
@login_required
def delete_grade(gid):
    db().execute("DELETE FROM grades WHERE id=? AND user_id=?", (gid, session["uid"]))
    db().commit()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
