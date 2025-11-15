import os
import sys
# DON\'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS, cross_origin
from flask_jwt_extended import JWTManager
from src.models.user import db, User
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.health_data import health_data_bp
from src.routes.predictions import predictions_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configurações
app.config['SECRET_KEY'] = 'health-dashboard-secret-key-2025'
app.config['JWT_SECRET_KEY'] = 'jwt-health-dashboard-secret-2025'
app.config['JWT_IDENTITY_CLAIM'] = 'user_id' # Adicionado para especificar o campo de identidade

# CORS para permitir requisições do frontend React
#CORS(app, 
#     origins="*",
#     supports_credentials=True,
#     allow_headers=["Content-Type", "Authorization"],
#     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
CORS(app, 
     origins=["http://localhost:5173"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])


# JWT Manager
jwt = JWTManager(app)

# Configuração do banco de dados - usando SQLite por enquanto, pode ser migrado para MySQL
#app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:123456@172.22.1.2:3306/dashboard_saude"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar banco de dados
db.init_app(app)
with app.app_context():
    db.create_all()

# Registrar blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(health_data_bp, url_prefix='/api/health')
app.register_blueprint(predictions_bp, url_prefix='/api/predictions')

# Rota de teste para verificar se a API está funcionando
@app.route('/api/test')
def test():
    return jsonify({"message": "API funcionando!", "status": "ok"})

@app.route('/', defaults={'path': ''}) 
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "Frontend not built yet", 404

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    print("📊 Dashboard de Análise Preditiva em Saúde")
    print("🔗 API disponível em: http://localhost:5000")
    print("🧪 Teste a API em: http://localhost:5000/api/test")
    with app.app_context():
        if not User.query.filter_by(email='admin@example.com').first():
            admin_user = User(
                first_name='Admin',
                last_name='User',
                email='admin@example.com',
                role='admin'
            )
            admin_user.set_password('admin')
            db.session.add(admin_user)
            db.session.commit()
            print('Usuário admin padrão criado.')
    app.run(host='0.0.0.0', port=5000, debug=True)
