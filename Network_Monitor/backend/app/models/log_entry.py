from .. import db
import datetime
from sqlalchemy.dialects.sqlite import JSON # Or PostgreSQL JSONB
# from sqlalchemy.dialects.postgresql import JSONB

class LogEntry(db.Model):
    __tablename__ = 'log_entries'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False, index=True)
    device_ip = db.Column(db.String(45), nullable=False, index=True) # Store denormalized IP for faster filtering

    timestamp = db.Column(db.DateTime, nullable=False, index=True, default=datetime.datetime.utcnow)
    log_level = db.Column(db.String(50), nullable=True, index=True)
    process_name = db.Column(db.String(128), nullable=True, index=True)
    message = db.Column(db.Text, nullable=False)
    raw_message = db.Column(db.Text, nullable=True) # Store the original if needed

    # Structured data extracted during reformatting
    structured_data = db.Column(JSON, nullable=True)

    # AI Processing Status
    pushed_to_ai = db.Column(db.Boolean, default=False, index=True)
    pushed_at = db.Column(db.DateTime, nullable=True)
    push_attempts = db.Column(db.Integer, default=0)
    last_push_error = db.Column(db.Text, nullable=True)

    # Relationship back to Device
    device = db.relationship('Device', back_populates='logs')

    def __repr__(self):
        return f'<LogEntry {self.id} from {self.device_ip} at {self.timestamp}>'

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_ip': self.device_ip,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'log_level': self.log_level,
            'process_name': self.process_name,
            'message': self.message,
            'structured_data': self.structured_data,
            'pushed_to_ai': self.pushed_to_ai,
            'pushed_at': self.pushed_at.isoformat() + 'Z' if self.pushed_at else None,
        } 