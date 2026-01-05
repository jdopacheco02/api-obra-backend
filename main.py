from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse # <--- Importante para mostrar o site
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI()

# --- CONFIGURAÇÃO DE SEGURANÇA (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DADOS (Simulação) ---
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
    obs: Optional[str] = ""

# --- O CÓDIGO DO SITE (HTML) ---
# Isto é o visual que vai aparecer no escritório
html_dashboard = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel FamaLuz</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; padding: 20px; background-color: #f4f6f8; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #3498db; color: white; }
        tr:hover { background-color: #f1f1f1; }
        .tag { padding: 4px 8px; border-radius: 12px; font-size: 0.85em; font-weight: bold; background: #e2e6ea; color: #333; }
        .pendente { background-color: #f1c40f; color: #fff; text-shadow: 0px 0px 2px black; }
        .urgente { color: #e74c3c; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📦 Pedidos em Tempo Real</h1>
        <p>A aguardar sincronização com a App...</p>
        <table id="tabela">
            <thead>
                <tr>
                    <th>Hora</th>
                    <th>Técnico</th>
                    <th>Material</th>
                    <th>Qtd</th>
                    <th>Obs</th>
                    <th>Estado</th>
                </tr>
            </thead>
            <tbody id="corpo-tabela">
                </tbody>
        </table>
    </div>

    <script>
        // Função que vai buscar os dados ao próprio site
        async function atualizar() {
            try {
                // Vai buscar os dados à API (a rota /api/pedidos que criamos abaixo)
                const response = await fetch('/api/pedidos'); 
                const pedidos = await response.json();
                
                const html = pedidos.map(p => `
                    <tr>
                        <td>${p.data.split(' ')[1]}</td>
                        <td>${p.tecnico}</td>
                        <td><b>${p.produto}</b></td>
                        <td>${p.qtd}</td>
                        <td class="${p.obs.toLowerCase().includes('urgente') ? 'urgente' : ''}">${p.obs}</td>
                        <td><span class="tag pendente">${p.status}</span></td>
                    </tr>
                `).join('');
                
                document.getElementById('corpo-tabela').innerHTML = html;
            } catch (err) {
                console.error("Erro ao atualizar");
            }
        }
        
        // Atualiza a cada 5 segundos
        setInterval(atualizar, 5000);
        atualizar();
    </script>
</body>
</html>
"""

# --- ROTAS DA API ---

# Rota Principal (Onde antes dava "Not Found", agora mostra o Dashboard)
@app.get("/", response_class=HTMLResponse)
def home():
    return html_dashboard

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
    return {"sucesso": True}

# Rota auxiliar para o Dashboard ir buscar os dados (JSON)
@app.get("/api/pedidos")
def api_pedidos():
    return db_pedidos