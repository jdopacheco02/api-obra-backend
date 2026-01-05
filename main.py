from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # <--- NOVO IMPORTE
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI()

# --- CONFIGURAÇÃO DE SEGURANÇA (CORS) ---
# Isto permite que a App (Web ou Mobile) fale com o Python sem bloqueios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens (para teste)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DADOS ---
db_produtos = [
    {"id": 1, "nome": "Tubo PVC 50mm", "stock": 100, "categoria": "Canalização"},
    {"id": 2, "nome": "Cabo UTP Cat6", "stock": 350, "categoria": "Redes"},
    {"id": 3, "nome": "Disjuntor 16A", "stock": 15, "categoria": "Eletricidade"},
    {"id": 4, "nome": "Saco Cimento 25kg", "stock": 40, "categoria": "Construção"},
    {"id": 5, "nome": "Luvas Proteção", "stock": 20, "categoria": "EPI"},
]
db_pedidos = []

# --- MODELOS ---
class Produto(BaseModel):
    id: int
    nome: str
    stock: int
    categoria: str

class Pedido(BaseModel):
    tecnico: str
    id_produto: int
    qtd: int
    obs: Optional[str] = "" # <--- NOVO CAMPO (Notas)

# --- ROTAS ---
@app.get("/produtos", response_model=List[Produto])
def ver_produtos():
    return db_produtos

@app.post("/pedir")
def fazer_pedido(pedido: Pedido):
    prod = next((p for p in db_produtos if p["id"] == pedido.id_produto), None)
    if not prod:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    novo_pedido = {
        "id": len(db_pedidos) + 1,
        "tecnico": pedido.tecnico,
        "produto": prod["nome"],
        "qtd": pedido.qtd,
        "obs": pedido.obs,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "Pendente"
    }
    db_pedidos.append(novo_pedido)
    print(f"NOVO PEDIDO: {novo_pedido}") # Mostra no terminal
    return {"sucesso": True}

@app.get("/dashboard")
def dashboard():
    return db_pedidos