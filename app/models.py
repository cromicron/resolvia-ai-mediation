from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Enum
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Mediation(db.Model):
    mediation_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    initiator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    other_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable if they can invite later
    timestamp_started = db.Column(db.DateTime, default=datetime.utcnow)
    initiator_conflict_statement = db.Column(db.Text, nullable=True)  # Nullable until submitted
    other_conflict_statement = db.Column(db.Text, nullable=True)  # Nullable until submitted
    initiator_statement_committed = db.Column(db.Boolean, default=False, nullable=False)
    other_statement_committed = db.Column(db.Boolean, default=False, nullable=False)

class MessagePrivate(db.Model):
    mediation_id = db.Column(db.Integer, db.ForeignKey('mediation.mediation_id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    sequence_number = db.Column(db.Integer, primary_key=True)
    role = db.Column(Enum('system', 'user', 'assistant'), nullable=False)  # 'system', 'user', or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class MessagePublic(db.Model):
    mediation_id = db.Column(db.Integer, db.ForeignKey('mediation.mediation_id'), primary_key=True)
    sequence_number = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    role = db.Column(Enum('system', 'user', 'assistant'), nullable=False)  # 'system', 'user', or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Agreement(db.Model):
    agreement_id = db.Column(db.Integer, primary_key=True)
    agreement_title = db.Column(db.Text)
    agreement_statement = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    mediation_id = db.Column(db.Integer, db.ForeignKey('mediation.mediation_id'))
