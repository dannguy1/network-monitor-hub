import os
from .. import db
from cryptography.fernet import Fernet
from flask import current_app
import datetime

class Credential(db.Model):
    __tablename__ = 'credentials'
    id = db.Column(db.Integer, primary_key=True)
    # name = db.Column(db.String(128), nullable=False, unique=True, index=True) # REMOVED
    ssh_username = db.Column(db.String(128), nullable=False)
    # Store encrypted password and private key
    encrypted_password = db.Column(db.LargeBinary, nullable=True)
    encrypted_private_key = db.Column(db.LargeBinary, nullable=True)
    # Indicate type ('password' or 'key')
    auth_type = db.Column(db.String(10), nullable=False, default='password') # 'password' or 'key'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationship back to Device (One-to-One for now)
    device = db.relationship('Device', back_populates='credential', uselist=False)

    @staticmethod
    def _get_fernet():
        key = current_app.config.get('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY not configured in application.")
        return Fernet(key.encode('utf-8'))

    @property
    def password(self):
        if not self.encrypted_password:
            return None
        try:
            f = self._get_fernet()
            decrypted = f.decrypt(self.encrypted_password)
            return decrypted.decode('utf-8')
        except Exception as e:
            current_app.logger.error(f"Failed to decrypt password for credential {self.id}: {e}")
            return "<DECRYPTION_ERROR>"

    @password.setter
    def password(self, plaintext_password):
        if plaintext_password:
            f = self._get_fernet()
            self.encrypted_password = f.encrypt(plaintext_password.encode('utf-8'))
            self.auth_type = 'password'
            self.encrypted_private_key = None # Clear key if setting password
        else:
            self.encrypted_password = None

    @property
    def private_key(self):
        if not self.encrypted_private_key:
            return None
        try:
            f = self._get_fernet()
            decrypted = f.decrypt(self.encrypted_private_key)
            return decrypted.decode('utf-8')
        except Exception as e:
            current_app.logger.error(f"Failed to decrypt private key for credential {self.id}: {e}")
            return "<DECRYPTION_ERROR>"

    @private_key.setter
    def private_key(self, plaintext_key):
        if plaintext_key:
            f = self._get_fernet()
            self.encrypted_private_key = f.encrypt(plaintext_key.encode('utf-8'))
            self.auth_type = 'key'
            self.encrypted_password = None # Clear password if setting key
        else:
            self.encrypted_private_key = None

    def __repr__(self):
        return f'<Credential ID: {self.id} (User: {self.ssh_username}, Type: {self.auth_type})>'

    # Exclude sensitive decrypted fields from default dict representation
    def to_dict(self):
        return {
            'id': self.id,
            # 'name': self.name, # REMOVED
            'ssh_username': self.ssh_username,
            'auth_type': self.auth_type,
            'has_password': self.encrypted_password is not None,
            'has_private_key': self.encrypted_private_key is not None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
            'device_id': self.device.id if self.device else None
        } 