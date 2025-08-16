import os
from datetime import datetime, timedelta
import re

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

import firebase_admin
from firebase_admin import credentials, firestore

# ---------------------------
# Firebase
# ---------------------------
cred = credentials.Certificate("firebase-key.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------------------
# Flask
# ---------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-this")

# ---------------------------
# Helpers
# ---------------------------
def login_required(view_func):
    def wrapper(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

def current_email():
    return session.get("user_email")

def clean_id(name: str) -> str:
    return re.sub(r"[^\w\s-]", "", name).replace(" ", "_").lower()

def parse_amount(amount_str: str) -> int:
    """Convert '₹1,80,000' or '100000' -> 180000"""
    if not amount_str:
        return 0
    digits = re.sub(r"[^\d]", "", str(amount_str))
    return int(digits) if digits else 0

# ---------------------------
# Public pages
# ---------------------------
@app.route("/")
def index():
    # Public landing (not logged in) or redirect to home if logged in
    if "user_email" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

# ---------------------------
# Auth
# ---------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    # POST
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")

    if not email or not password:
        flash("Email and password are required.", "error")
        return render_template("signup.html")

    if password != confirm:
        flash("Passwords do not match.", "error")
        return render_template("signup.html")

    # Check if user exists
    user_doc = db.collection("users").document(email).get()
    if user_doc.exists:
        flash("Account already exists. Please log in.", "error")
        return redirect(url_for("login"))

    password_hash = generate_password_hash(password)
    db.collection("users").document(email).set({
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.utcnow().isoformat()
    })

    session["user_email"] = email
    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    # POST
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user_doc = db.collection("users").document(email).get()
    if not user_doc.exists:
        flash("Invalid email or password.", "error")
        return render_template("login.html")

    user = user_doc.to_dict()
    if not check_password_hash(user.get("password_hash", ""), password):
        flash("Invalid email or password.", "error")
        return render_template("login.html")

    session["user_email"] = email
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------------------------
# After login
# ---------------------------
@app.route("/home")
@login_required
def home():
    return render_template("home.html")

# ---------------------------
# Profile form (create / view / edit)
# ---------------------------
@app.route("/form", methods=["GET"])
@login_required
def form():
    email = current_email()
    doc = db.collection("profiles").document(email).get()
    profile = doc.to_dict() if doc.exists else None

    # If profile exists and not in edit mode -> readonly
    readonly = False
    if profile and request.args.get("edit") != "1":
        readonly = True

    return render_template("form.html", profile=profile, readonly=readonly)

@app.route("/profile/edit")
@login_required
def profile_edit():
    # Force edit mode on /form
    return redirect(url_for("form", edit="1"))

@app.route("/submit-profile", methods=["POST"])
@login_required
def submit_profile():
    email = current_email()

    profile = {
        "gender": request.form["gender"],
        "education": request.form["education"],
        "category": request.form["category"],
        "income": int(request.form["income"]),
        "state": request.form["state"],
        "dob": request.form["dob"],
        "religion": request.form["religion"],
        "disability": request.form["disability"],
        "course": request.form.get("course", ""),
        "percentage": int(request.form.get("percentage", 0)),
        "submitted_at": datetime.utcnow().isoformat(),
        "email": email,   # keep for convenience
    }
    # Save (doc id = email, so one per user)
    db.collection("profiles").document(email).set(profile)
    return redirect(url_for("results"))

# ---------------------------
# Scholarship results + search/filter + save/apply
# ---------------------------
def profile_or_404(email: str):
    doc = db.collection("profiles").document(email).get()
    if not doc.exists:
        abort(404, description="No profile found. Please complete your profile first.")
    return doc.to_dict()

def is_eligible(s: dict, user: dict) -> bool:
    try:
        gender_ok = (s.get("gender", "Any") == "Any" or s["gender"] == user["gender"])
        edu_ok = (s.get("education", "").lower() == user.get("education", "").lower())
        cat_ok = (s.get("category", "Any").lower() in ["any", user.get("category", "").lower()])
        state_ok = (s.get("state", "All").lower() == "all" or s.get("state", "").lower() == user.get("state", "").lower())
        income_ok = (int(user.get("income", 0)) <= int(s.get("max_income", 99999999)))
        religion_ok = (s.get("religion", "Any") in ["Any", user.get("religion", "")])
        disability_ok = (s.get("disability", "Any") in ["Any", user.get("disability", "")])
        perc_ok = (int(user.get("percentage", 0)) >= int(s.get("min_percentage", 0)))
        return all([gender_ok, edu_ok, cat_ok, state_ok, income_ok, religion_ok, disability_ok, perc_ok])
    except Exception:
        return False

@app.route("/results", methods=["GET"])
@login_required
def results():
    email = current_email()
    profile = profile_or_404(email)

    saved_ids = {
        d.id.split("__", 1)[1]
        for d in db.collection("saved").where("email", "==", email).stream()
        if "__" in d.id
    }
    applied_ids = {
        d.id.split("__", 1)[1]
        for d in db.collection("applied").where("email", "==", email).stream()
        if "__" in d.id
    }

    matched = []
    today = datetime.utcnow()
    for doc in db.collection("scholarships").stream():
        s = doc.to_dict()
        s["id"] = doc.id
        # Do NOT skip saved/applied here (show all)
        try:
            deadline_dt = datetime.strptime(s.get("deadline", "2099-12-31"), "%Y-%m-%d")
            s["is_closing_soon"] = (deadline_dt - today).days <= 7
        except Exception:
            s["is_closing_soon"] = False

        if is_eligible(s, profile):
            matched.append(s)

    # client filters (search / amount)
    q = request.args.get("q", "").strip().lower()
    income_max = request.args.get("income_max", "").strip()
    amount_min = request.args.get("amount_min", "").strip()

    if q:
        matched = [s for s in matched if q in s.get("name", "").lower()]

    if income_max.isdigit():
        income_max_val = int(income_max)
        matched = [s for s in matched if int(s.get("max_income", 0)) <= income_max_val]

    if amount_min.isdigit():
        amt_min_val = int(amount_min)
        matched = [s for s in matched if parse_amount(s.get("amount", "0")) >= amt_min_val]

    return render_template("results.html",
                           scholarships=matched,
                           saved_ids=saved_ids,
                           applied_ids=applied_ids)


@app.post("/save-scholarship")
@login_required
def save_scholarship():
    email = current_email()
    sid = request.form.get("scholarship_id", "")
    if not sid:
        abort(400)
    doc_id = f"{email}__{sid}"
    if not db.collection("saved").document(doc_id).get().exists:
        db.collection("saved").document(doc_id).set({
            "email": email,
            "scholarship_id": sid,
            "saved_at": datetime.utcnow().isoformat(),
        })
    return redirect(url_for("results"))

@app.post("/apply-scholarship")
@login_required
def apply_scholarship():
    email = current_email()
    sid = request.form.get("scholarship_id", "")
    if not sid:
        abort(400)
    doc_id = f"{email}__{sid}"
    if not db.collection("applied").document(doc_id).get().exists:
        db.collection("applied").document(doc_id).set({
            "email": email,
            "scholarship_id": sid,
            "applied_at": datetime.utcnow().isoformat(),
        })
    return redirect(url_for("dashboard"))
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        # Here you would handle password reset logic (send mail, etc.)
        flash("If this email is registered, you will receive reset instructions.", "info")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")

# ---------------------------
# Dashboard
# ---------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    email = current_email()

    # --- Saved / Applied Scholarships ---
    saved_docs = list(db.collection("saved").where("email", "==", email).stream())
    applied_docs = list(db.collection("applied").where("email", "==", email).stream())

    saved_ids = {d.id.split("__", 1)[1] for d in saved_docs if "__" in d.id}
    applied_ids = {d.id.split("__", 1)[1] for d in applied_docs if "__" in d.id}

    saved_schols = []
    applied_schols = []

    for sid in saved_ids:
        sdoc = db.collection("scholarships").document(sid).get()
        if sdoc.exists:
            s = sdoc.to_dict()
            s["id"] = sid
            # Annotate closing soon
            try:
                deadline_dt = datetime.strptime(s.get("deadline", "2099-12-31"), "%Y-%m-%d")
                s["is_closing_soon"] = (deadline_dt - datetime.utcnow()).days <= 7
            except Exception:
                s["is_closing_soon"] = False
            saved_schols.append(s)

    for sid in applied_ids:
        sdoc = db.collection("scholarships").document(sid).get()
        if sdoc.exists:
            s = sdoc.to_dict()
            s["id"] = sid
            # Annotate closing soon
            try:
                deadline_dt = datetime.strptime(s.get("deadline", "2099-12-31"), "%Y-%m-%d")
                s["is_closing_soon"] = (deadline_dt - datetime.utcnow()).days <= 7
            except Exception:
                s["is_closing_soon"] = False
            applied_schols.append(s)

    # --- Latest Profile ---
    profile_doc = db.collection("profiles").document(email).get()
    profile = profile_doc.to_dict() if profile_doc.exists else None

    matched_schols = []
    if profile:
        today = datetime.utcnow()
        for sdoc in db.collection("scholarships").stream():
            s = sdoc.to_dict()
            s["id"] = sdoc.id
            # Skip if already saved or applied
            if s["id"] in saved_ids or s["id"] in applied_ids:
                continue
            # Annotate closing soon
            try:
                deadline_dt = datetime.strptime(s.get("deadline", "2099-12-31"), "%Y-%m-%d")
                s["is_closing_soon"] = (deadline_dt - today).days <= 7
            except Exception:
                s["is_closing_soon"] = False

            if is_eligible(s, profile):
                matched_schols.append(s)

    # --- Deadlines for saved scholarships ---
    deadlined = sum(
        1 for s in saved_schols
        if 0 <= (datetime.strptime(s.get("deadline", "2099-12-31"), "%Y-%m-%d") - datetime.utcnow()).days <= 7
    )

    stats = {
        "total_applied": len(applied_schols),
        "saved_count": len(saved_schols),
        "deadlined": deadlined,
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        saved_scholarships=saved_schols,
        applied_scholarships=applied_schols,
        matched_scholarships=matched_schols
    )

from apscheduler.schedulers.background import BackgroundScheduler
from notify_users import notify_new_or_closing_scholarships

scheduler = BackgroundScheduler()
scheduler.add_job(func=notify_new_or_closing_scholarships, trigger="interval", hours=6)
scheduler.start()


# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
