# 🎓 ScholarMatch – Smart Scholarship Finder & Eligibility Checker

ScholarMatch is a full-stack web application that matches students with scholarships based on their eligibility. Users submit a profile form, and the system filters scholarships from a database and notifies users via email.

## ✨ Features

- 🔍 **Profile-Based Matching** – Matches scholarships based on gender, category, income, education, state, disability, and more.
- 📩 **Email Notifications** – Sends emails when new scholarships are added or when closing deadlines are near (via SendGrid).
- 🔄 **Multiple Submissions Support** – Only the latest user profile is used for matching.
- 📦 **Firebase Firestore Backend** – Stores all profiles and scholarships securely.
- 📊 **Scholarship Results Page** – Shows filtered, closing-soon tagged scholarships with search and filters.

## 🧰 Technologies Used

- 🔥 Firebase (Firestore)
- 🐍 Python (Flask)
- ✉️ SendGrid Email API
- 🌐 HTML, Tailwind CSS
- ☁️ Hosting via Flask locally

## 🚀 How to Run Locally

1. **Clone the repo**
```bash
git clone https://github.com/uma1625/Scholarmatch-Project.git
cd scholarmatch
