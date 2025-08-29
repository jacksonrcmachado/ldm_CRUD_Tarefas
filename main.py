from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os


# --- Configuração do Banco ---
DATABASE_URL = "sqlite:///./tarefas.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Modelo SQLAlchemy ---
class TarefaModel(Base):
    __tablename__ = "tarefas"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    descricao = Column(String)
    status = Column(String, default="pendente")  # pendente ou concluída

Base.metadata.create_all(bind=engine)

# --- Modelo Pydantic ---
class Tarefa(BaseModel):
    id: int
    titulo: str
    descricao: str
    status: Optional[str] = "pendente"
    
class Config:
    orm_mode = True

class TarefaUpdate(BaseModel):
    titulo: Optional[str]
    descricao: Optional[str]
    status: Optional[str]

# --- Criação da API ---
app = FastAPI(title="API de Tarefas", version="1.0")

# Monta a pasta 'static' para servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Rota raiz que entrega o index.html
@app.get("/")
def read_root():
    return FileResponse(os.path.join("static", "index.html"))

# --- Dependência para acessar o DB ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Rotas CRUD ---
@app.post("/tarefas", response_model=Tarefa)
def criar_tarefa(tarefa: Tarefa):
    db = next(get_db())
    db_tarefa = TarefaModel(**tarefa.model_dump())
    db.add(db_tarefa)
    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa

@app.get("/tarefas", response_model=List[Tarefa])
def listar_tarefas():
    db = next(get_db())
    tarefas = db.query(TarefaModel).all()
    return tarefas

@app.get("/tarefas/{id}", response_model=Tarefa)
def obter_tarefa(id: int):
    db = next(get_db())
    tarefa = db.query(TarefaModel).filter(TarefaModel.id == id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return tarefa

@app.put("/tarefas/{id}", response_model=Tarefa)
def atualizar_tarefa(id: int, tarefa: TarefaUpdate):
    db = next(get_db())
    db_tarefa = db.query(TarefaModel).filter(TarefaModel.id == id).first()
    if not db_tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    for key, value in tarefa.dict(exclude_unset=True).items():
        setattr(db_tarefa, key, value)
    
    db.commit()
    db.refresh(db_tarefa)
    return db_tarefa

@app.delete("/tarefas/{id}")
def deletar_tarefa(id: int):
    db = next(get_db())
    db_tarefa = db.query(TarefaModel).filter(TarefaModel.id == id).first()
    if not db_tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    db.delete(db_tarefa)
    db.commit()
    return {"detail": "Tarefa deletada com sucesso"}
