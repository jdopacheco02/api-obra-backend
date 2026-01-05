from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fpdf import FPDF
from typing import List, Optional
import io
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAÇÃO: LISTAS DE VERIFICAÇÃO ---
# Adicione ou altere as perguntas aqui. A ordem aqui será a mesma do PDF.

ITENS_GAS = [
    "Verificação do estado da central e indicadores luminosos",
    "Verificação do estado das baterias (tensão e carga)",
    "Ensaio de detetores com gás padrão/calibração",
    "Verificação da atuação das eletroválvulas de corte",
    "Verificação do sistema de interbloqueio (ventilação)",
    "Verificação da sinalização ótica e acústica",
    "Estado geral das tubagens e cablagens visíveis",
    "Limpeza geral dos equipamentos"
]

ITENS_INCENDIO = [
    "Teste de detetores",
    "Teste de sirenes"
    # Adicione os itens de incêndio aqui depois
]

ITENS_ELETRICO = [
    "Quadro Geral",
    "Transformador"
    # Adicione os itens elétricos aqui depois
]

# --- CLASSE PARA GERAR O PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        # Se tiver logotipo: self.image('logo.png', 10, 8, 33)
        self.cell(0, 10, 'Relatório Técnico de Manutenção', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def desenhar_tabela_verificacao(self, itens, respostas):
        # Cabeçalho da Tabela
        self.set_font("Arial", 'B', 10)
        self.set_fill_color(240, 240, 240)
        self.cell(110, 8, "Ação / Parâmetro", 1, 0, 'L', True)
        self.cell(20, 8, "V", 1, 0, 'C', True)
        self.cell(20, 8, "NA", 1, 0, 'C', True)
        self.cell(20, 8, "OBS", 1, 1, 'C', True)

        # Linhas
        self.set_font("Arial", size=9)
        for i, item in enumerate(itens):
            # Tenta ir buscar a resposta (V, NA ou OBS). Se não houver, fica vazio.
            resp = respostas.get(f"check_{i}", "")
            
            # Altura da linha dinâmica se o texto for grande
            x_start = self.get_x()
            y_start = self.get_y()
            
            # Coluna Texto
            self.multi_cell(110, 8, item, 1)
            
            # Posição após multi_cell
            y_end = self.get_y()
            altura_linha = y_end - y_start
            
            # Voltar ao topo da linha para desenhar as caixas das cruzes
            self.set_xy(x_start + 110, y_start)
            
            # Função auxiliar para desenhar o X
            def desenhar_x(valor_esperado):
                texto = "X" if resp == valor_esperado else ""
                # Se for OBS, pomos a negrito
                if resp == "OBS" and valor_esperado == "OBS":
                    self.set_font("Arial", 'B', 9)
                self.cell(20, altura_linha, texto, 1, 0, 'C')
                self.set_font("Arial", size=9) # Reset font

            desenhar_x("V")
            desenhar_x("NA")
            desenhar_x("OBS")
            
            self.ln() # Nova linha
            # Garantir que o cursor desce o correto (caso o multi_cell tenha quebrado linha)
            self.set_y(y_end)

# --- FUNÇÃO PRINCIPAL DE CRIAÇÃO DO PDF ---
def gerar_pdf_final(dados: dict, imagens: list):
    pdf = PDF()
    pdf.add_page()
    
    # 1. TÍTULO E DADOS GERAIS
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(230, 230, 230)
    
    titulo = "Relatório Técnico"
    if dados.get('tipo_relatorio') == 'gas':
        titulo = "Manutenção de Deteção de Gás e CO"
    elif dados.get('tipo_relatorio') == 'incendio':
        titulo = "Manutenção de Sistema de Incêndio"
    elif dados.get('tipo_relatorio') == 'eletrico':
        titulo = "Vistoria Instalações Elétricas / PT"

    pdf.cell(0, 12, titulo, 0, 1, 'C', True)
    pdf.ln(5)

    # 2. DADOS DO CABEÇALHO (Técnico, Cliente, etc.)
    pdf.set_font("Arial", size=10)
    
    # Função auxiliar para linhas de dados
    def linha_dado(label, valor):
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 7, label, 0, 0)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 7, str(valor), 0, 1)

    linha_dado("Técnico:", dados.get('tecnico', ''))
    linha_dado("Cliente:", dados.get('cliente', ''))
    linha_dado("Data:", dados.get('data_relatorio', ''))
    
    # Campos específicos de Gás
    if dados.get('tipo_relatorio') == 'gas':
        pdf.ln(2)
        linha_dado("Periodicidade:", dados.get('periodicidade', '').upper())
        linha_dado("Instalação:", dados.get('instalacao', ''))
        linha_dado("Localização:", dados.get('localizacao', ''))
        linha_dado("Tipo Sistema:", dados.get('tipo_sistema', '').replace('_', ' ').title())

    pdf.ln(5)

    # 3. TABELA DE VERIFICAÇÃO
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Ações de Verificação:", 0, 1)
    
    if dados.get('tipo_relatorio') == 'gas':
        pdf.desenhar_tabela_verificacao(ITENS_GAS, dados)
    elif dados.get('tipo_relatorio') == 'incendio':
        pdf.desenhar_tabela_verificacao(ITENS_INCENDIO, dados)
    elif dados.get('tipo_relatorio') == 'eletrico':
        pdf.desenhar_tabela_verificacao(ITENS_ELETRICO, dados)

    pdf.ln(5)

    # 4. OBSERVAÇÕES
    obs = dados.get('obs', '')
    if obs:
        pdf.set_fill_color(255, 250, 240) # Fundo amarelado leve
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "Observações Gerais:", 1, 1, 'L', True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, obs, 1)
        pdf.ln(5)

    # 5. FOTOS
    if imagens:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Registo Fotográfico:", 0, 1)
        
        y_pos = 30
        for img_bytes in imagens:
            if y_pos > 200: # Nova página se chegar ao fundo
                pdf.add_page()
                y_pos = 20
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
                    temp.write(img_bytes)
                    temp_path = temp.name
                
                pdf.image(temp_path, x=40, y=y_pos, w=130)
                y_pos += 100 
            except Exception:
                pass

    return pdf.output(dest='S')


# --- FRONTEND (HTML) ---
# Aqui geramos o HTML dinamicamente com base nas listas Python
def gerar_html_gas_checks():
    html = ""
    for i, item in enumerate(ITENS_GAS):
        html += f"""
        <tr>
            <td>{item}</td>
            <td class="col-check"><input type="radio" name="check_{i}" value="V"></td>
            <td class="col-check"><input type="radio" name="check_{i}" value="NA"></td>
            <td class="col-check"><input type="radio" name="check_{i}" value="OBS"></td>
        </tr>
        """
    return html

html_app = f"""
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatórios FamaLuz</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f4f9; padding: 15px; }}
        .container {{ max-width: 700px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #2c3e50; font-size: 1.5rem; }}
        
        .grupo-input {{ margin-bottom: 15px; }}
        label {{ display: block; font-weight: bold; margin-bottom: 5px; color: #555; }}
        input[type="text"], input[type="date"], select, textarea {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }}
        
        .input-estilo {{ background-color: #e8f0fe; border-color: #007BFF; color: #007BFF; font-weight: bold; }}
        .hidden {{ display: none; }}

        /* Tabela de Verificação */
        .tabela-verificacao {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; }}
        .tabela-verificacao th, .tabela-verificacao td {{ border: 1px solid #eee; padding: 8px; font-size: 0.9rem; }}
        .tabela-verificacao th {{ background-color: #f8f9fa; text-align: center; }}
        .col-check {{ text-align: center; width: 40px; }}
        .tabela-verificacao input[type="radio"] {{ width: 20px; height: 20px; accent-color: #007BFF; }}
        
        .btn-submit {{ background: #28a745; color: white; width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 1.1em; font-weight: bold; cursor: pointer; margin-top: 20px; }}
        
        .loading {{ display: none; text-align: center; margin-top: 15px; font-weight: bold; color: #e67e22; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Relatório Técnico</h1>
        
        <form action="/gerar-relatorio" method="post" enctype="multipart/form-data" onsubmit="mostrarLoading()">
            
            <div class="grupo-input">
                <label>Técnico:</label>
                <input type="text" name="tecnico" id="tecnico" required placeholder="Seu nome">
            </div>
            
             <div class="grupo-input">
                <label>Cliente / Obra:</label>
                <input type="text" name="cliente" required placeholder="Nome do Cliente">
            </div>

            <hr style="margin: 20px 0; border: 0; border-top: 1px solid #eee;">

            <div class="grupo-input">
                <label>Selecione o Relatório:</label>
                <select id="tipo_relatorio" name="tipo_relatorio" onchange="alternarRelatorios()" class="input-estilo" required>
                    <option value="">-- Escolha --</option>
                    <option value="gas">🔥 Gás Combustível / CO</option>
                    <option value="incendio">🧯 Incêndio (SADI)</option>
                    <option value="eletrico">⚡ Elétrico / PT</option>
                </select>
            </div>

            <div id="form-gas" class="hidden">
                <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <div class="grupo-input">
                        <label>Periodicidade:</label>
                        <select name="periodicidade">
                            <option value="semestral">Semestral</option>
                            <option value="anual">Anual</option>
                        </select>
                    </div>
                    <div class="grupo-input">
                        <label>Data:</label>
                        <input type="date" name="data_relatorio" class="data-hoje">
                    </div>
                    <div class="grupo-input">
                        <label>Instalação:</label>
                        <input type="text" name="instalacao" placeholder="Ex: Central Térmica">
                    </div>
                    <div class="grupo-input">
                        <label>Localização:</label>
                        <input type="text" name="localizacao" placeholder="Ex: Piso -1">
                    </div>
                    <div class="grupo-input">
                        <label>Tipo de Sistema:</label>
                        <select name="tipo_sistema">
                            <option value="gas_combustivel">Gás Combustível</option>
                            <option value="monoxido">Monóxido de Carbono (CO)</option>
                        </select>
                    </div>
                </div>

                <h3>✅ Ações de Verificação</h3>
                <table class="tabela-verificacao">
                    <thead>
                        <tr>
                            <th>Ação</th>
                            <th>V</th>
                            <th>NA</th>
                            <th>OBS</th>
                        </tr>
                    </thead>
                    <tbody>
                        {gerar_html_gas_checks()}
                    </tbody>
                </table>
            </div>

            <div id="form-incendio" class="hidden">
                <p style="text-align:center; padding: 20px; background: #fff3cd; border-radius:8px;">
                    ⚠️ O formulário de Incêndio será configurado em breve.
                    <br>Use o de Gás como teste por enquanto.
                </p>
                <input type="hidden" name="data_relatorio_backup" class="data-hoje"> 
            </div>

            <div id="form-eletrico" class="hidden">
                 <p style="text-align:center; padding: 20px; background: #d1ecf1; border-radius:8px;">
                    ⚠️ O formulário Elétrico será configurado em breve.
                </p>
            </div>

            <div class="grupo-input">
                <label>📝 Observações Gerais:</label>
                <textarea name="obs" rows="3"></textarea>
            </div>

            <div class="grupo-input">
                <label>📷 Fotografias:</label>
                <input type="file" name="fotos" accept="image/*" multiple style="padding: 10px;">
            </div>

            <button type="submit" class="btn-submit">📄 Gerar PDF</button>
            <div id="loading" class="loading">⏳ A gerar relatório...</div>
        </form>
    </div>

    <script>
        // Preencher data de hoje
        window.onload = function() {{
            const hoje = new Date().toISOString().split('T')[0];
            const camposData = document.querySelectorAll('.data-hoje');
            camposData.forEach(c => c.value = hoje);

            // Recuperar nome técnico
            const salvo = localStorage.getItem("nomeTecnico");
            if(salvo) document.getElementById('tecnico').value = salvo;
        }}

        function alternarRelatorios() {{
            document.getElementById('form-gas').classList.add('hidden');
            document.getElementById('form-incendio').classList.add('hidden');
            document.getElementById('form-eletrico').classList.add('hidden');

            const tipo = document.getElementById('tipo_relatorio').value;
            if (tipo) {{
                document.getElementById('form-' + tipo).classList.remove('hidden');
            }}
        }}

        function mostrarLoading() {{
            const nome = document.getElementById('tecnico').value;
            if(nome) localStorage.setItem("nomeTecnico", nome);
            document.getElementById('loading').style.display = 'block';
        }}
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return html_app

@app.post("/gerar-relatorio")
async def gerar_relatorio(request: Request):
    # 1. Receber TODOS os dados do formulário
    form_data = await request.form()
    
    # Converter para dicionário normal
    dados = dict(form_data)
    
    # Processar imagens separadamente
    fotos = form_data.getlist("fotos")
    imagens_bytes = []
    for foto in fotos:
        if isinstance(foto, UploadFile) and foto.filename:
            conteudo = await foto.read()
            imagens_bytes.append(conteudo)

    # 2. Gerar PDF
    pdf_bytes = gerar_pdf_final(dados, imagens_bytes)
    
    # 3. Nome do ficheiro
    cliente_safe = dados.get('cliente', 'Cliente').replace(' ', '_')
    tipo = dados.get('tipo_relatorio', 'Relatorio')
    nome_ficheiro = f"{tipo.upper()}_{cliente_safe}_{datetime.now().strftime('%d%m')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(bytes(pdf_bytes)), 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nome_ficheiro}"}
    )