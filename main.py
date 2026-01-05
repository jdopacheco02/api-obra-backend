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

# --- 1. LISTAS DE VERIFICAÇÃO (CHECKLISTS) ---

ITENS_GAS = [
    "Inspeção Visual: Efetuar a inspeção visual da central e do conjunto dos detetores, botões de alarme e demais periféricos e verificar se existem danos visíveis ou outras condições que ponham em causa o funcionamento / desempenho do sistema",
    "Inspeção Visual: Verificar se existe identificação de zonas / detetores",
    "Detetores: Confirmar o posicionamento dos detetores em função do gás a detetar",
    "Detetores: Verificar a validade",
    "Detetores: Efetuar o teste de detenção a todos os detetores e verificar se estão calibrados (ajustar ao intervalo de valores recomendado pelo fabricante), quando aplicável",
    "Sinalizador Ótico-Acústico: Verificar a visibilidade e som",
    "Sinalizador Ótico-Acústico: Verificar a fixação e estado de conservação",
    "Sinalizador Ótico-Acústico: Verificar a descrição <<Atmosfera Perigosa - Tipo de Gás>>",
    "Sinalizador Ótico-Acústico: Verificar a descrição <<Atmosfera Saturada - CO>>",
    "Central: Efetuar ensaios de zona",
    "Central: Verificar as funções de monitorização de anomalias",
    "Central: Confirmar que a programação do equipamento está de acordo com o funcionamento atual aprovado para o edifício de acordo com o projeto e subsequentes alterações registadas no registo de ocorrências / registo de segurança",
    "Central: Verificar a capacidade de operar comandos de outros equipamentos interligados, designadamente ventilação (Monóxido de Carbono)",
    "Central: Verificar a capacidade de operar comandos de outros equipamentos interligados, designadamente electroválvulas e ventilação (Gás Combustível)",
    "Central: Comprovar o correto funcionamento da unidade de alimentação e testar a carga das baterias de forma a garantir a autonomia mínima prevista no Regulamento Técnico de SCIE",
    "Central: Comprovar o correto funcionamento da unidade de alimentação",
    "Fonte de Alimentação: Verificar o teste de carga das baterias",
    "Fonte de Alimentação: Verificação das tensões de Entrada / Saída",
    "Fonte de Alimentação: Limpeza e reaperto de bornes",
    "Painel Repetidor: Verificar indicações visuais",
    "Painel Repetidor: Verificar os botões e comandos"

  
]

ITENS_INCENDIO = [
    "Verificação visual da Central de Incêndio (CDI)",
    "Verificação do estado das baterias e fonte de alimentação",
    "Teste de funcionamento de botoneiras de alarme",
    "Teste de detetores (Fumo/Térmico) por amostragem",
    "Verificação das sirenes e sinalizadores óticos",
    "Teste de transmissão de alarme (comunicador)",
    "Verificação dos painéis repetidores",
    "Verificação de retentores de portas de fogo",
    "Sinalização de segurança e plantas de emergência",
    "Limpeza geral dos equipamentos"
]

ITENS_ELETRICO = [
    "Estado geral do Quadro Geral Baixa Tensão (QGBT)",
    "Verificação de aquecimentos (Termografia visual)",
    "Reaperto de ligações elétricas (Bornes/Barramentos)",
    "Teste dos botões de teste dos Diferenciais",
    "Verificação da continuidade do condutor de proteção (Terra)",
    "Verificação da seletividade das proteções",
    "Limpeza interior e exterior dos quadros",
    "Estado da iluminação de emergência (Autonomia)",
    "Verificação do Posto de Transformação (Nível óleo/Sílica)",
    "Existência de esquemas elétricos e sinalização de perigo"
]

# --- 2. CLASSE GERADORA DE PDF ---

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'Relatório Técnico de Manutenção', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def check_page_break(self, height_needed):
        """Cria nova página se não houver espaço suficiente"""
        if self.get_y() + height_needed > 270:
            self.add_page()

    def desenhar_tabela_verificacao(self, itens, respostas):
        self.check_page_break(50)
        self.set_font("Arial", 'B', 12)
        self.cell(0, 10, "1. Ações de Verificação:", 0, 1)
        
        # Cabeçalho
        self.set_font("Arial", 'B', 9)
        self.set_fill_color(240, 240, 240)
        self.cell(130, 8, "Ação / Parâmetro", 1, 0, 'L', True)
        self.cell(20, 8, "V", 1, 0, 'C', True)
        self.cell(20, 8, "NA", 1, 0, 'C', True)
        self.cell(20, 8, "OBS", 1, 1, 'C', True)

        self.set_font("Arial", size=9)
        for i, item in enumerate(itens):
            resp = respostas.get(f"check_{i}", "")
            
            x_start = self.get_x()
            y_start = self.get_y()
            
            # Coluna Texto (MultiCell para quebrar linha se for grande)
            self.multi_cell(130, 8, item, 1)
            
            y_end = self.get_y()
            altura = y_end - y_start
            
            # Desenhar as caixas das respostas com a mesma altura
            self.set_xy(x_start + 130, y_start)
            
            def draw_cell(val):
                txt = "X" if resp == val else ""
                if resp == "OBS" and val == "OBS": self.set_font("Arial", 'B', 9)
                self.cell(20, altura, txt, 1, 0, 'C')
                self.set_font("Arial", size=9)

            draw_cell("V")
            draw_cell("NA")
            draw_cell("OBS")
            
            self.ln()
            self.set_y(y_end) # Assegura cursor no sítio certo

    def desenhar_tabela_componentes(self, dados):
        self.ln(5)
        self.check_page_break(60)
        self.set_font("Arial", 'B', 12)
        self.cell(0, 10, "2. Listagem de Componentes Instalados / Substituídos:", 0, 1)

        # Cabeçalho
        self.set_font("Arial", 'B', 8)
        self.set_fill_color(240, 240, 240)
        self.cell(70, 7, "Componente", 1, 0, 'L', True)
        self.cell(50, 7, "Marca", 1, 0, 'L', True)
        self.cell(50, 7, "Modelo", 1, 0, 'L', True)
        self.cell(20, 7, "Qtd", 1, 1, 'C', True)

        # Linhas (10x)
        self.set_font("Arial", size=8)
        for i in range(10):
            comp = dados.get(f'comp_nome_{i}', '')
            marca = dados.get(f'comp_marca_{i}', '')
            modelo = dados.get(f'comp_modelo_{i}', '')
            qtd = dados.get(f'comp_qtd_{i}', '')

            if comp or marca or modelo: # Só imprime se tiver algo escrito
                self.cell(70, 7, comp, 1)
                self.cell(50, 7, marca, 1)
                self.cell(50, 7, modelo, 1)
                self.cell(20, 7, qtd, 1, 1, 'C')

    def desenhar_tabela_equipamentos(self, dados):
        self.ln(5)
        self.check_page_break(60)
        self.set_font("Arial", 'B', 12)
        self.cell(0, 10, "3. Equipamentos de Medida e Ensaio:", 0, 1)

        self.set_font("Arial", 'B', 8)
        self.set_fill_color(240, 240, 240)
        self.cell(60, 7, "Equipamento", 1, 0, 'L', True)
        self.cell(30, 7, "Data Calib.", 1, 0, 'C', True)
        self.cell(40, 7, "Certificado Nº", 1, 0, 'L', True)
        self.cell(60, 7, "Entidade", 1, 1, 'L', True)

        self.set_font("Arial", size=8)
        for i in range(10):
            nome = dados.get(f'equip_nome_{i}', '')
            data = dados.get(f'equip_data_{i}', '')
            cert = dados.get(f'equip_cert_{i}', '')
            ent = dados.get(f'equip_ent_{i}', '')

            if nome or cert:
                self.cell(60, 7, nome, 1)
                self.cell(30, 7, data, 1, 0, 'C')
                self.cell(40, 7, cert, 1)
                self.cell(60, 7, ent, 1, 1)

    def desenhar_tabela_observacoes(self, dados):
        self.ln(5)
        self.check_page_break(60)
        self.set_font("Arial", 'B', 12)
        self.cell(0, 10, "4. Observações:", 0, 1)

        self.set_font("Arial", 'B', 8)
        self.set_fill_color(240, 240, 240)
        self.cell(20, 7, "OBS Nº", 1, 0, 'C', True)
        self.cell(170, 7, "Descrição", 1, 1, 'L', True)

        self.set_font("Arial", size=8)
        for i in range(10):
            num = dados.get(f'obs_num_{i}', '')
            desc = dados.get(f'obs_desc_{i}', '')

            if num or desc:
                self.cell(20, 7, num, 1, 0, 'C')
                self.multi_cell(170, 7, desc, 1)

    def desenhar_identificacao_tecnico(self, dados):
        self.ln(10)
        self.check_page_break(50)
        self.set_fill_color(230, 230, 230)
        self.set_font("Arial", 'B', 12)
        self.cell(0, 10, "Identificação do Técnico", 1, 1, 'L', True)

        self.set_font("Arial", size=9)
        
        # Linha 1: Nome e CC
        self.cell(30, 8, "Nome:", 0, 0, 'L')
        self.cell(100, 8, dados.get('tec_nome', ''), "B", 0, 'L')
        self.cell(20, 8, "CC Nº:", 0, 0, 'R')
        self.cell(40, 8, dados.get('tec_cc', ''), "B", 1, 'L')

        # Linha 2: Morada
        self.cell(30, 8, "Morada:", 0, 0, 'L')
        self.cell(160, 8, dados.get('tec_morada', ''), "B", 1, 'L')

        # Linha 3: Localidade e CP
        self.cell(30, 8, "Localidade:", 0, 0, 'L')
        self.cell(80, 8, dados.get('tec_localidade', ''), "B", 0, 'L')
        self.cell(30, 8, "C. Postal:", 0, 0, 'R')
        self.cell(50, 8, dados.get('tec_cp', ''), "B", 1, 'L')

        # Linha 4: NIF e Registo
        self.cell(30, 8, "Contribuinte:", 0, 0, 'L')
        self.cell(60, 8, dados.get('tec_nif', ''), "B", 0, 'L')
        self.cell(40, 8, "Nº DGEG/OET:", 0, 0, 'R')
        self.cell(60, 8, dados.get('tec_registo', ''), "B", 1, 'L')
        
        self.ln(10)
        self.cell(0, 10, "Assinatura: __________________________________________________", 0, 1, 'R')

# --- 3. LÓGICA PRINCIPAL PDF ---

def gerar_pdf_final(dados: dict, imagens: list):
    pdf = PDF()
    pdf.add_page()
    
    # Cabeçalho Principal
    pdf.set_font("Arial", 'B', 16)
    pdf.set_fill_color(200, 220, 255)
    
    titulo = "Relatório Técnico"
    tipo = dados.get('tipo_relatorio')
    lista_checks = []

    if tipo == 'gas':
        titulo = "MANUTENÇÃO GÁS E MONÓXIDO"
        lista_checks = ITENS_GAS
    elif tipo == 'incendio':
        titulo = "MANUTENÇÃO SADI (INCÊNDIO)"
        lista_checks = ITENS_INCENDIO
    elif tipo == 'eletrico':
        titulo = "VISTORIA ELÉTRICA / PT"
        lista_checks = ITENS_ELETRICO

    pdf.cell(0, 15, titulo, 0, 1, 'C', True)
    pdf.ln(5)

    # Dados Cliente
    pdf.set_font("Arial", size=10)
    pdf.cell(30, 7, "Cliente:", 0, 0); pdf.cell(0, 7, dados.get('cliente', ''), 1, 1)
    pdf.cell(30, 7, "Data:", 0, 0); pdf.cell(0, 7, dados.get('data_relatorio', ''), 1, 1)
    
    if tipo == 'gas':
        pdf.cell(30, 7, "Instalação:", 0, 0); pdf.cell(0, 7, dados.get('instalacao', ''), 1, 1)
    
    pdf.ln(5)

    # 1. Tabela Checklist
    pdf.desenhar_tabela_verificacao(lista_checks, dados)

    # 2. Componentes
    pdf.desenhar_tabela_componentes(dados)

    # 3. Equipamentos
    pdf.desenhar_tabela_equipamentos(dados)

    # 4. Observações
    pdf.desenhar_tabela_observacoes(dados)

    # 5. Fotos
    if imagens:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "5. Registo Fotográfico:", 0, 1)
        y_pos = 30
        for img_bytes in imagens:
            if y_pos > 200:
                pdf.add_page(); y_pos = 20
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
                    temp.write(img_bytes); temp_path = temp.name
                pdf.image(temp_path, x=40, y=y_pos, w=130)
                y_pos += 100 
            except: pass

    # 6. Identificação Técnico
    pdf.desenhar_identificacao_tecnico(dados)

    return pdf.output(dest='S')


# --- 4. FUNÇÕES HTML HELPERS ---

def gerar_linhas_tabela(nome_lista, prefixo_radio):
    html = ""
    for i, item in enumerate(nome_lista):
        html += f"""<tr>
            <td>{item}</td>
            <td class="col-center"><input type="radio" name="{prefixo_radio}_{i}" value="V"></td>
            <td class="col-center"><input type="radio" name="{prefixo_radio}_{i}" value="NA"></td>
            <td class="col-center"><input type="radio" name="{prefixo_radio}_{i}" value="OBS"></td>
        </tr>"""
    return html

def gerar_inputs_repetidos(qtd, campos):
    """Gera tabelas de inputs repetidos para Components, Equipamentos, etc."""
    html = ""
    for i in range(qtd):
        html += "<tr>"
        for campo in campos:
            largura = "width: 50px;" if "qtd" in campo['nome'] else "width: 100%;"
            html += f'<td><input type="text" name="{campo["nome"]}_{i}" placeholder="{campo["ph"]}" style="{largura}"></td>'
        html += "</tr>"
    return html


# --- 5. ENDPOINTS E HTML PRINCIPAL ---

html_app = f"""
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatórios Técnicos</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f4f9; padding: 10px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        h1, h3 {{ color: #2c3e50; }}
        h3 {{ border-bottom: 2px solid #007BFF; padding-bottom: 5px; margin-top: 30px; }}
        
        .grupo-input {{ margin-bottom: 15px; }}
        label {{ display: block; font-weight: bold; margin-bottom: 5px; font-size: 0.9em; }}
        input, select {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }}
        
        .hidden {{ display: none; }}
        
        /* Tabelas */
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; margin-bottom: 10px; }}
        th {{ background: #eee; text-align: left; padding: 8px; border: 1px solid #ddd; }}
        td {{ border: 1px solid #ddd; padding: 5px; }}
        .col-center {{ text-align: center; width: 40px; }}
        
        .btn-submit {{ background: #28a745; color: white; width: 100%; padding: 15px; font-weight: bold; font-size: 1.2em; border: none; border-radius: 8px; cursor: pointer; margin-top: 20px; }}
        
        .seccao-tecnico {{ background: #e8f4fd; padding: 15px; border-radius: 8px; border: 1px solid #b6d4fe; }}
    </style>
</head>
<body>
    <div class="container">
        <h1 style="text-align:center;">📋 Relatório Técnico</h1>
        
        <form action="/gerar-relatorio" method="post" enctype="multipart/form-data" onsubmit="guardarDados()">
            
            <div class="grupo-input">
                <label>Cliente / Obra:</label>
                <input type="text" name="cliente" required placeholder="Nome do Cliente">
            </div>
            <div class="grupo-input">
                <label>Data:</label>
                <input type="date" name="data_relatorio" id="data_hoje">
            </div>

            <div class="grupo-input">
                <label>Tipo de Intervenção:</label>
                <select id="tipo_relatorio" name="tipo_relatorio" onchange="mudarForm()" style="background:#fff3cd; font-weight:bold;">
                    <option value="">-- Selecione --</option>
                    <option value="gas">🔥 Gás e Monóxido</option>
                    <option value="incendio">🧯 Incêndio (SADI)</option>
                    <option value="eletrico">⚡ Elétrico / PT</option>
                </select>
            </div>

            <hr>

            <div id="form-gas" class="hidden">
                <div class="grupo-input"><label>Instalação:</label><input type="text" name="instalacao"></div>
                <table>
                    <tr><th>Ação Verificação</th><th>V</th><th>NA</th><th>OBS</th></tr>
                    {gerar_linhas_tabela(ITENS_GAS, 'check')}
                </table>
            </div>

            <div id="form-incendio" class="hidden">
                <table>
                    <tr><th>Ação Verificação</th><th>V</th><th>NA</th><th>OBS</th></tr>
                    {gerar_linhas_tabela(ITENS_INCENDIO, 'check')}
                </table>
            </div>

            <div id="form-eletrico" class="hidden">
                <table>
                    <tr><th>Ação Verificação</th><th>V</th><th>NA</th><th>OBS</th></tr>
                    {gerar_linhas_tabela(ITENS_ELETRICO, 'check')}
                </table>
            </div>

            <h3> Listagem de Componentes Instalados</h3>
            <table>
                <tr><th>Componente</th><th>Marca</th><th>Modelo</th><th>Qtd</th></tr>
                {gerar_inputs_repetidos(10, [
                    {'nome': 'comp_nome', 'ph': ''},
                    {'nome': 'comp_marca', 'ph': ''},
                    {'nome': 'comp_modelo', 'ph': ''},
                    {'nome': 'comp_qtd', 'ph': '0'}
                ])}
            </table>

            <h3> Listagem dos Equipamentos de Medida e Ensaio Utilizados </h3>
            <table>
                <tr><th>Equipamento</th><th>Data Calib.</th><th>Certificado</th><th>Entidade</th></tr>
                {gerar_inputs_repetidos(10, [
                    {'nome': 'equip_nome', 'ph': ''},
                    {'nome': 'equip_data', 'ph': ''},
                    {'nome': 'equip_cert', 'ph': ''},
                    {'nome': 'equip_ent', 'ph': ''}
                ])}
            </table>

            <h3> Lista de Observações </h3>
            <table>
                <tr><th style="width:50px;">OBS Nº</th><th>Descrição</th></tr>
                {gerar_inputs_repetidos(10, [
                    {'nome': 'obs_num', 'ph': '#'},
                    {'nome': 'obs_desc', 'ph': 'Descrição da anomalia...'}
                ])}
            </table>

            <h3>📷 Fotos</h3>
            <input type="file" name="fotos" accept="image/*" multiple>

            <div class="seccao-tecnico">
                <h3>👷 Identificação do Técnico</h3>
                <div class="grupo-input"><label>Nome Completo:</label><input type="text" name="tec_nome" id="tec_nome"></div>
                <div style="display:flex; gap:10px;">
                    <div style="flex:1"><label>CC Nº:</label><input type="text" name="tec_cc" id="tec_cc"></div>
                    <div style="flex:1"><label>NIF:</label><input type="text" name="tec_nif" id="tec_nif"></div>
                </div>
                <div class="grupo-input"><label>Morada:</label><input type="text" name="tec_morada" id="tec_morada"></div>
                <div style="display:flex; gap:10px;">
                    <div style="flex:2"><label>Localidade:</label><input type="text" name="tec_localidade" id="tec_localidade"></div>
                    <div style="flex:1"><label>C. Postal:</label><input type="text" name="tec_cp" id="tec_cp"></div>
                </div>
                <div class="grupo-input"><label>Nº DGEG / OET:</label><input type="text" name="tec_registo" id="tec_registo"></div>
            </div>

            <button type="submit" class="btn-submit">📄 GERAR PDF</button>
        </form>
    </div>

    <script>
        window.onload = function() {{
            document.getElementById('data_hoje').value = new Date().toISOString().split('T')[0];
            
            // Carregar dados do técnico guardados
            ['tec_nome','tec_cc','tec_nif','tec_morada','tec_localidade','tec_cp','tec_registo'].forEach(id => {{
                if(localStorage.getItem(id)) document.getElementById(id).value = localStorage.getItem(id);
            }});
        }}

        function mudarForm() {{
            document.getElementById('form-gas').classList.add('hidden');
            document.getElementById('form-incendio').classList.add('hidden');
            document.getElementById('form-eletrico').classList.add('hidden');
            
            let tipo = document.getElementById('tipo_relatorio').value;
            if(tipo) document.getElementById('form-' + tipo).classList.remove('hidden');
        }}

        function guardarDados() {{
            ['tec_nome','tec_cc','tec_nif','tec_morada','tec_localidade','tec_cp','tec_registo'].forEach(id => {{
                localStorage.setItem(id, document.getElementById(id).value);
            }});
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
    form_data = await request.form()
    dados = dict(form_data)
    
    fotos = form_data.getlist("fotos")
    imagens_bytes = []
    for foto in fotos:
        if isinstance(foto, UploadFile) and foto.filename:
            imagens_bytes.append(await foto.read())

    pdf_bytes = gerar_pdf_final(dados, imagens_bytes)
    
    nome_ficheiro = f"Relatorio_{dados.get('tipo_relatorio')}_{datetime.now().strftime('%d%m_%H%M')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(bytes(pdf_bytes)), 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nome_ficheiro}"}
    )