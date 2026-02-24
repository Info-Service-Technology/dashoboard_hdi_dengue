# src/routes/uploads.py
import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from src.models.user import db
from src.models.user_profile import UserProfile

uploads_bp = Blueprint("uploads_bp", __name__)

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}
MAX_SIZE_MB = 3

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

@uploads_bp.post("/account/avatar")
@jwt_required()
def upload_avatar():
    user_id = get_jwt_identity()

    if "file" not in request.files:
        return jsonify({"error": "Arquivo não enviado (campo 'file')"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "Arquivo inválido"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Formato inválido. Use png/jpg/jpeg/webp"}), 400

    # valida tamanho (lê stream todo pra checar)
    file_bytes = file.read()
    file.seek(0)
    if len(file_bytes) > MAX_SIZE_MB * 1024 * 1024:
        return jsonify({"error": f"Arquivo muito grande. Máx {MAX_SIZE_MB}MB"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")

    # pasta física
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    save_path = os.path.join(upload_dir, filename)
    file.save(save_path)

    # URL pública (Flask serve /static/*)
    public_url = f"/static/uploads/avatars/{filename}"

    profile = UserProfile.query.get(user_id)
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)

    profile.avatar_url = public_url
    db.session.commit()

    return jsonify({"avatar_url": public_url}), 200