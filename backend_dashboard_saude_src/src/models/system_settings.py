from datetime import datetime
from src.models.user import db

class SystemSettings(db.Model):
    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True, default=1)

    app_name = db.Column(db.String(120), nullable=False, default="Dashboard Saúde")
    default_language = db.Column(db.String(10), nullable=False, default="pt-BR")
    timezone = db.Column(db.String(64), nullable=False, default="America/Sao_Paulo")

    enable_notifications = db.Column(db.Boolean, nullable=False, default=True)
    enable_audit_log = db.Column(db.Boolean, nullable=False, default=True)

    data_refresh_minutes = db.Column(db.Integer, nullable=False, default=15)
    maps_default_zoom = db.Column(db.Integer, nullable=False, default=6)

    # Tema global padrão (opcional)
    theme_default = db.Column(db.String(20), nullable=False, default="light")

    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "app_name": self.app_name,
            "default_language": self.default_language,
            "timezone": self.timezone,
            "enable_notifications": self.enable_notifications,
            "enable_audit_log": self.enable_audit_log,
            "data_refresh_minutes": self.data_refresh_minutes,
            "maps_default_zoom": self.maps_default_zoom,
            "theme_default": self.theme_default,
            "updated_by_user_id": self.updated_by_user_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }