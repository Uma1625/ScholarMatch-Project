import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

cred = credentials.Certificate("firebase-key.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = "umabharathimothukuri25@gmail.com"
sg = SendGridAPIClient(SENDGRID_API_KEY)

schols = [s.to_dict() | {"id": s.id} for s in db.collection("scholarships").stream()]
profiles = {p.id: p.to_dict() for p in db.collection("profiles").stream()}   # key = email
users = {u.id: u.to_dict() for u in db.collection("users").stream()}         # key = email

days_to_check = [10, 5, 1]
today = datetime.today().date()

def eligible(s, u):
    return (
        (s.get('gender','Any') == "Any" or s['gender'] == u['gender']) and
        (s.get('education','').lower() == u.get('education','').lower()) and
        (s.get('category','Any').lower() in ['any', u.get('category','').lower()]) and
        (s.get('state','All').lower() in ['all', u.get('state','').lower()]) and
        (int(u.get('income', 0)) <= int(s.get('max_income', 99999999))) and
        (s.get('religion','Any') in ['Any', u.get('religion','')]) and
        (s.get('disability','Any') in ['Any', u.get('disability','')]) and
        (int(u.get('percentage', 0)) >= int(s.get('min_percentage', 0)))
    )

for s in schols:
    try:
        d = datetime.strptime(s['deadline'], "%Y-%m-%d").date()
        days_left = (d - today).days
        if days_left in days_to_check:
            for email, prof in profiles.items():
                if eligible(s, prof):
                    user = users.get(email)
                    if not user: 
                        continue
                    msg = Mail(
                        from_email=SENDER_EMAIL,
                        to_emails=email,
                        subject=f"⏰ Scholarship Closing Soon: {s['name']}",
                        html_content=f"""
                        <p>Hello {email},</p>
                        <p>The scholarship <strong>{s['name']}</strong> is closing in <strong>{days_left} day(s)</strong>.</p>
                        <p><strong>Amount:</strong> {s['amount']}</p>
                        <p><strong>Deadline:</strong> {s['deadline']}</p>
                        <p><a href="{s.get('apply_link','#')}">Apply Now</a></p>
                        """
                    )
                    sg.send(msg)
                    print(f"Sent to {email}")
    except Exception as e:
        print("Error:", e)
