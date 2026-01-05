from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI()

# --- CONFIGURAÇÃO ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. OS SEUS MATERIAIS (INTRODUZA AQUI) ---
# Adicione ou remova linhas aqui para atualizar o catálogo
db_produtos = [
    {"id": 1, "nome": "Tubo PVC 50mm", "stock": 100, "categoria": "Canalização"},
    {"id": 2, "nome": "Cabo UTP Cat6", "stock": 350, "categoria": "Redes"},
    {"id": 3, "nome": "Disjuntor 16A", "stock": 15, "categoria": "Eletricidade"},
    {"id": 4, "nome": "Saco Cimento 25kg", "stock": 40, "categoria": "Construção"},
    {"id": 5, "nome": "Luvas Proteção", "stock": 20, "categoria": "EPI"},
    {"id": 6, "nome": "Lâmpada LED E27", "stock": 50, "categoria": "Iluminação"},
    {"id": 7, "nome": "Fita Isoladora", "stock": 100, "categoria": "Acessórios"},
]

db_pedidos = []

# --- MODELOS ---
class Pedido(BaseModel):
    tecnico: str
    id_produto: int
    qtd: int
    obs: Optional[str] = ""

class AtualizarEstado(BaseModel):
    estado: str

# --- APLICAÇÃO WEB (FRONTEND) ---
html_app = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>App FamaLuz</title>
    <style>
        /* ESTILOS GERAIS */
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; background-color: #f0f2f5; color: #333; }
        .hidden { display: none !important; }
        
        /* ECRÃ DE LOGIN */
        #view-login { display: flex; flex-direction: column; justify-content: center; alignItems: center; height: 100vh; background: linear-gradient(135deg, #007BFF, #0056b3); color: white; }
        .btn-role { width: 80%; padding: 20px; margin: 10px; border: none; border-radius: 12px; font-size: 1.2rem; font-weight: bold; cursor: pointer; transition: transform 0.2s; }
        .btn-tecnico { background: white; color: #007BFF; }
        .btn-escritorio { background: #333; color: white; }
        
        /* ECRÃ TÉCNICO (MOBILE) */
        .header { background: #007BFF; color: white; padding: 15px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }
        .card-produto { background: white; padding: 15px; margin: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; }
        .btn-pedir { background: #007BFF; color: white; border: none; padding: 8px 20px; border-radius: 20px; font-weight: bold; }
        
        /* ECRÃ ESCRITÓRIO (DESKTOP) */
        .table-container { padding: 20px; max-width: 1000px; margin: 0 auto; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #34495e; color: white; }
        
        /* ESTADOS */
        .estado-pendente { color: #f39c12; font-weight: bold; }
        .estado-aprovado { color: #27ae60; font-weight: bold; }
        .estado-recusado { color: #c0392b; font-weight: bold; text-decoration: line-through; }

        /* MODAL */
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000; }
        .modal-content { background: white; padding: 25px; border-radius: 15px; width: 85%; max-width: 350px; }
        input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        .btn-confirmar { background: #28a745; color: white; width: 100%; padding: 12px; border: none; border-radius: 8px; font-size: 1rem; }
        .btn-cancelar { background: #dc3545; color: white; width: 100%; padding: 12px; border: none; border-radius: 8px; margin-top: 10px; }
        
        /* BOTÕES AÇÃO ESCRITÓRIO */
        .btn-acao { padding: 5px 10px; margin-right: 5px; border: none; border-radius: 4px; cursor: pointer; color: white; }
        .btn-ok { background: #27ae60; }
        .btn-no { background: #c0392b; }
    </style>
</head>
<body>

    <div id="view-login">
        <h1>FamaLuz App</h1>
        <p>Quem está a utilizar?</p>
        <button class="btn-role btn-tecnico" onclick="mudarView('tecnico')">👷 Sou Técnico (Rua)</button>
        <button class="btn-role btn-escritorio" onclick="mudarView('escritorio')">🏢 Sou Escritório</button>
    </div>

    <div id="view-tecnico" class="hidden">
        <div class="header">
            <span style="font-weight: bold; font-size: 1.2rem;">Catálogo</span>
            <button onclick="location.reload()" style="background:none; border:none; color:white;">Sair</button>
        </div>
        <div style="padding: 10px;">
            <input type="text" id="searchBox" placeholder="🔍 Pesquisar material..." onkeyup="filtrarProdutos()" style="padding: 12px; width: 100%; border-radius: 20px; border: 1px solid #ddd;">
        </div>
        <div id="lista-produtos" style="padding-bottom: 50px;">
            </div>
    </div>

    <div id="view-escritorio" class="hidden">
        <div class="header" style="background: #34495e;">
            <span>Painel de Gestão</span>
            <button onclick="location.reload()" style="background:none; border:none; color:white;">Sair</button>
        </div>
        <div class="table-container">
            <h2>Pedidos Recentes</h2>
            <table id="tabela-pedidos">
                <thead>
                    <tr>
                        <th>Hora</th>
                        <th>Técnico</th>
                        <th>Produto</th>
                        <th>Qtd</th>
                        <th>Obs</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody id="corpo-tabela"></tbody>
            </table>
        </div>
    </div>

    <div id="modal-pedido" class="hidden modal">
        <div class="modal-content">
            <h3 id="modal-titulo">Produto</h3>
            <label>Quantidade:</label>
            <input type="number" id="modal-qtd" value="1">
            <label>Observações:</label>
            <textarea id="modal-obs" placeholder="Ex: Urgente..."></textarea>
            <button class="btn-confirmar" onclick="enviarPedido()">✅ Enviar Pedido</button>
            <button class="btn-cancelar" onclick="fecharModal()">Cancelar</button>
        </div>
    </div>

    <script>
        let produtosCache = [];
        let produtoSelecionadoId = null;

        // --- NAVEGAÇÃO ---
        function mudarView(tipo) {
            document.getElementById('view-login').classList.add('hidden');
            if (tipo === 'tecnico') {
                document.getElementById('view-tecnico').classList.remove('hidden');
                carregarProdutos();
            } else {
                document.getElementById('view-escritorio').classList.remove('hidden');
                carregarPedidos();
                setInterval(carregarPedidos, 5000); // Atualiza a cada 5s
            }
        }

        // --- LÓGICA DO TÉCNICO ---
        async function carregarProdutos() {
            const res = await fetch('/api/produtos');
            produtosCache = await res.json();
            renderizarProdutos(produtosCache);
        }

        function renderizarProdutos(lista) {
            const container = document.getElementById('lista-produtos');
            container.innerHTML = lista.map(p => `
                <div class="card-produto">
                    <div>
                        <div style="font-weight:bold; font-size:1.1rem;">${p.nome}</div>
                        <div style="color:gray; font-size:0.9rem;">${p.categoria} | Stock: ${p.stock}</div>
                    </div>
                    <button class="btn-pedir" onclick="abrirModal(${p.id}, '${p.nome}')">PEDIR</button>
                </div>
            `).join('');
        }

        function filtrarProdutos() {
            const termo = document.getElementById('searchBox').value.toLowerCase();
            const filtrados = produtosCache.filter(p => p.nome.toLowerCase().includes(termo));
            renderizarProdutos(filtrados);
        }

        function abrirModal(id, nome) {
            produtoSelecionadoId = id;
            document.getElementById('modal-titulo').innerText = nome;
            document.getElementById('modal-pedido').classList.remove('hidden');
        }

        function fecharModal() {
            document.getElementById('modal-pedido').classList.add('hidden');
        }

        async function enviarPedido() {
            const qtd = document.getElementById('modal-qtd').value;
            const obs = document.getElementById('modal-obs').value;
            
            await fetch('/pedir', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    tecnico: "Técnico (Web)", 
                    id_produto: produtoSelecionadoId,
                    qtd: parseInt(qtd),
                    obs: obs
                })
            });
            
            alert('Pedido Enviado!');
            fecharModal();
        }

        // --- LÓGICA DO ESCRITÓRIO ---
        async function carregarPedidos() {
            const res = await fetch('/api/pedidos');
            const pedidos = await res.json();
            
            const tbody = document.getElementById('corpo-tabela');
            tbody.innerHTML = pedidos.slice().reverse().map(p => `
                <tr>
                    <td>${p.data.split(' ')[1]}</td>
                    <td>${p.tecnico}</td>
                    <td>${p.produto}</td>
                    <td>${p.qtd}</td>
                    <td>${p.obs}</td>
                    <td>
                        ${p.status === 'Pendente' ? `
                            <button class="btn-acao btn-ok" onclick="mudarEstado(${p.id}, 'Aprovado')">✔</button>
                            <button class="btn-acao btn-no" onclick="mudarEstado(${p.id}, 'Recusado')">✖</button>
                        ` : `<span class="estado-${p.status.toLowerCase()}">${p.status}</span>`}
                    </td>
                </tr>
            `).join('');
        }

        async function mudarEstado(id, novoEstado) {
            await fetch(`/pedido/${id}/estado`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ estado: novoEstado })
            });
            carregarPedidos();
        }
    </script>
</body>
</html>
"""

# --- ROTAS API ---

@app.get("/", response_class=HTMLResponse)
def home():
    return html_app

@app.get("/api/produtos")
def api_produtos():
    return db_produtos

@app.get("/api/pedidos")
def api_pedidos():
    return db_pedidos

@app.post("/pedir")
def fazer_pedido(pedido: Pedido):
    prod = next((p for p in db_produtos if p["id"] == pedido.id_produto), None)
    if prod:
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
    return {"ok": True}

@app.put("/pedido/{id_pedido}/estado")
def atualizar_estado(id_pedido: int, dados: AtualizarEstado):
    pedido = next((p for p in db_pedidos if p["id"] == id_pedido), None)
    if pedido:
        pedido["status"] = dados.estado
    return {"ok": True}