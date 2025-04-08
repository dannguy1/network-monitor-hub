from .. import db
import datetime
from sqlalchemy.orm import relationship

class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True, nullable=False)
    ip_address = db.Column(db.String(128), unique=True, index=True, nullable=False)
    description = db.Column(db.String(256))
    status = db.Column(db.String(64), default='Unknown') # e.g., Unknown, Online, Offline, Verified, Verification Failed, Rebooting
    control_method = db.Column(db.String(32), default='ssh', nullable=False) # 'ssh' or 'rest'
    last_seen = db.Column(db.DateTime, default=None)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Foreign Key for the associated credential
    credential_id = db.Column(db.Integer, db.ForeignKey('credentials.id'), nullable=True)
    # Relationship (one-to-one Device -> Credential, Credential -> Device is defined in Credential model)
    credential = relationship("Credential", back_populates="device", foreign_keys=[credential_id])

    # Relationship to Log Entries (one-to-many Device -> LogEntry)
    logs = relationship(
        "LogEntry", 
        back_populates="device", 
        lazy='dynamic', 
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        # Serialize the credential using its own to_dict if it exists
        credential_data = self.credential.to_dict() if self.credential else None
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.ip_address,
            'description': self.description,
            'status': self.status,
            'control_method': self.control_method,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'credential_id': self.credential_id,
            'credential': credential_data # Include the serialized credential object
            # 'credential_name': self.credential.name if self.credential else None # REMOVED
        }

    def __repr__(self):
        return f'<Device {self.name} ({self.ip_address})>' 