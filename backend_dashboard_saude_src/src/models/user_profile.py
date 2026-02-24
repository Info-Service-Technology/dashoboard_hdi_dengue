from datetime import datetime
from src.models.user import db
from sqlalchemy.sql import func

class UserProfile(db.Model):
    __tablename__ = "user_profile"

    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    phone = db.Column(db.String(30), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    about = db.Column(db.Text, nullable=True)

    # Foto (inicialmente via URL)
    avatar_url = db.Column(db.String(255), nullable=True)

    # Tema do usuário: light | dark | system
    theme = db.Column(db.String(20), nullable=False, default="light")

    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "phone": self.phone,
            "location": self.location,
            "about": self.about,
            "avatar_url": self.avatar_url,
            "theme": self.theme,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }