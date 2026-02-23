import streamlit as st
import pandas as pd
import json
import os
import time
import html
from io import BytesIO
from datetime import datetime, date, timedelta
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT

# Importar funções de cronograma automático
from cronograma_auto import gerar_cronograma_automatico, get_cargas_com_auto, get_descricao_carga

# --- FERIADOS DO ANO CORRENTE (2026) ---
ANO_ATUAL = 2026

def calcular_pascoa(ano):
    """Calcula a data da Páscoa para um determinado ano"""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)

def get_feriados_2026():
    """Retorna todos os feriados de 2026"""
    pascoa = calcular_pascoa(2026)

    feriados = [
        # Feriados nacionais fixos
        {"data": date(2026, 1, 1), "nome": "Confraternização Universal"},
        {"data": date(2026, 4, 21), "nome": "Tiradentes"},
        {"data": date(2026, 5, 1), "nome": "Dia do Trabalho"},
        {"data": date(2026, 9, 7), "nome": "Independência do Brasil"},
        {"data": date(2026, 10, 12), "nome": "Nossa Senhora Aparecida"},
        {"data": date(2026, 11, 2), "nome": "Finados"},
        {"data": date(2026, 11, 15), "nome": "Proclamação da República"},
        {"data": date(2026, 11, 20), "nome": "Consciência Negra"},
        {"data": date(2026, 12, 25), "nome": "Natal"},
        # Feriados estaduais (RJ)
        {"data": date(2026, 4, 23), "nome": "Dia de São Jorge (RJ)"},
        # Feriados municipais (Campos dos Goytacazes - exemplo)
        {"data": date(2026, 1, 15), "nome": "Santo Amaro"},
        {"data": date(2026, 8, 6), "nome": "São Salvador"},
        # Feriados móveis (baseados na Páscoa 2026)
        {"data": pascoa - timedelta(days=47), "nome": "Carnaval"},
        {"data": pascoa - timedelta(days=46), "nome": "Carnaval (segunda)"},
        {"data": pascoa - timedelta(days=2), "nome": "Sexta-feira Santa"},
        {"data": pascoa, "nome": "Páscoa"},
        {"data": pascoa + timedelta(days=60), "nome": "Corpus Christi"},
    ]

    feriados.sort(key=lambda x: x["data"])
    return feriados

feriados_2026 = get_feriados_2026()

# --- TEXTOS PADRÃO ---
TEXTO_FALTAS_PADRAO = """Por lei, não há abono de faltas. A legislação exige que o aluno tenha 75% de presença nas atividades para obter aprovação. Portanto, o aluno pode faltar até 25% da carga horária em uma disciplina.

Atestados médicos não abonam faltas, apenas há uma justificativa que já é descontada dos 25% permitidos por lei. Logo, é recomendado ser parcimonioso ao faltar às aulas. Faltas trazmr danos ao aprendizado do estudante, além de usar os 25% de faltas para uma eventual emergência ou situação médica.

As faltas são registradas em horas. O número de faltas permitidas depende da carga horária da disciplina em que o aluno está matriculado. Para cada aula de 2 horas, são contabilizadas 2 faltas.

Veja alguns exemplos:
• 34 horas -> Máximo de 8 horas de falta (4 dias de aula de 2 h)
• 51 horas -> Máximo de 12 horas de falta (6 dias de aula de 2 h) ou (4 dias de aula de 3h)
• 68 horas -> Máximo de 16 horas de falta (8 dias de aula de 2 h), e assim por diante.

As faltas devem ser registradas mensalmente no sistema acadêmico, e o percentual de presença é atualizado automaticamente. Para casos de saúde em que é necessário faltar até 15 dias (limitado a 60 dias): o aluno deve entrar com solicitação de Regime de Exercícios Escolares, sendo a entrega das atividades obrigatória como compensação às faltas; a não entrega implica no registro da falta."""

TEXTO_RECOMENDA_PADRAO = """• Estudar com constância à medida que o conteúdo for aplicado.
• Use livros, e acesse minha biblioteca no sistema acadêmico. A leitura é essencial;
• Estude antecipadamente o conteúdo e Resolva lista de exercícios;
• Forme grupos de estudos;
• Não deixe para estudar na véspera da prova, faça uma programação de estudos.
• Frequente a monitoria.
• Tirar dúvidas com o professor."""

# --- FUNÇÕES DE CONVERSÃO DE DATAS ---
def converter_data_para_string(data_valor):
    """Converte data do date picker para string no formato dd/mm/aaaa"""
    if data_valor is None or pd.isna(data_valor):
        return ""
    if isinstance(data_valor, date):
        return data_valor.strftime("%d/%m/%Y")
    if isinstance(data_valor, str):
        try:
            datetime.strptime(data_valor, "%d/%m/%Y")
            return data_valor
        except:
            return ""
    return ""

def converter_string_para_data(data_str):
    """Converte string dd/mm/aaaa para objeto date do Python"""
    if not data_str or pd.isna(data_str):
        return None
    try:
        if isinstance(data_str, str):
            return datetime.strptime(data_str, "%d/%m/%Y").date()
    except:
        pass
    return None

# --- FUNÇÕES DE CÁLCULO DE FALTAS ---
def calcular_faltas_permitidas(carga_horaria):
    """Calcula o número máximo de faltas baseado na carga horária"""
    try:
        carga = int(carga_horaria) if carga_horaria else 0
        faltas_max = int(carga * 0.25)
        dias_falta = faltas_max // 2
        return faltas_max, dias_falta
    except:
        return 0, 0

def atualizar_texto_faltas(carga_horaria):
    """Atualiza o texto de faltas com base na carga horária"""
    faltas_max, dias_falta = calcular_faltas_permitidas(carga_horaria)

    if faltas_max > 0:
        return f"""Por lei, não há abono de faltas. A legislação exige que o aluno tenha 75% de presença nas atividades para obter aprovação. Portanto, o aluno pode faltar até 25% da carga horária em uma disciplina.

Atestados médicos não abonam faltas, apenas há uma justificativa que já é descontada dos 25% permitidos por lei. Logo, recomenda-se ser parcimonioso ao faltar às aulas, pois isso pode trazer danos ao aprendizado do estudante além de reduzir as possibilidades de faltas para uma situação médica.

As faltas são registradas em horas. O número de faltas permitidas depende da carga horária da disciplina em que o aluno está matriculado. Para cada aula de 2 horas, são contabilizadas 2 faltas.

Para esta disciplina com carga horária de {carga_horaria}h:
• Máximo de {faltas_max} horas de falta ({dias_falta} dias de aula de 2h)

As faltas devem ser registradas mensalmente no sistema acadêmico, e o percentual de presença é atualizado automaticamente. Para casos de saúde em que é necessário faltar até 15 dias (limitado a 60 dias): o aluno deve entrar com solicitação de Regime de Exercícios Escolares, sendo a entrega das atividades obrigatória como compensação às faltas; a não entrega implica no registro da falta."""
    else:
        return TEXTO_FALTAS_PADRAO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gerador de Plano de Ensino de Disciplinas de Graduação - UENF",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
        [data-testid='stFileUploader'] section button { font-size: 0 !important; color: transparent !important; }
        [data-testid='stFileUploader'] section button::after { content: 'Carregar Arquivo' !important; font-size: 14px !important; color: inherit !important; visibility: visible !important; display: block !important; }
        [data-testid='stFileUploader'] section > div > div > span, [data-testid='stFileUploader'] section > div > div > small { display: none !important; }
        [data-testid='stFileUploader'] section > div > div::before { content: 'Carregue o arquivo ou solte aqui' !important; font-size: 14px !important; color: #555 !important; display: block !important; margin-bottom: 5px !important; }
        [data-testid='stFileUploader'] section > div > div::after { content: 'Limite de 200MB' !important; font-size: 12px !important; color: #888 !important; display: block !important; margin-top: 5px !important; }
        .stButton button { width: 100%; }
        div[data-testid="column"] div[data-testid="stDateInput"] { min-width: 150px; }
    </style>
""", unsafe_allow_html=True)

st.title("🎓 Gerador de Plano de Ensino de Disciplinas de Graduação - UENF")

# --- INICIALIZAÇÃO DOS DADOS ---
if 'gerais' not in st.session_state:
    st.session_state.gerais = {
        "disciplina": "", "codigo": "", "turma": "",
        "laboratorio": "", "coordenador": "", "tipo_aprovacao": "Média e frequência",
        "professor": "", "semestre": "", "carga_horaria": "",
        "horas_extensao": 0,
        "ementa": "", "objetivo": ""
    }

if 'extras' not in st.session_state:
    st.session_state.extras = {
        "criterios": "", "bib_basica": "", "bib_complementar": "",
        "tem_exame": True, "data_exame": None,
        "obs_faltas": TEXTO_FALTAS_PADRAO, "obs_recomenda": TEXTO_RECOMENDA_PADRAO
    }

if 'df_cronograma' not in st.session_state:
    dados_iniciais = []
    for i in range(1, 18):
        dados_iniciais.append({
            "Semana": str(i),
            "Data": "",
            "Duração": "2 h",
            "Conteúdo": "",
            "Estratégia Didática": "",
            "Avaliação": ""
        })
    st.session_state.df_cronograma = pd.DataFrame(dados_iniciais)
    st.session_state['editor_counter'] = 0

# --- FUNÇÕES DE SALVAR E CARREGAR ---
def obter_dados_completos():
    # Salvar cronograma com datas em string
    df_salvar = st.session_state.df_cronograma.copy()
    if 'Data' in df_salvar.columns:
        df_salvar['Data'] = df_salvar['Data'].apply(converter_data_para_string)

    # Salvar extras com data_exame em string
    extras_salvar = st.session_state.extras.copy()
    if extras_salvar.get('data_exame') and isinstance(extras_salvar['data_exame'], date):
        extras_salvar['data_exame'] = extras_salvar['data_exame'].strftime("%d/%m/%Y")

    return {
        "gerais": st.session_state.gerais,
        "extras": extras_salvar,
        "cronograma": df_salvar.to_dict(orient='records')
    }
def carregar_projeto(arquivo_json):
    try:
        dados = json.load(arquivo_json)

        # 1. Dados Gerais - Sincroniza com as chaves 'input_...' e 'area_...'
        if "gerais" in dados:
            st.session_state.gerais = dados["gerais"]
            g = dados["gerais"]
            st.session_state["input_disciplina"] = g.get("disciplina", "")
            st.session_state["input_codigo"] = g.get("codigo", "")
            st.session_state["input_turma"] = g.get("turma", "")
            st.session_state["input_professor"] = g.get("professor", "")
            st.session_state["input_coordenador"] = g.get("coordenador", "")
            st.session_state["input_laboratorio"] = g.get("laboratorio", "")
            st.session_state["input_semestre"] = g.get("semestre", "")
            st.session_state["area_ementa"] = g.get("ementa", "")
            st.session_state["area_objetivo"] = g.get("objetivo", "")
            st.session_state["input_carga"] = g.get("carga_horaria", "")


        # 2. Cronograma - O DataFrame já funciona bem assim
        if "cronograma" in dados:
            st.session_state.df_cronograma = pd.DataFrame(dados["cronograma"])

        # 3. Extras - Sincroniza com as chaves 'area_...' e 'input_...'
        if "extras" in dados:
            st.session_state.extras = dados["extras"]
            e = dados["extras"]
            st.session_state["area_criterios"] = e.get("criterios", "")
            st.session_state["area_bib_basica"] = e.get("bib_basica", "")
            st.session_state["area_bib_complementar"] = e.get("bib_complementar", "")
            st.session_state["area_faltas"] = e.get("obs_faltas", "")
            st.session_state["area_recomenda"] = e.get("obs_recomenda", "")
            # Caso tenha data de exame
            if "data_exame" in e and e["data_exame"]:
                try:
                    # Converte a string "01/07/2026" para objeto date
                    st.session_state["input_data_exame"] = datetime.strptime(e["data_exame"], "%d/%m/%Y").date()
                except:
                    pass

        st.success("✅ Projeto carregado com sucesso!")
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")


def resetar_projeto():
    """Reseta completamente o projeto para os valores iniciais"""
    # Resetar informações gerais
    st.session_state.gerais = {
        "disciplina": "", "codigo": "", "turma": "",
        "laboratorio": "", "coordenador": "", "tipo_aprovacao": "Média e frequência",
        "professor": "", "semestre": "", "carga_horaria": "",
        "horas_extensao": 0,
        "ementa": "", "objetivo": ""
    }

    # Resetar informações extras
    st.session_state.extras = {
        "criterios": "", "bib_basica": "", "bib_complementar": "",
        "tem_exame": True, "data_exame": None,
        "obs_faltas": TEXTO_FALTAS_PADRAO, "obs_recomenda": TEXTO_RECOMENDA_PADRAO
    }

    # Resetar cronograma
    dados_iniciais = []
    for i in range(1, 18):
        dados_iniciais.append({
            "Semana": str(i),
            "Data": "",
            "Duração": "2 h",
            "Conteúdo": "",
            "Estratégia Didática": "",
            "Avaliação": ""
        })
    st.session_state.df_cronograma = pd.DataFrame(dados_iniciais)
    st.session_state['editor_counter'] = 0

    # Limpar buffer do PDF se existir
    if 'pdf_buffer' in st.session_state:
        del st.session_state.pdf_buffer

    st.rerun()
def resetar_projeto():
    """Reseta completamente o projeto para os valores iniciais"""
    # Resetar informações gerais
    st.session_state.gerais = {
        "disciplina": "", "codigo": "", "turma": "",
        "laboratorio": "", "coordenador": "", "tipo_aprovacao": "Média e frequência",
        "professor": "", "semestre": "", "carga_horaria": "",
        "horas_extensao": 0,
        "ementa": "", "objetivo": ""
    }

    # Resetar informações extras
    st.session_state.extras = {
        "criterios": "", "bib_basica": "", "bib_complementar": "",
        "tem_exame": True, "data_exame": None,
        "obs_faltas": TEXTO_FALTAS_PADRAO, "obs_recomenda": TEXTO_RECOMENDA_PADRAO
    }

    # Resetar cronograma
    dados_iniciais = []
    for i in range(1, 18):
        dados_iniciais.append({
            "Semana": str(i),
            "Data": "",
            "Duração": "2 h",
            "Conteúdo": "",
            "Estratégia Didática": "",
            "Avaliação": ""
        })
    st.session_state.df_cronograma = pd.DataFrame(dados_iniciais)
    st.session_state['editor_counter'] = 0

    # Limpar buffer do PDF se existir
    if 'pdf_buffer' in st.session_state:
        del st.session_state.pdf_buffer

    st.rerun()

# --- FUNÇÕES PDF ---
def desenhar_cabecalho_rodape(canvas, doc):
    canvas.saveState()
    largura, altura = landscape(A4)

    # Brasão do RJ no centro superior
    if os.path.exists("brasao_rj.png"):
        canvas.drawImage("brasao_rj.png", (largura - 35) / 2.0, altura - 45, width=35, height=35, preserveAspectRatio=True, mask='auto')

    # Texto institucional
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(largura / 2.0, altura - 55, "Governo do Estado do Rio de Janeiro")
    canvas.drawCentredString(largura / 2.0, altura - 65, "Universidade Estadual do Norte Fluminense Darcy Ribeiro")

    # Número da página
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(largura / 2.0, 30, f"Página {doc.page}")

    # Logos nos cantos inferiores
    if os.path.exists("logo_uenf.png"):
        canvas.drawImage("logo_uenf.png", 40, 20, width=80, height=40, preserveAspectRatio=True, mask='auto')

    if os.path.exists("logo_prograd_1.png"):
        canvas.drawImage("logo_prograd_1.png", largura - 120, 20, width=80, height=40, preserveAspectRatio=True, mask='auto')

    canvas.restoreState()

def gerar_pdf_buffer(gerais, df_cronograma, extras):
    buffer = BytesIO()
    largura_folha, _ = landscape(A4)
    largura_util = largura_folha - 80

    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=40, leftMargin=40, topMargin=80, bottomMargin=70)
    elementos = []
    estilos = getSampleStyleSheet()

    estilo_titulo = estilos['Heading1']
    estilo_titulo.alignment = TA_CENTER
    estilo_normal = estilos['Normal']
    estilo_normal.alignment = TA_JUSTIFY
    estilo_normal.leading = 12

    estilo_caixa = ParagraphStyle(name='CaixaTexto', parent=estilos['Normal'], alignment=TA_JUSTIFY, leading=12)
    estilo_tabela = ParagraphStyle(name='TabelaTexto', parent=estilos['Normal'], fontSize=9, leading=11)

    def texto_seguro(texto):
        if pd.isna(texto) or texto is None: return ""
        return html.escape(str(texto).strip()).replace("\n", "<br/>")

    def criar_faixa_azul(texto):
        estilo_branco = ParagraphStyle(name='BrancoCentro', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.whitesmoke, alignment=TA_CENTER)
        tabela = Table([[Paragraph(texto, estilo_branco)]], colWidths=[largura_util])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#2C3E50")),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6)
        ]))
        return tabela

    def criar_caixa_texto(texto_escapado):
        linhas = texto_escapado.split("<br/>")
        elementos_linha = []
        for linha in linhas:
            if not linha.strip():
                elementos_linha.append([Paragraph("&nbsp;", estilo_caixa)])
            else:
                elementos_linha.append([Paragraph(linha, estilo_caixa)])

        tabela = Table(elementos_linha, colWidths=[largura_util])
        tabela.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        return tabela

    # --- PÁGINA 1: TÍTULO, CABEÇALHO, EMENTA E OBJETIVO ---
    # TÍTULO
    elementos.append(Paragraph(f"Plano de Ensino: {texto_seguro(gerais.get('disciplina', ''))}", estilo_titulo))
    elementos.append(Spacer(1, 15))

    # CABEÇALHO
    estilo_info = ParagraphStyle(name='InfoTexto', parent=estilos['Normal'], fontSize=9, leading=14)
    coord_texto = f"<b>Coordenador(a):</b> {texto_seguro(gerais.get('coordenador', ''))}" if gerais.get('coordenador') else ""

    extensao_texto = ""
    if gerais.get('horas_extensao', 0) > 0:
        extensao_texto = f" | Extensão: {gerais['horas_extensao']}h"

    if extras.get('tem_exame', True):
        data_exame = extras.get('data_exame', '')
        if isinstance(data_exame, date):
            data_exame = data_exame.strftime("%d/%m/%Y")
        exame_texto = f"<b>Exame Final:</b> {texto_seguro(data_exame)}"
    else:
        exame_texto = "<b>Exame Final:</b> Não aplicável"

    dados_header = [
        [Paragraph(f"<b>Código / Turma:</b> {texto_seguro(gerais.get('codigo', ''))} - {texto_seguro(gerais.get('turma', ''))}", estilo_info),
         Paragraph(f"<b>Ano/Período:</b> {texto_seguro(gerais.get('semestre', ''))}", estilo_info)],
        [Paragraph(f"<b>Professor(a):</b> {texto_seguro(gerais.get('professor', ''))}", estilo_info),
         Paragraph(coord_texto, estilo_info)],
        [Paragraph(f"<b>Laboratório:</b> {texto_seguro(gerais.get('laboratorio', ''))}", estilo_info),
         Paragraph(f"<b>Carga Horária:</b> {texto_seguro(gerais.get('carga_horaria', ''))}{extensao_texto}", estilo_info)],
        [Paragraph(f"<b>Tipo de Aprovação:</b> {texto_seguro(gerais.get('tipo_aprovacao', 'Média e frequência'))}", estilo_info),
         Paragraph(exame_texto, estilo_info)]
    ]

    tabela_header = Table(dados_header, colWidths=[largura_util*0.5, largura_util*0.5])
    tabela_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3)
    ]))
    elementos.append(tabela_header)
    elementos.append(Spacer(1, 15))

    # EMENTA
    elementos.append(criar_faixa_azul("Ementa"))
    elementos.append(criar_caixa_texto(texto_seguro(gerais.get('ementa', ''))))
    elementos.append(Spacer(1, 15))

    # OBJETIVO GERAL
    elementos.append(criar_faixa_azul("Objetivo Geral"))
    elementos.append(criar_caixa_texto(texto_seguro(gerais.get('objetivo', ''))))
    elementos.append(Spacer(1, 20))

    # --- PÁGINA 2: CRONOGRAMA ---
    elementos.append(PageBreak())
    elementos.append(criar_faixa_azul("Cronograma de Aulas"))

    dados_tabela = [["Semana", "Data", "Duração", "Conteúdo Programático", "Estratégia Didática", "Avaliações / Entregas"]]

    for index, row in df_cronograma.iterrows():
        dados_tabela.append([
            str(row.get('Semana', '')),
            str(row.get('Data', '')),
            str(row.get('Duração', '')),
            Paragraph(texto_seguro(row.get('Conteúdo', '')), estilo_tabela),
            Paragraph(texto_seguro(row.get('Estratégia Didática', '')), estilo_tabela),
            Paragraph(texto_seguro(row.get('Avaliação', '')), estilo_tabela)
        ])

    larguras_colunas = [
        largura_util * 0.07,
        largura_util * 0.10,
        largura_util * 0.07,
        largura_util * 0.32,
        largura_util * 0.24,
        largura_util * 0.20
    ]

    estilo_tabela_grid = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 1.0, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),

        # Alinhar colunas específicas
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Coluna Duração (índice 2) centralizada
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Semana centralizada (opcional)
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Data centralizada (opcional)
    ]

    tabela_crono = Table(dados_tabela, colWidths=larguras_colunas, repeatRows=1)
    tabela_crono.setStyle(TableStyle(estilo_tabela_grid))

    elementos.append(tabela_crono)
    elementos.append(Spacer(1, 25))

    # --- PÁGINA 3: SISTEMA DE AVALIAÇÃO ---
    elementos.append(PageBreak())
    elementos.append(criar_faixa_azul("Sistema de Avaliação"))
    elementos.append(criar_caixa_texto(texto_seguro(extras['criterios'])))
    elementos.append(Spacer(1, 15))

    # --- PÁGINA 4: BIBLIOGRAFIA ---
    elementos.append(PageBreak())

    # Bibliografia Básica
    elementos.append(criar_faixa_azul("Bibliografia Básica"))
    texto_bib_basica = texto_seguro(extras['bib_basica'])
    if len(texto_bib_basica.split("<br/>")) > 3:
        estilo_bib_compacto = ParagraphStyle(
            name='BibliografiaCompacta',
            parent=estilo_caixa,
            fontSize=9,
            leading=11,
            alignment=TA_JUSTIFY
        )
        linhas_bib = texto_bib_basica.split("<br/>")
        elementos_bib = []
        for linha in linhas_bib:
            if linha.strip():
                elementos_bib.append([Paragraph(linha, estilo_bib_compacto)])
        tabela_bib = Table(elementos_bib, colWidths=[largura_util])
        tabela_bib.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        elementos.append(tabela_bib)
    else:
        elementos.append(criar_caixa_texto(texto_bib_basica))
    elementos.append(Spacer(1, 10))

    # Bibliografia Complementar
    elementos.append(criar_faixa_azul("Bibliografia Complementar"))
    elementos.append(criar_caixa_texto(texto_seguro(extras['bib_complementar'])))

    # --- PÁGINA 5: OBSERVAÇÕES ---
    elementos.append(PageBreak())
    elementos.append(criar_faixa_azul("Observações e Instruções Acadêmicas"))
    elementos.append(Spacer(1, 15))
    elementos.append(Paragraph("<b>1. Regras de Frequência e Faltas</b>", estilos['Heading3']))
    elementos.append(Spacer(1, 5))
    elementos.append(Paragraph(texto_seguro(extras['obs_faltas']), estilo_normal))
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("<b>2. Recomendações para o Sucesso na Disciplina</b>", estilos['Heading3']))
    elementos.append(Spacer(1, 5))
    elementos.append(Paragraph(texto_seguro(extras['obs_recomenda']), estilo_normal))

    try:
        doc.build(elementos, onFirstPage=desenhar_cabecalho_rodape, onLaterPages=desenhar_cabecalho_rodape)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Erro ao gerar o PDF: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Gerenciar Arquivo")
    arquivo_upload = st.file_uploader("Carregar projeto salvo (.json)", type=["json"], key="uploader")
    if arquivo_upload:
        if st.button("Restaurar Dados", key="btn_restaurar"):
            carregar_projeto(arquivo_upload)
            st.rerun()

    st.divider()

    # Garantir que nome_arquivo está definido
    nome_arquivo = f"Plano_de_Ensino_{st.session_state.gerais['codigo']}_{st.session_state.gerais['semestre']}"
    nome_arquivo = nome_arquivo.replace(" ", "_").replace("/", "_")
    if nome_arquivo == "Plano_de_Ensino__":
        nome_arquivo = "Plano_de_Ensino"

    st.download_button(
        label="💾 Salvar Projeto (JSON)",
        data=json.dumps(obter_dados_completos(), indent=4, ensure_ascii=False),
        file_name=f"{nome_arquivo}.json",
        mime="application/json",
        key="btn_salvar_json"
    )

    st.divider()
    st.header("📄 Novo Plano")
    with st.expander("✨ Começar um Novo Plano"):
        if st.button("🗑️ Limpar Tudo", key="btn_limpar_tudo"):
            resetar_projeto()

    # --- FERIADOS 2026 ---
    st.divider()
    with st.expander("📅 Feriados 2026", expanded=False):
        meses_feriados = [
            ("Janeiro", {1: "Confraternização Universal", 15: "Santo Amaro"}),
            ("Fevereiro", {}),
            ("Março", {}),
            ("Abril", {21: "Tiradentes", 23: "São Jorge (RJ)"}),
            ("Maio", {1: "Dia do Trabalho"}),
            ("Junho", {}),
            ("Julho", {}),
            ("Agosto", {6: "São Salvador"}),
            ("Setembro", {7: "Independência"}),
            ("Outubro", {12: "Nossa Sra. Aparecida"}),
            ("Novembro", {2: "Finados", 15: "Proclamação República", 20: "Consciência Negra"}),
            ("Dezembro", {25: "Natal"})
        ]

        pascoa = calcular_pascoa(2026)
        carnaval = pascoa - timedelta(days=47)
        corpus = pascoa + timedelta(days=60)
        sexta_santa = pascoa - timedelta(days=2)

        st.write("**Feriados Fixos:**")
        for mes_nome, feriados in meses_feriados:
            for dia, nome_feriado in feriados.items():
                st.write(f"  • {dia:02d}/{mes_nome[:3]} - {nome_feriado}")

        st.write("**Feriados Móveis:**")
        st.write(f"  • {carnaval.strftime('%d/%m')} - Carnaval")
        st.write(f"  • {sexta_santa.strftime('%d/%m')} - Sexta-feira Santa")
        st.write(f"  • {pascoa.strftime('%d/%m')} - Páscoa")
        st.write(f"  • {corpus.strftime('%d/%m')} - Corpus Christi")

    # --- LOGOS ---
    st.divider()

    # Usar colunas para criar margem esquerda
    col_esquerda, col_logos, col_direita = st.columns([1, 3, 1])

    with col_logos:
        if os.path.exists("logo_prograd_1.png"):
            st.image("logo_prograd_1.png", width=130)

        if os.path.exists("logo_uenf.png"):
            st.image("logo_uenf.png", width=100)

    # --- GERAÇÃO RÁPIDA ---
    st.divider()
    st.markdown("### ⚡ Geração Rápida")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("34h", use_container_width=True, key="btn_34h"):
            df = gerar_cronograma_automatico(34)
            if df is not None:
                st.session_state.df_cronograma = df
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.rerun()

    with col2:
        if st.button("68h", use_container_width=True, key="btn_68h"):
            df = gerar_cronograma_automatico(68)
            if df is not None:
                st.session_state.df_cronograma = df
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.rerun()

    col3, col4 = st.columns(2)
    with col3:
        if st.button("102h", use_container_width=True, key="btn_102h"):
            df = gerar_cronograma_automatico(102)
            if df is not None:
                st.session_state.df_cronograma = df
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.rerun()

    with col4:
        if st.button("Reset", use_container_width=True, key="btn_reset_rapido"):
            dados = [{"Semana": str(i), "Data": "", "Duração": "2 h", "Conteúdo": "", "Estratégia Didática": "", "Avaliação": ""} for i in range(1, 18)]
            st.session_state.df_cronograma = pd.DataFrame(dados)
            st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
            st.rerun()

# --- INTERFACE PRINCIPAL ---
st.subheader("1. Informações Gerais")

c1, c2, c3 = st.columns([2, 1, 1])
# Removido o st.session_state.gerais.get(...) de dentro dos parênteses
st.session_state.gerais['disciplina'] = c1.text_input("Disciplina", key="input_disciplina")
st.session_state.gerais['codigo'] = c2.text_input("Código", key="input_codigo")
st.session_state.gerais['turma'] = c3.text_input("Turma", key="input_turma")

c4, c5 = st.columns([1, 1])
st.session_state.gerais['professor'] = c4.text_input("Professor(a)", key="input_professor")
st.session_state.gerais['coordenador'] = c5.text_input("Coordenador(a)", key="input_coordenador")

c6, c7 = st.columns([1, 1])
st.session_state.gerais['laboratorio'] = c6.text_input("Laboratório", key="input_laboratorio")
st.session_state.gerais['semestre'] = c7.text_input("Ano/Período", key="input_semestre")

# O mesmo para as áreas de texto
st.session_state.gerais['ementa'] = st.text_area("Ementa", height=100, key="area_ementa")
st.session_state.gerais['objetivo'] = st.text_area("Objetivo Geral", height=100, key="area_objetivo")

# --- CARGA HORÁRIA ---
st.subheader("1.1 Configuração de Carga Horária")

c8, c9, c10 = st.columns([1, 1, 1])
with c8:
    opcoes = ["", "34", "51", "68", "85", "102"]
    index = 0
    if st.session_state.gerais['carga_horaria'] in opcoes:
        index = opcoes.index(st.session_state.gerais['carga_horaria'])

    carga = st.selectbox("Carga Horária Total", opcoes, index=index, key="select_carga")
    st.session_state.gerais['carga_horaria'] = carga

    if carga:
        st.caption(f"📋 {get_descricao_carga(carga)}")

with c9:
    st.session_state.gerais['horas_extensao'] = st.number_input(
        "Horas de Extensão",
        min_value=0,
        max_value=100,
        value=st.session_state.gerais['horas_extensao'],
        step=1,
        key="num_extensao"
    )

with c10:
    st.session_state.gerais['tipo_aprovacao'] = st.selectbox(
        "Tipo de Aprovação",
        ["Média e frequência", "Só frequência"],
        index=0 if st.session_state.gerais['tipo_aprovacao'] == "Média e frequência" else 1,
        key="select_aprovacao"
    )

col_a1, col_a2, col_a3 = st.columns([1, 1, 2])
with col_a1:
    if st.button("⚡ Gerar Estrutura", type="primary", use_container_width=True, key="btn_gerar_estrutura"):
        if st.session_state.gerais['carga_horaria']:
            df = gerar_cronograma_automatico(st.session_state.gerais['carga_horaria'])
            if df is not None:
                st.session_state.df_cronograma = df
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.success("Estrutura gerada!")
                st.rerun()
            else:
                st.info("Preenchimento manual necessário")

with col_a2:
    if st.button("🔄 Reset 1/semana", use_container_width=True, key="btn_reset_semana"):
        dados = [{"Semana": str(i), "Data": "", "Duração": "2 h", "Conteúdo": "", "Estratégia Didática": "", "Avaliação": ""} for i in range(1, 18)]
        st.session_state.df_cronograma = pd.DataFrame(dados)
        st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
        st.rerun()

with col_a3:
    st.caption(f"✨ Automático: {', '.join(map(str, get_cargas_com_auto()))}h")

if st.session_state.gerais['carga_horaria']:
    faltas, dias = calcular_faltas_permitidas(st.session_state.gerais['carga_horaria'])
    st.info(f"📊 Carga: {st.session_state.gerais['carga_horaria']}h | Faltas: {faltas}h ({dias} dias)")

st.divider()

# --- CRONOGRAMA DE AULAS ---
st.subheader("2. Cronograma de Aulas")
st.write("📅 Clique na data para abrir o calendário")

opcoes_duracao = ["", "2 h", "3 h", "4 h"]
opcoes_estrategia = ["", "Aula Expositiva Dialogada", "Resolução de Exercícios / Problemas", "Aula Prática em Laboratório",
                     "Sala de Aula Invertida", "Apresentação de Seminários", "Estudo Dirigido / Leitura de Texto",
                     "Discussão em Grupo / Debate", "Trabalho de campo", "Atividade extensionista",
                     "Avaliação Escrita / Prova", "Outra"]
opcoes_avaliacao = ["", "Nenhuma", "Prova 1", "Prova 2", "Prova 3", "Prova 4", "Prova Oral","Relatório", "Lista de Exercícios",
                    "Seminário", "Teste Online", "Teste", "Trabalho", "Participação", "Projeto Prático",
                    "Apresentação Oral", "Outra"]

# Preparar DataFrame para edição - garantir que temos dados
df_para_edicao = st.session_state.df_cronograma.copy()

# Converter strings de data para objetos date de forma robusta
if 'Data' in df_para_edicao.columns:
    def safe_string_to_date(x):
        if pd.isna(x) or x == "" or x is None:
            return None
        if isinstance(x, date):
            return x
        if isinstance(x, str):
            # Tentar diferentes formatos
            try:
                # Formato dd/mm/aaaa
                return datetime.strptime(x.strip(), "%d/%m/%Y").date()
            except:
                try:
                    # Formato yyyy-mm-dd (ISO)
                    return datetime.strptime(x.strip(), "%Y-%m-%d").date()
                except:
                    return None
        return None

    # Aplicar conversão apenas para strings, preservar objetos date existentes
    df_para_edicao['Data'] = df_para_edicao['Data'].apply(safe_string_to_date)

# Data editor com key única
editor_key = f"data_editor_{st.session_state.get('editor_counter', 0)}"
df_editado = st.data_editor(
    df_para_edicao,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=False,
    key=editor_key,
    column_config={
        "Semana": st.column_config.TextColumn("Semana", required=False),
        "Data": st.column_config.DateColumn(
            "Data",
            format="DD/MM/YYYY",
            min_value=date(2020,1,1),
            max_value=date(2030,12,31),
            required=False
        ),
        "Duração": st.column_config.SelectboxColumn("Duração", options=opcoes_duracao, required=False),
        "Conteúdo": st.column_config.TextColumn("Conteúdo", required=False),
        "Estratégia Didática": st.column_config.SelectboxColumn("Estratégia Didática", options=opcoes_estrategia, required=False),
        "Avaliação": st.column_config.SelectboxColumn("Avaliação", options=opcoes_avaliacao, required=False)
    }
)

# --- BOTÕES DE CONTROLE DO CRONOGRAMA ---
col_b1, col_b2, col_b3 = st.columns([1, 1, 4])

with col_b1:
    if st.button("💾 Salvar Cronograma", type="primary", use_container_width=True, key="btn_salvar_cronograma"):
        # Criar cópia do DataFrame editado
        df_salvar = df_editado.copy()

        # Converter datas para string no formato brasileiro
        if 'Data' in df_salvar.columns:
            def safe_date_to_string(x):
                if pd.isna(x) or x is None:
                    return ""
                if isinstance(x, date):
                    return x.strftime("%d/%m/%Y")
                if isinstance(x, str):
                    # Já é string, manter como está
                    return x
                return ""

            df_salvar['Data'] = df_salvar['Data'].apply(safe_date_to_string)

        # Salvar no session_state
        st.session_state.df_cronograma = df_salvar

        # Incrementar contador para forçar atualização
        st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1

        st.success("✅ Cronograma salvo com sucesso!")
        st.rerun()

with col_b2:
    if st.button("↻ Recarregar", use_container_width=True, key="btn_recarregar"):
        st.rerun()

# --- VERIFICAÇÃO DE FERIADOS (CORRIGIDA) ---
st.divider()
st.subheader("🔍 Verificação de Feriados")

if 'Data' in df_editado.columns:
    datas_feriados = [f["data"] for f in feriados_2026]
    nomes_feriados = {f["data"]: f["nome"] for f in feriados_2026}

    feriados_encontrados = []

    for idx, row in df_editado.iterrows():
        data = row.get('Data')
        semana = row.get('Semana', '?')

        # Verificar se é um objeto date e está na lista de feriados
        if isinstance(data, date) and data in datas_feriados:
            nome = nomes_feriados[data]
            feriados_encontrados.append((semana, data, nome))

    if feriados_encontrados:
        st.error("🚨 **ATENÇÃO: Feriados Detectados!**")
        for semana, data, nome in feriados_encontrados:
            st.warning(f"📅 Semana {semana}: {data.strftime('%d/%m/%Y')} - **{nome}**")
    else:
        st.success("✅ Nenhum feriado detectado nas datas selecionadas.")

# --- PREVIEW DOS DADOS (MOSTRANDO DATAS) ---
with st.expander("👁️ Visualizar Dados Salvos", expanded=False):
    # Mostrar o DataFrame com as datas em formato string
    st.dataframe(st.session_state.df_cronograma, use_container_width=True)

    # Mostrar estatísticas
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("Total de Linhas", len(st.session_state.df_cronograma))
    with col_stats2:
        semanas_unicas = st.session_state.df_cronograma['Semana'].nunique()
        st.metric("Semanas Únicas", semanas_unicas)
    with col_stats3:
        # Contar quantas datas foram preenchidas (não vazias)
        datas_preenchidas = st.session_state.df_cronograma['Data'].astype(bool).sum()
        st.metric("Datas Preenchidas", datas_preenchidas)

    # Mostrar as primeiras datas como exemplo
    st.write("**Primeiras datas salvas:**")
    st.write(st.session_state.df_cronograma[['Semana', 'Data']].head())

# --- TESTE DE DATAS (PARA DEBUG - REMOVER DEPOIS) ---
with st.expander("🔧 Debug - Datas", expanded=False):
    st.write("**Datas no session_state:**")
    st.write(st.session_state.df_cronograma[['Semana', 'Data']].head(10))

    st.write("**Tipos das datas:**")
    for i, val in enumerate(st.session_state.df_cronograma['Data'].head(5)):
        st.write(f"Linha {i}: {val} - tipo: {type(val)}")



# --- INSERIR LINHA POR SEMANA ---
st.divider()
st.markdown("#### ➕ Inserir Nova Linha em uma Semana")

# CSS simples para alinhamento pela base
st.markdown("""
    <style>
        /* Força todas as colunas a alinharem seu conteúdo pela base */
        [data-testid="column"] {
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            height: 100%;
        }

        /* Remove margens extras que causam desalinhamento */
        [data-testid="column"] .stSelectbox,
        [data-testid="column"] .stButton,
        [data-testid="column"] .stAlert {
            margin-bottom: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

semanas = st.session_state.df_cronograma['Semana'].unique()
semanas = [s for s in semanas if str(s).strip()]

if len(semanas) > 0:
    col_s1, col_s2, col_s3 = st.columns(3)

    with col_s1:
        semana_para_inserir = st.selectbox("", semanas, key="semana_inserir_select", label_visibility="collapsed")

    with col_s2:
        if st.button("➕ Inserir Nova Linha", use_container_width=True, key="btn_inserir_linha"):
            df_atual = st.session_state.df_cronograma.copy()
            indices = df_atual[df_atual['Semana'] == semana_para_inserir].index
            if len(indices) > 0:
                posicao_inserir = indices[-1] + 1
                nova_linha = pd.DataFrame([{
                    "Semana": semana_para_inserir,
                    "Data": "",
                    "Duração": "2 h",
                    "Conteúdo": "",
                    "Estratégia Didática": "",
                    "Avaliação": ""
                }])
                df_atual = pd.concat([
                    df_atual.iloc[:posicao_inserir],
                    nova_linha,
                    df_atual.iloc[posicao_inserir:]
                ]).reset_index(drop=True)
                st.session_state.df_cronograma = df_atual
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.success("✅ Inserido!")
                st.rerun()

    with col_s3:
        qtd_atividades = len(st.session_state.df_cronograma[st.session_state.df_cronograma['Semana'] == semana_para_inserir])
        st.info(f"📊 {qtd_atividades} atividade(s)")
else:
    st.warning("Nenhuma semana encontrada.")

st.divider()

# --- EXAME FINAL, AVALIAÇÃO E BIBLIOGRAFIA ---
st.subheader("3. Exame Final, Avaliação e Bibliografia")

col_e1, col_e2 = st.columns([1, 2])
with col_e1:
    tem_exame = st.radio("Exame Final?", ["Sim", "Não"], index=0 if st.session_state.extras.get('tem_exame', True) else 1, key="radio_exame")
    st.session_state.extras['tem_exame'] = (tem_exame == "Sim")

with col_e2:
    if st.session_state.extras['tem_exame']:
        data_exame = st.session_state.extras.get('data_exame')
        if isinstance(data_exame, str):
            try:
                data_exame = datetime.strptime(data_exame, "%d/%m/%Y").date()
            except:
                data_exame = None

        st.session_state.extras['data_exame'] = st.date_input(
                "Data do Exame Final",
                format="DD/MM/YYYY",  # Força o formato brasileiro visualmente
                key="input_data_exame"
            )

st.session_state.extras['criterios'] = st.text_area("Critérios de Avaliação", st.session_state.extras.get('criterios', ''), height=100, key="area_criterios")
st.session_state.extras['bib_basica'] = st.text_area("Bibliografia Básica", st.session_state.extras.get('bib_basica', ''), height=100, key="area_bib_basica")
st.session_state.extras['bib_complementar'] = st.text_area("Bibliografia Complementar", st.session_state.extras.get('bib_complementar', ''), height=100, key="area_bib_complementar")

st.divider()



# --- OBSERVAÇÕES ---
st.subheader("4. Observações e Instruções")

col_o1, col_o2 = st.columns([1, 3])
with col_o1:
    if st.button("🔄 Atualizar Texto de Faltas", use_container_width=True, key="btn_atualizar_faltas"):
        if st.session_state.gerais.get('carga_horaria'):
            st.session_state.extras['obs_faltas'] = atualizar_texto_faltas(st.session_state.gerais['carga_horaria'])
            st.rerun()

with col_o2:
    st.caption("Clique para gerar texto automático baseado na carga horária")

st.session_state.extras['obs_faltas'] = st.text_area(
    "Regras de Frequência e Faltas",
    st.session_state.extras.get('obs_faltas', ''),
    height=200,
    key="area_faltas"
)

st.session_state.extras['obs_recomenda'] = st.text_area(
    "Recomendações para o Sucesso",
    st.session_state.extras.get('obs_recomenda', ''),
    height=150,
    key="area_recomenda"
)

st.divider()

# --- GERAR PDF ---
st.subheader("📄 Gerar PDF")

if st.button("🔄 Gerar PDF", use_container_width=True, key="btn_gerar_pdf"):
    with st.spinner("Gerando PDF..."):
        buffer = gerar_pdf_buffer(st.session_state.gerais, st.session_state.df_cronograma, st.session_state.extras)
        if buffer:
            st.session_state.pdf_buffer = buffer
            st.success("✅ PDF gerado com sucesso!")

if 'pdf_buffer' in st.session_state:
    st.download_button(
        label="📥 Baixar PDF",
        data=st.session_state.pdf_buffer,
        file_name=f"{nome_arquivo}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="btn_download_pdf"
    )

st.divider()

# --- SAIR ---
if st.button("Sair do Programa", use_container_width=True, key="btn_sair"):
    st.error("Encerrando o programa...")
    time.sleep(1)
    os._exit(0)
