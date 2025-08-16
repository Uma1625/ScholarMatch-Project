from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_details = db.Column(db.Text)
    scholarships_saved = db.relationship('Scholarship', secondary='saved_scholarships', backref='saved_by')

class Scholarship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.DateTime, nullable=False)
    eligibility_criteria = db.Column(db.Text)

# Association table for saved scholarships
saved_scholarships = db.Table('saved_scholarships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('scholarship_id', db.Integer, db.ForeignKey('scholarship.id'), primary_key=True)
)
