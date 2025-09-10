from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Configurações
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tarefas.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "troque-esta-chave-por-uma-secreta-e-long"  # MUDE em produção
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120))
    descricao = db.Column(db.String(255))
    status = db.Column(db.String(50), default="pendente")

# --- Rotas estáticas ---
@app.route("/")
def index():
    # Serve o arquivo static/index.html
    return send_from_directory("static", "index.html")

# --- Autenticação ---
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"msg": "username e password são obrigatórios"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "usuário já existe"}), 409
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "usuário criado"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"msg": "username e password são obrigatórios"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Credenciais inválidas"}), 401
    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token)

# --- Rotas protegidas (tarefas) ---
@app.route("/tarefas", methods=["GET"])
@jwt_required()
def listar_tarefas():
    tarefas = Tarefa.query.all()
    lista = [{"id": t.id, "titulo": t.titulo, "descricao": t.descricao, "status": t.status} for t in tarefas]
    return jsonify(lista)

@app.route("/tarefas", methods=["POST"])
@jwt_required()
def criar_tarefa():
    data = request.get_json() or {}
    t = Tarefa(
        titulo=data.get("titulo"),
        descricao=data.get("descricao"),
        status=data.get("status", "pendente")
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"id": t.id, "titulo": t.titulo, "descricao": t.descricao, "status": t.status}), 201

@app.route("/tarefas/<int:id>", methods=["GET"])
@jwt_required()
def obter_tarefa(id):
    t = Tarefa.query.get(id)
    if not t:
        return jsonify({"msg": "Tarefa não encontrada"}), 404
    return jsonify({"id": t.id, "titulo": t.titulo, "descricao": t.descricao, "status": t.status})

@app.route("/tarefas/<int:id>", methods=["PUT"])
@jwt_required()
def atualizar_tarefa(id):
    t = Tarefa.query.get(id)
    if not t:
        return jsonify({"msg": "Tarefa não encontrada"}), 404
    data = request.get_json() or {}
    if "titulo" in data: t.titulo = data["titulo"]
    if "descricao" in data: t.descricao = data["descricao"]
    if "status" in data: t.status = data["status"]
    db.session.commit()
    return jsonify({"id": t.id, "titulo": t.titulo, "descricao": t.descricao, "status": t.status})

@app.route("/tarefas/<int:id>", methods=["DELETE"])
@jwt_required()
def deletar_tarefa(id):
    t = Tarefa.query.get(id)
    if not t:
        return jsonify({"msg": "Tarefa não encontrada"}), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify({"msg": "Tarefa deletada com sucesso"})

# --- Inicializa DB e roda ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
