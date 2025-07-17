import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta, timezone
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Step 1: Initialize Firebase
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ✅ Step 2: Initialize SendGrid
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")  # Replace this
SENDER_EMAIL = "umabharathimothukuri25@gmail.com"

sg = SendGridAPIClient(SENDGRID_API_KEY)

# ✅ Step 3: Get scholarships added in last 24 hours
cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

scholarships = db.collection("scholarships")\
    .where("created_at", ">", cutoff.isoformat())\
    .stream()

new_scholarships = [s.to_dict() for s in scholarships]

# ✅ Step 4: Get all user profiles
users = [doc.to_dict() for doc in db.collection("profiles").stream()]

# ✅ Step 5: Check matches and send emails
for scholarship in new_scholarships:
    for user in users:
        match = (
            (scholarship['gender'] == "Any" or scholarship['gender'] == user['gender']) and
            (scholarship['education'] == user['education']) and
            (scholarship['category'].lower() == user['category'].lower()) and
            (scholarship['state'].lower() in ['all', user['state'].lower()]) and
            (user['income'] <= scholarship['max_income']) and
            (scholarship['religion'] in ['Any', user['religion']]) and
            (scholarship['disability'] in ['Any', user['disability']]) and
            (user['percentage'] >= scholarship.get('min_percentage', 0))
        )
        if match:
            message = Mail(
                from_email=SENDER_EMAIL,
                to_emails=user['email'],
                subject=f"🎓 New Scholarship: {scholarship['name']}",
                html_content=f"""
                    <p>Hi {user['email']},</p>
                    <p>A new scholarship <strong>{scholarship['name']}</strong> matches your profile!</p>
                    <p><strong>Amount:</strong> {scholarship['amount']}</p>
                    <p><strong>Deadline:</strong> {scholarship['deadline']}</p>
                    <p><a href="{scholarship['apply_link']}">Apply Now</a></p>
                    <p>– ScholarMatch</p>
                """
            )
            try:
                sg.send(message)
                print(f"✅ Email sent to {user['email']}")
            except Exception as e:
                print(f"❌ Failed for {user['email']}: {e}")
