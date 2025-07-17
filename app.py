from flask import Flask, render_template, request, redirect
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import uuid

# 🔐 Initialize Firebase
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

# 🏠 Home Page
@app.route('/')
def home():
    return render_template('index.html')

# 🧾 User Input Form
@app.route('/form')
def form():
    return render_template('form.html')

# 📩 Handle Form Submission and Save User Profile
@app.route('/submit-profile', methods=['POST'])
def submit_profile():
    user = {
        "gender": request.form['gender'],
        "education": request.form['education'],
        "category": request.form['category'],
        "income": int(request.form['income']),
        "state": request.form['state'],
        "dob": request.form['dob'],
        "religion": request.form['religion'],
        "disability": request.form['disability'],
        "course": request.form['course'],
        "percentage": int(request.form['percentage']),
        "email": request.form['email']
    }

    user["submitted_at"] = datetime.now().isoformat()
    user["profile_id"] = str(uuid.uuid4())  # Unique ID for every submission

    # ✅ Save profile in Firestore under "profiles" collection
    db.collection("profiles").document(user["profile_id"]).set(user)

    return redirect(f"/get-scholarships/{user['email']}")

# 🎓 Scholarships Results Page
@app.route('/get-scholarships/<email>')
def get_scholarships(email):
    category_filter = request.args.get('category', '').lower()
    education_filter = request.args.get('education', '').lower()

    # ✅ Fetch the most recently submitted profile for this email
    profiles_query = db.collection("profiles")\
        .where("email", "==", email)\
        .order_by("submitted_at", direction=firestore.Query.DESCENDING)\
        .limit(1)\
        .stream()
    profiles = [doc.to_dict() for doc in profiles_query]

    if not profiles:
        return "⚠️ No profile found for this email. Please submit the form first.", 404

    profile = profiles[0]  # Get the latest profile only

    # ✅ Load all scholarships from Firestore
    scholarships = [doc.to_dict() for doc in db.collection("scholarships").stream()]
    today = datetime.today()
    matched_scholarships = []

    def is_eligible(s, user):
        return (
            (s.get('gender', 'Any') == "Any" or s['gender'] == user['gender']) and
            (s.get('education', '').lower() == user['education'].lower()) and
            (s.get('category', '').lower() in ['any', user['category'].lower()]) and
            (s.get('state', 'All').lower() == 'all' or s['state'].lower() == user['state'].lower()) and
            (user['income'] <= s.get('max_income', 9999999)) and
            (s.get('religion', 'Any') in ['Any', user['religion']]) and
            (s.get('disability', 'Any') in ['Any', user['disability']]) and
            (user['percentage'] >= s.get('min_percentage', 0))
        )

    for s in scholarships:
        if is_eligible(s, profile):
            try:
                deadline = datetime.strptime(s['deadline'], "%Y-%m-%d")
                s['is_closing_soon'] = (deadline - today).days <= 7
            except:
                s['is_closing_soon'] = False

            # ✅ Apply optional filters from dropdowns
            if (not category_filter or s.get('category', '').lower() == category_filter) and \
               (not education_filter or s.get('education', '').lower() == education_filter):
                matched_scholarships.append(s)

    return render_template("results.html", scholarships=matched_scholarships, email=email)

# 🚀 Run Flask App
if __name__ == '__main__':
    app.run(debug=True)
