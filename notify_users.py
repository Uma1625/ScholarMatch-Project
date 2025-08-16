from flask_mail import Mail, Message
from datetime import datetime, timedelta
from app import db, is_eligible  # import your firebase db and helper
import os
# -----------------------------
# Configure Flask-Mail
# -----------------------------
from app import app  # import your Flask app

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),  # your email
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD")   # app password
)
mail = Mail(app)

def send_email(to, subject, body):
    with app.app_context():
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[to])
        msg.body = body
        mail.send(msg)
def notify_new_or_closing_scholarships():
    users = db.collection("users").stream()
    today = datetime.utcnow()
    for user_doc in users:
        user_email = user_doc.id
        profile_doc = db.collection("profiles").document(user_email).get()
        if not profile_doc.exists:
            continue
        profile = profile_doc.to_dict()

        # 1️⃣ New matched scholarships
        matched = []
        for sdoc in db.collection("scholarships").stream():
            s = sdoc.to_dict()
            s["id"] = sdoc.id

            # Check eligibility
            if not is_eligible(s, profile):
                continue

            # Skip if already saved/applied
            saved_applied_ids = {d.id.split("__",1)[1] for d in db.collection("saved").where("email","==",user_email).stream()}
            applied_ids = {d.id.split("__",1)[1] for d in db.collection("applied").where("email","==",user_email).stream()}
            if s["id"] in saved_applied_ids or s["id"] in applied_ids:
                continue

            matched.append(s)

        if matched:
            body = "🎓 New scholarships matching your profile:\n\n"
            for s in matched:
                body += f"{s['name']} - Apply here: {s.get('apply_link', 'No link')}\n"
            send_email(user_email, "New Scholarships Available", body)

        # 2️⃣ Scholarships closing soon (saved or matched)
        closing_soon = []
        for sdoc in db.collection("scholarships").stream():
            s = sdoc.to_dict()
            s["id"] = sdoc.id

            # Only saved or matched
            saved_ids = {d.id.split("__",1)[1] for d in db.collection("saved").where("email","==",user_email).stream()}
            applied_ids = {d.id.split("__",1)[1] for d in db.collection("applied").where("email","==",user_email).stream()}

            if s["id"] not in saved_ids and s["id"] not in applied_ids:
                continue

            try:
                deadline_dt = datetime.strptime(s.get("deadline","2099-12-31"), "%Y-%m-%d")
                days_left = (deadline_dt - today).days
                if 0 <= days_left <= 7:  # closing within 7 days
                    closing_soon.append(s)
            except:
                continue

        if closing_soon:
            body = "⏰ The following scholarships are closing soon:\n\n"
            for s in closing_soon:
                body += f"{s['name']} - Deadline: {s.get('deadline','N/A')} - Apply: {s.get('apply_link','No link')}\n"
            send_email(user_email, "Scholarships Closing Soon", body)
