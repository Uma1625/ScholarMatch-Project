from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps

def init_routes(app, db_firestore, mail):
    # ---------------- Helpers ----------------
    def login_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_email" not in session:
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapper

    def current_email():
        return session.get("user_email")

    def parse_amount(amount_str):
        if not amount_str:
            return 0
        digits = ''.join(filter(str.isdigit, str(amount_str)))
        return int(digits) if digits else 0

    # ---------------- Routes ----------------
    @app.route("/")
    def index():
        if "user_email" in session:
            return redirect(url_for("home"))
        return render_template("index.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "GET":
            return render_template("signup.html")
        email = request.form.get("email").lower().strip()
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        if password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for("signup"))
        user_doc = db_firestore.collection("users").document(email).get()
        if user_doc.exists:
            flash("Email already exists", "error")
            return redirect(url_for("login"))
        db_firestore.collection("users").document(email).set({
            "email": email,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.utcnow().isoformat()
        })
        session["user_email"] = email
        return redirect(url_for("home"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html")
        email = request.form.get("email").lower().strip()
        password = request.form.get("password")
        user_doc = db_firestore.collection("users").document(email).get()
        if not user_doc.exists or not check_password_hash(user_doc.to_dict().get("password_hash",""), password):
            flash("Invalid email or password", "error")
            return redirect(url_for("login"))
        session["user_email"] = email
        return redirect(url_for("home"))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/home")
    @login_required
    def home():
        return render_template("home.html")

    # ---------------- Dashboard example ----------------
    @app.route("/dashboard")
    @login_required
    def dashboard():
        email = current_email()
        saved_docs = list(db_firestore.collection("saved").where("email", "==", email).stream())
        applied_docs = list(db_firestore.collection("applied").where("email", "==", email).stream())
        stats = {
            "saved_count": len(saved_docs),
            "applied_count": len(applied_docs)
        }
        return render_template("dashboard.html", stats=stats)

    # ---------------- Notifications ----------------
    def send_closing_soon_notifications():
        users = db_firestore.collection("users").stream()
        today = datetime.utcnow()
        for u in users:
            email = u.id
            saved_docs = db_firestore.collection("saved").where("email","==",email).stream()
            soon = []
            for s_doc in saved_docs:
                s = db_firestore.collection("scholarships").document(s_doc.id.split("__")[1]).get().to_dict()
                try:
                    deadline = datetime.strptime(s.get("deadline","2099-12-31"), "%Y-%m-%d")
                    if 0 <= (deadline - today).days <= 3:
                        soon.append(s.get("name"))
                except:
                    continue
            if soon:
                try:
                    from flask_mail import Message
                    msg = Message("Scholarships Closing Soon",
                                  sender=app.config['MAIL_USERNAME'],
                                  recipients=[email])
                    msg.body = "Closing soon:\n" + "\n".join(soon)
                    mail.send(msg)
                except Exception as e:
                    print(f"Mail error: {e}")
