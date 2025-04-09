from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .. import db, login_manager # Import login_manager
import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    # Increase length to accommodate modern hashes (e.g., scrypt)
    password_hash = db.Column(db.String(256))
    # Add other user fields if needed (email, name, roles etc.)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# Flask-Login user loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id)) 