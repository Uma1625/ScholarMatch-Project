import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
from dotenv import load_dotenv

# ✅ Initialize Firebase
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
load_dotenv()
# ✅ SendGrid Configuration
SENDGRID_API_KEY =  os.getenv("SENDGRID_API_KEY")  # Replace with your key
SENDER_EMAIL = "umabharathimothukuri25@gmail.com"  # Your verified sender

sg = SendGridAPIClient(SENDGRID_API_KEY)

# ✅ Fetch all scholarships
scholarships = db.collection("scholarships").stream()
scholarships = [s.to_dict() for s in scholarships]

# ✅ Target deadlines (in days)
days_to_check = [10, 5, 1]
today = datetime.today().date()

# ✅ Fetch all user profiles
users = [doc.to_dict() for doc in db.collection("profiles").stream()]

# ✅ Loop over scholarships
for s in scholarships:
    try:
        deadline = datetime.strptime(s['deadline'], "%Y-%m-%d").date()
        days_left = (deadline - today).days

        if days_left in days_to_check:
            for user in users:
                is_match = (
                    (s['gender'] == "Any" or s['gender'] == user['gender']) and
                    (s['education'] == user['education']) and
                    (s['category'].lower() == user['category'].lower()) and
                    (s['state'].lower() in ['all', user['state'].lower()]) and
                    (user['income'] <= s['max_income']) and
                    (s['religion'] in ['Any', user['religion']]) and
                    (s['disability'] in ['Any', user['disability']]) and
                    (user['percentage'] >= s.get('min_percentage', 0))
                )

                if is_match:
                    message = Mail(
                        from_email=SENDER_EMAIL,
                        to_emails=user['email'],
                        subject=f"⏰ Scholarship Closing Soon: {s['name']}",
                        html_content=f"""
                            <p>Hello {user['email']},</p>
                            <p>The scholarship <strong>{s['name']}</strong> is closing in <strong>{days_left} day(s)</strong>.</p>
                            <p><strong>Amount:</strong> {s['amount']}</p>
                            <p><strong>Deadline:</strong> {s['deadline']}</p>
                            <p><a href="{s['apply_link']}">Apply Now</a></p>
                            <br><p>Best wishes,<br>ScholarMatch Team</p>
                        """
                    )
                    sg.send(message)
                    print(f"✅ Email sent to {user['email']} for {s['name']} (Deadline in {days_left} days)")
    except Exception as e:
        print(f"❌ Error processing scholarship {s.get('name')}: {e}")
