from src.models.user import db

class Tenant(db.Model):
    __tablename__ = "tenants"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    scope_type = db.Column(db.Enum("BR", "UF", "MUN"), nullable=False, default="BR")
    scope_value = db.Column(db.String(64), nullable=False, default="all")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

class UserTenant(db.Model):
    __tablename__ = "user_tenants"

    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    tenant_id = db.Column(db.BigInteger, db.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)