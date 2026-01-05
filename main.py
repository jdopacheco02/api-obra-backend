from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fpdf import FPDF
from typing import List
import io
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURAÇÃO DO CHECKLIST ---
# Defina aqui o que os técnicos têm de verificar
ITENS_CHECKLIST = [
    "Quadro Elétrico (Limpeza/Aperto)",
    "Iluminação de Emergência",
    "Tomadas e Interruptores",
    "Cabos e Ligações Visíveis",
    "Extintores e Sinalética",
    "Limpeza Geral do Local"
]

# --- FUNÇÃO GERADORA DE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Relatório de Visita Técnica', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def criar_pdf(tecnico, cliente, obs, checks, imagens):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # 1. Cabeçalho do Relatório
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 10, txt=f"Cliente/Obra: {cliente}", ln=1, align='L', fill=True)
    pdf.cell(0, 10, txt=f"Técnico: {tecnico}", ln=1, align='L')
    pdf.cell(0, 10, txt=f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1, align='L')
    pdf.ln(5)

    # 2. Checklist
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Verificações Efetuadas:", ln=1)
    pdf.set_font("Arial", size=12)
    
    # Desenha as caixas [X] ou [ ]
    for item in ITENS_CHECKLIST:
        marcado = item in checks
        sinal = "[ X ]" if marcado else "[   ]"
        cor = (0, 150, 0) if marcado else (150, 150, 150) # Verde se feito, Cinza se não
        
        pdf.set_text_color(*cor)
        pdf.cell(15, 8, sinal, 0, 0)
        pdf.set_text_color(0, 0, 0) # Volta a preto
        pdf.cell(0, 8, item, 0, 1)
    
    pdf.ln(5)

    # 3. Observações
    if obs:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Observações / Anomalias:", ln=1)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, obs)
        pdf.ln(5)

    # 4. Fotografias
    if imagens:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Registo Fotográfico:", ln=1)
        
        # Lógica simples para meter fotos (2 por página, ajustadas)
        y_pos = 30
        for img_bytes in imagens:
            if y_pos > 200: # Se chegar ao fundo, nova página
                pdf.add_page()
                y_pos = 20
            
            try:
                # Cria ficheiro temporário na memória para o PDF ler
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
                    temp.write(img_bytes)
                    temp_path = temp.name
                
                # Insere imagem (largura 100mm, centrada)
                pdf.image(temp_path, x=55, y=y_pos, w=100)
                y_pos += 80 # Avança para a próxima posição
            except Exception as e:
                pdf.cell(0, 10, f"Erro ao anexar imagem: {str(e)}", ln=1)

    # Retorna o PDF como bytes
    return pdf.output(dest='S')

# --- INTERFACE (HTML/JS) ---
html_content = f"""
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Obra</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f4f9; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; }}
        
        .grupo-input {{ margin-bottom: 15px; }}
        label {{ display: block; font-weight: bold; margin-bottom: 5px; }}
        input[type="text"], textarea {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }}
        
        .checklist-item {{ background: #f9f9f9; padding: 12px; margin-bottom: 8px; border-radius: 8px; display: flex; align-items: center; border: 1px solid #eee; }}
        .checklist-item input {{ width: 20px; height: 20px; margin-right: 15px; }}
        
        .btn-submit {{ background: #27ae60; color: white; width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 1.1em; font-weight: bold; cursor: pointer; margin-top: 20px; }}
        .btn-submit:hover {{ background: #219150; }}

        .loading {{ display: none; text-align: center; margin-top: 10px; font-weight: bold; color: #e67e22; }}
    </style>
</head>
<body>

    <div class="container">
        <h1>📋 Relatório de Campo</h1>
        
        <form id="relatorioForm" action="/gerar-relatorio" method="post" enctype="multipart/form-data">
            
            <div class="grupo-input">
                <label>Nome do Técnico:</label>
                <input type="text" name="tecnico" placeholder="Ex: João Silva" required>
            </div>

            <div class="grupo-input">
                <label>Cliente / Local:</label>
                <input type="text" name="cliente" placeholder="Ex: Obra Hotel Ritz" required>
            </div>

            <h3>Verificações (Marque o que fez):</h3>
            <div id="lista-checks">
                {''.join([f'<div class="checklist-item"><input type="checkbox" name="checks" value="{item}"><span>{item}</span></div>' for item in ITENS_CHECKLIST])}
            </div>

            <div class="grupo-input">
                <label>Observações:</label>
                <textarea name="obs" rows="3" placeholder="Ex: Disjuntor principal estava desligado..."></textarea>
            </div>

            <div class="grupo-input">
                <label>📷 Fotografias (Opcional):</label>
                <input type="file" name="fotos" accept="image/*" multiple capture="environment" style="padding: 10px;">
                <small style="display:block; color:gray;">Pode selecionar várias ou tirar na hora.</small>
            </div>

            <button type="submit" class="btn-submit" onclick="mostrarLoading()">📄 Gerar e Baixar PDF</button>
            <div id="loading" class="loading">⏳ A gerar relatório, aguarde...</div>
        </form>
    </div>

    <script>
        // Recuperar nome guardado
        window.onload = function() {{
            const salvo = localStorage.getItem("nomeTecnico");
            if(salvo) document.querySelector('input[name="tecnico"]').value = salvo;
        }}

        // Guardar nome ao enviar e mostrar loading
        function mostrarLoading() {{
            const nome = document.querySelector('input[name="tecnico"]').value;
            if(nome) localStorage.setItem("nomeTecnico", nome);
            document.getElementById('loading').style.display = 'block';
        }}
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content

@app.post("/gerar-relatorio")
async def gerar_relatorio(
    tecnico: str = Form(...),
    cliente: str = Form(...),
    obs: str = Form(""),
    checks: List[str] = Form([]),
    fotos: List[UploadFile] = File(None)
):
    # Processar imagens (ler os bytes)
    imagens_bytes = []
    if fotos:
        for foto in fotos:
            if foto.filename: # Se tiver nome, é ficheiro válido
                conteudo = await foto.read()
                imagens_bytes.append(conteudo)

    # Gerar PDF
    pdf_bytes = criar_pdf(tecnico, cliente, obs, checks, imagens_bytes)
    
    # Enviar para download imediato
    nome_ficheiro = f"Relatorio_{cliente.replace(' ', '_')}_{datetime.now().strftime('%H%M')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(bytes(pdf_bytes)), 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nome_ficheiro}"}
    )