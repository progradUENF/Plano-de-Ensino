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
# Definir o ano corrente
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
    # Páscoa em 2026
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

    # Ordenar por data
    feriados.sort(key=lambda x: x["data"])
    return feriados

# Obter feriados de 2026
feriados_2026 = get_feriados_2026()

# --- TEXTOS PADRÃO (OBSERVAÇÕES E FALTAS) ---
TEXTO_FALTAS_PADRAO = """Por lei, não há abono de faltas. A legislação exige que o aluno tenha 75% de presença nas atividades para obter aprovação. Portanto, o aluno pode faltar até 25% da carga horária em uma disciplina.

Atestados médicos não abonam faltas, apenas há uma justificativa que já é descontada dos 25% permitidos por lei. Logo, recomenda-se ser parcimonioso ao faltar às aulas, pois isso pode trazer danos ao aprendizado do estudante além de reduzir as possibilidades de faltas para uma situação médica.

As faltas são registradas em horas. O número de faltas permitidas depende da carga horária da disciplina em que o aluno está matriculado. Para cada aula de 2 horas, são contabilizadas 2 faltas.

Veja alguns exemplos:
• 34 horas -> Máximo de 8 horas de falta (4 dias de aula de 2 h)
• 51 horas -> Máximo de 12 horas de falta (6 dias de aula de 2 h) ou (4 dias de aula de 3h)
• 68 horas -> Máximo de 16 horas de falta (8 dias de aula de 2 h), e assim por diante.

As faltas devem ser registradas mensalmente no sistema acadêmico, e o percentual de presença é atualizado automaticamente. Para casos de saúde em que é necessário faltar até 15 dias (limitado a 60 dias): o aluno deve entrar com solicitação de Regime de Exercícios Escolares, sendo a entrega das atividades obrigatória como compensação às faltas; a não entrega implica no registro da falta."""

TEXTO_RECOMENDA_PADRAO = """• Estudar com constância à medida que o conteúdo for aplicado.
• Use livros, biblioteca virtual, a leitura é essencial.
• Estudar antecipadamente.
• Formar grupos de estudos.
• Não deixar para estudar na véspera da prova.
• Procurar monitoria.
• Tirar dúvidas com o professor."""

# --- FUNÇÃO PARA CONVERTER DATAS ---
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

# --- FUNÇÃO PARA CALCULAR FALTAS PERMITIDAS ---
def calcular_faltas_permitidas(carga_horaria):
    """Calcula o número máximo de faltas baseado na carga horária"""
    try:
        carga = int(carga_horaria) if carga_horaria else 0
        faltas_max = int(carga * 0.25)  # 25% da carga horária
        dias_falta = faltas_max // 2  # Cada aula tem 2h
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
st.set_page_config(page_title="Gerador de Plano de Ensino UENF", layout="wide")

# --- CSS E TRADUÇÃO ---
st.markdown("""
    <style>
        [data-testid='stFileUploader'] section button { font-size: 0 !important; color: transparent !important; }
        [data-testid='stFileUploader'] section button::after { content: 'Carregar Arquivo' !important; font-size: 14px !important; color: inherit !important; visibility: visible !important; display: block !important; }
        [data-testid='stFileUploader'] section > div > div > span, [data-testid='stFileUploader'] section > div > div > small { display: none !important; }
        [data-testid='stFileUploader'] section > div > div::before { content: 'Carregue o arquivo ou solte aqui' !important; font-size: 14px !important; color: #555 !important; display: block !important; margin-bottom: 5px !important; }
        [data-testid='stFileUploader'] section > div > div::after { content: 'Limite de 200MB' !important; font-size: 12px !important; color: #888 !important; display: block !important; margin-top: 5px !important; }
        .stButton button { width: 100%; }
        .semana-destaque { background-color: #f0f2f6; padding: 10px; border-radius: 5px; }
        div[data-testid="column"] div[data-testid="stDateInput"] {
            min-width: 150px;
        }
        div[data-testid="column"]:nth-of-type(2) div[data-testid="stButton"] {
            margin-top: 0px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🎓 Gerador de Plano de Ensino Institucional - UENF")

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
    dados_iniciais = [{"Semana": str(i), "Data": "", "Duração": "2 h", "Conteúdo": "", "Estratégia Didática": "", "Avaliação": ""} for i in range(1, 18)]
    dados_iniciais.append({
        "Semana": "17",
        "Data": "",
        "Duração": "2 h",
        "Conteúdo": "Prova Final",
        "Estratégia Didática": "Avaliação Escrita",
        "Avaliação": "Prova"
    })
    st.session_state.df_cronograma = pd.DataFrame(dados_iniciais)
    st.session_state['editor_counter'] = 0

# --- FUNÇÕES DE SALVAR, CARREGAR E RESETAR ---
def obter_dados_completos():
    df_salvar = st.session_state.df_cronograma.copy()
    if 'Data' in df_salvar.columns:
        df_salvar['Data'] = df_salvar['Data'].apply(converter_data_para_string)

    extras_salvar = st.session_state.extras.copy()
    if extras_salvar.get('data_exame') and isinstance(extras_salvar['data_exame'], date):
        extras_salvar['data_exame'] = extras_salvar['data_exame'].strftime("%d/%m/%Y")

    return {
        "gerais": st.session_state.gerais,
        "extras": extras_salvar,
        "cronograma": df_salvar.to_dict(orient='records')
    }

def carregar_projeto(arquivo_json):
    dados = json.load(arquivo_json)
    for chave in st.session_state.gerais.keys():
        st.session_state.gerais[chave] = dados.get("gerais", {}).get(chave, st.session_state.gerais[chave])

    for chave in st.session_state.extras.keys():
        valor = dados.get("extras", {}).get(chave, st.session_state.extras[chave])
        if chave == "data_exame" and valor and isinstance(valor, str):
            try:
                valor = datetime.strptime(valor, "%d/%m/%Y").date()
            except:
                pass
        st.session_state.extras[chave] = valor

    if not st.session_state.extras.get("obs_faltas"): st.session_state.extras["obs_faltas"] = TEXTO_FALTAS_PADRAO
    if not st.session_state.extras.get("obs_recomenda"): st.session_state.extras["obs_recomenda"] = TEXTO_RECOMENDA_PADRAO

    if "cronograma" in dados:
        df_carregado = pd.DataFrame(dados["cronograma"])
        if 'Metodologia' in df_carregado.columns:
            df_carregado.rename(columns={'Metodologia': 'Estratégia Didática'}, inplace=True)
        for col in ["Semana", "Data", "Duração", "Conteúdo", "Estratégia Didática", "Avaliação"]:
            if col not in df_carregado.columns:
                df_carregado[col] = ""
        st.session_state.df_cronograma = df_carregado

    st.success("Projeto carregado com sucesso!")

def resetar_projeto():
    for key in ['gerais', 'extras', 'df_cronograma', 'pdf_buffer', 'editor_counter']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# --- FUNÇÕES PDF ---
def desenhar_cabecalho_rodape(canvas, doc):
    canvas.saveState()
    largura, altura = landscape(A4)
    if os.path.exists("brasao_rj.png"):
        canvas.drawImage("brasao_rj.png", (largura - 35) / 2.0, altura - 45, width=35, height=35, preserveAspectRatio=True, mask='auto')
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(largura / 2.0, altura - 55, "GOVERNO DO ESTADO DO RIO DE JANEIRO")
    canvas.drawCentredString(largura / 2.0, altura - 65, "UNIVERSIDADE ESTADUAL DO NORTE FLUMINENSE DARCY RIBEIRO")
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(largura / 2.0, 30, f"Página {doc.page}")
    if os.path.exists("logo_uenf.png"):
        canvas.drawImage("logo_uenf.png", 40, 20, width=80, height=40, preserveAspectRatio=True, mask='auto')
    if os.path.exists("logo_prograd.png"):
        canvas.drawImage("logo_prograd.png", largura - 120, 20, width=80, height=40, preserveAspectRatio=True, mask='auto')
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

    estilo_caixa = ParagraphStyle(name='CaixaTexto', parent=estilos['Normal'], alignment=TA_JUSTIFY, leading=14)
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

    # --- TÍTULO ---
    elementos.append(Paragraph(f"Plano de Ensino: {texto_seguro(gerais.get('disciplina', ''))}", estilo_titulo))
    elementos.append(Spacer(1, 15))

    # --- CABEÇALHO EM 2 COLUNAS ---
    estilo_info = ParagraphStyle(name='InfoTexto', parent=estilos['Normal'], fontSize=10, leading=14)
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
        exame_texto = "<b>Exame Final:</b> Não aplicável a esta disciplina"

    dados_header = [
        [Paragraph(f"<b>Código / Turma:</b> {texto_seguro(gerais.get('codigo', ''))} - {texto_seguro(gerais.get('turma', ''))}", estilo_info),
         Paragraph(f"<b>Semestre/Ano:</b> {texto_seguro(gerais.get('semestre', ''))}", estilo_info)],
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

    # --- EMENTA E OBJETIVOS ---
    elementos.append(criar_faixa_azul("Ementa"))
    elementos.append(criar_caixa_texto(texto_seguro(gerais.get('ementa', ''))))
    elementos.append(Spacer(1, 15))

    elementos.append(criar_faixa_azul("Objetivo Geral"))
    elementos.append(criar_caixa_texto(texto_seguro(gerais.get('objetivo', ''))))
    elementos.append(Spacer(1, 20))

    # --- CRONOGRAMA DE AULAS ---
    elementos.append(PageBreak())
    elementos.append(criar_faixa_azul("Cronograma de Aulas"))

    dados_tabela = [["Semana", "Data", "Duração", "Conteúdo Programático", "Estratégia Didática", "Avaliações / Entregas"]]

    semanas_unicas = df_cronograma['Semana'].unique()
    semana_para_cor = {}
    cores = [colors.white, colors.HexColor("#F5F5F5")]

    for i, semana in enumerate(semanas_unicas):
        semana_para_cor[semana] = cores[i % 2]

    contagem_semanas = df_cronograma['Semana'].value_counts().to_dict()

    estilo_grid = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]

    linha_atual = 1
    semana_anterior = None
    primeira_linha_semana = {}

    for index, row in df_cronograma.iterrows():
        semana = str(row.get('Semana', '')).strip()
        if semana and semana not in primeira_linha_semana:
            primeira_linha_semana[semana] = linha_atual
        linha_atual += 1

    linha_atual = 1

    for index, row in df_cronograma.iterrows():
        semana = str(row.get('Semana', '')).strip()
        semana = '' if semana.lower() in ['nan', 'none', ''] else semana

        if semana and semana in semana_para_cor:
            cor_fundo = semana_para_cor[semana]
        else:
            cor_fundo = colors.white

        estilo_grid.append(('BACKGROUND', (0, linha_atual), (-1, linha_atual), cor_fundo))

        if semana == semana_anterior:
            semana_display = ''
        else:
            semana_display = semana
            semana_anterior = semana

        data = str(row.get('Data', '')).strip()
        data = '' if data.lower() in ['nan', 'none', ''] else data

        duracao = str(row.get('Duração', '')).strip()
        duracao = '' if duracao.lower() in ['nan', 'none', ''] else duracao

        conteudo = str(row.get('Conteúdo', '')).strip()
        conteudo = '' if conteudo.lower() in ['nan', 'none', ''] else conteudo
        conteudo_para_tabela = Paragraph(conteudo.replace('\n', '<br/>'), estilo_tabela) if conteudo else ''

        estrategia = str(row.get('Estratégia Didática', '')).strip()
        estrategia = '' if estrategia.lower() in ['nan', 'none', ''] else estrategia
        estrategia_para_tabela = Paragraph(estrategia.replace('\n', '<br/>'), estilo_tabela) if estrategia else ''

        avaliacao = str(row.get('Avaliação', '')).strip()
        avaliacao = '' if avaliacao.lower() in ['nan', 'none', ''] else avaliacao
        avaliacao_para_tabela = Paragraph(avaliacao.replace('\n', '<br/>'), estilo_tabela) if avaliacao else ''

        dados_tabela.append([
            semana_display,
            data,
            duracao,
            conteudo_para_tabela,
            estrategia_para_tabela,
            avaliacao_para_tabela
        ])

        linha_atual += 1

    for semana, primeira_linha in primeira_linha_semana.items():
        if contagem_semanas.get(semana, 0) > 1:
            ultima_linha = primeira_linha + contagem_semanas[semana] - 1
            estilo_grid.append(('SPAN', (0, primeira_linha), (0, ultima_linha)))
            estilo_grid.append(('VALIGN', (0, primeira_linha), (0, ultima_linha), 'MIDDLE'))

    estilo_grid.extend([
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 1.0, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ])

    larguras_colunas_crono = [
        largura_util * 0.07,
        largura_util * 0.10,
        largura_util * 0.07,
        largura_util * 0.32,
        largura_util * 0.24,
        largura_util * 0.20
    ]

    tabela_crono = Table(dados_tabela, colWidths=larguras_colunas_crono, repeatRows=1)
    tabela_crono.setStyle(TableStyle(estilo_grid))

    elementos.append(tabela_crono)
    elementos.append(Spacer(1, 25))

    # --- AVALIAÇÃO E BIBLIOGRAFIA ---
    elementos.append(criar_faixa_azul("Sistema de Avaliação"))
    elementos.append(criar_caixa_texto(texto_seguro(extras['criterios'])))
    elementos.append(Spacer(1, 15))

    elementos.append(criar_faixa_azul("Bibliografia Básica"))
    elementos.append(criar_caixa_texto(texto_seguro(extras['bib_basica'])))
    elementos.append(Spacer(1, 15))

    elementos.append(criar_faixa_azul("Bibliografia Complementar"))
    elementos.append(criar_caixa_texto(texto_seguro(extras['bib_complementar'])))

    # --- PÁGINA FINAL ---
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
    arquivo_upload = st.file_uploader("Carregar projeto salvo (.json)", type=["json"])
    if arquivo_upload:
        if st.button("Restaurar Dados"):
            carregar_projeto(arquivo_upload)
            st.rerun()

    st.divider()
    nome_arquivo_final = f"Plano_de_Ensino_{st.session_state.gerais['codigo'].strip().replace(' ', '_')}_{st.session_state.gerais['semestre'].strip().replace('/', '_')}"
    st.download_button(label="💾 Salvar Projeto (JSON)", data=json.dumps(obter_dados_completos(), indent=4, ensure_ascii=False), file_name=f"{nome_arquivo_final}.json", mime="application/json")

    st.divider()
    st.header("📄 Novo Plano")
    with st.expander("✨ Começar um Novo Plano"):
        if st.button("🗑️ Limpar Tudo"):
            resetar_projeto()

    # --- FERIADOS 2026 ---
    st.sidebar.divider()
    with st.sidebar.expander("📅 Feriados 2026"):
        # Nova estrutura: (Nome do Mês, {dia: "Nome do Feriado"})
        meses_feriados = [
            ("Janeiro", {1: "Confrat. Universal", 15: "Santo Amaro"}),
            ("Fevereiro", {}),
            ("Abril", {21: "Tiradentes", 23: "São Jorge (RJ)"}),
            ("Maio", {1: "Dia do Trabalho"}),
            ("Julho", {}),
            ("Agosto", {6: "São Salvador"}),
            ("Setembro", {7: "Independência"}),
            ("Outubro", {12: "Nossa Sra. Aparecida"}),
            ("Novembro", {2: "Finados", 15: "Proclamação República",20: "Consciência Negra"}),
            ("Dezembro", {25: "Natal"})
        ]

        pascoa = calcular_pascoa(2026)
        carnaval = pascoa - timedelta(days=47)
        corpus = pascoa + timedelta(days=60)
        sexta_santa = pascoa - timedelta(days=2) # Adicionada Sexta-feira Santa

        st.write("**Feriados Fixos:**")
        for mes_nome, feriados in meses_feriados:
            for dia, nome_feriado in feriados.items():
                # Formata como: 21/Abr - Tiradentes
                st.write(f"  • {dia:02d}/{mes_nome[:3]} - {nome_feriado}")

        st.write("**Feriados Móveis:**")
        st.write(f"  • {carnaval.strftime('%d/%m')} - Carnaval")
        st.write(f"  • {sexta_santa.strftime('%d/%m')} - Sexta-feira Santa")
        st.write(f"  • {pascoa.strftime('%d/%m')} - Páscoa")
        st.write(f"  • {corpus.strftime('%d/%m')} - Corpus Christi")

    # --- LOGOS INSTITUCIONAIS ---
    st.sidebar.divider()

    # CSS aprimorado para forçar a centralização do widget de imagem do Streamlit
    st.sidebar.markdown("""
        <style>
            /* Alinha o container principal */
            .logo-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                width: 100%;
            }

            /* Força os widgets de imagem do Streamlit a centralizarem seu conteúdo */
            [data-testid="stSidebar"] [data-testid="stImage"] {
                display: flex;
                justify-content: center;
                margin-bottom: 40px; /* Aumenta a distância entre os logos */
                margin-left: 50px;
                width: 100%;
            }

            /* Remove a margem do último logo para não sobrar espaço embaixo */
            [data-testid="stSidebar"] [data-testid="stImage"]:last-child {
                margin-bottom: 0px;
            }
        </style>
    """, unsafe_allow_html=True)

    # Renderização na Sidebar
    with st.sidebar:
        # Abrimos um container div para envolver os elementos
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)

        # Logo ProGrad
        if os.path.exists("logo_prograd_1.png"):
            st.image("logo_prograd_1.png", width=160) # Aumentei um pouco para melhor leitura

        # Logo UENF
        if os.path.exists("logo_uenf.png"):
            st.image("logo_uenf.png", width=120)

        st.markdown('</div>', unsafe_allow_html=True)

    # --- GERAÇÃO RÁPIDA NA SIDEBAR ---
    st.sidebar.divider()
    st.sidebar.markdown("### ⚡ Geração Rápida")

    col_sb1, col_sb2 = st.sidebar.columns(2)
    with col_sb1:
        if st.sidebar.button("34h (1 aula/semana)", use_container_width=True):
            df_auto = gerar_cronograma_automatico(34)
            if df_auto is not None:
                st.session_state.df_cronograma = df_auto
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.sidebar.success("Cronograma 34h gerado!")
                st.rerun()

    with col_sb2:
        if st.sidebar.button("68h (2 aulas/semana)", use_container_width=True):
            df_auto = gerar_cronograma_automatico(68)
            if df_auto is not None:
                st.session_state.df_cronograma = df_auto
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.sidebar.success("Cronograma 68h gerado!")
                st.rerun()

    col_sb3, col_sb4 = st.sidebar.columns(2)
    with col_sb3:
        if st.sidebar.button("102h (3 aulas/semana)", use_container_width=True):
            df_auto = gerar_cronograma_automatico(102)
            if df_auto is not None:
                st.session_state.df_cronograma = df_auto
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.sidebar.success("Cronograma 102h gerado!")
                st.rerun()

    with col_sb4:
        if st.sidebar.button("Reset (1 aula/semana)", use_container_width=True):
            dados_iniciais = [{"Semana": str(i), "Data": "", "Duração": "2 h",
                              "Conteúdo": "", "Estratégia Didática": "", "Avaliação": ""}
                             for i in range(1, 18)]
            dados_iniciais.append({
                "Semana": "17",
                "Data": "",
                "Duração": "2 h",
                "Conteúdo": "Prova Final",
                "Estratégia Didática": "Avaliação Escrita",
                "Avaliação": "Prova"
            })
            st.session_state.df_cronograma = pd.DataFrame(dados_iniciais)
            st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
            st.sidebar.success("Resetado!")
            st.rerun()

# --- INTERFACE PRINCIPAL ---
st.subheader("1. Informações Gerais")

c1, c2, c3 = st.columns([2, 1, 1])
st.session_state.gerais['disciplina'] = c1.text_input("Disciplina", st.session_state.gerais.get('disciplina', ''))
st.session_state.gerais['codigo'] = c2.text_input("Código", st.session_state.gerais.get('codigo', ''))
st.session_state.gerais['turma'] = c3.text_input("Turma", st.session_state.gerais.get('turma', ''))

c4, c5 = st.columns([1, 1])
st.session_state.gerais['professor'] = c4.text_input("Professor(a)", st.session_state.gerais.get('professor', ''))
st.session_state.gerais['coordenador'] = c5.text_input("Coordenador(a) (Deixe em branco se não houver)", st.session_state.gerais.get('coordenador', ''))

c6, c7 = st.columns([1, 1])
st.session_state.gerais['laboratorio'] = c6.text_input("Laboratório", st.session_state.gerais.get('laboratorio', ''))
st.session_state.gerais['semestre'] = c7.text_input("Semestre/Ano", st.session_state.gerais.get('semestre', ''))

st.session_state.gerais['ementa'] = st.text_area("Ementa", st.session_state.gerais.get('ementa', ''))
st.session_state.gerais['objetivo'] = st.text_area("Objetivo Geral", st.session_state.gerais.get('objetivo', ''))

st.divider()

# --- SEÇÃO DE CARGA HORÁRIA E GERAÇÃO AUTOMÁTICA ---
st.subheader("1.1 Configuração de Carga Horária")

c8, c9, c10 = st.columns([1, 1, 1])
with c8:
    opcoes_carga = ["", "34", "51", "68", "85", "102"]
    carga_atual = st.session_state.gerais.get('carga_horaria', '')
    indice_carga = 0
    if carga_atual in opcoes_carga:
        indice_carga = opcoes_carga.index(carga_atual)

    carga_selecionada = st.selectbox(
        "Carga Horária Total",
        opcoes_carga,
        key="carga_select",
        index=indice_carga
    )
    st.session_state.gerais['carga_horaria'] = carga_selecionada

    if carga_selecionada:
        descricao = get_descricao_carga(carga_selecionada)
        st.caption(f"📋 {descricao}")

with c9:
    extensao_atual = st.session_state.gerais.get('horas_extensao', 0)
    st.session_state.gerais['horas_extensao'] = st.number_input(
        "Horas de Extensão",
        min_value=0,
        max_value=100,
        value=int(extensao_atual) if extensao_atual else 0,
        step=1
    )

with c10:
    st.session_state.gerais['tipo_aprovacao'] = st.selectbox(
        "Tipo de Aprovação",
        ["Média e frequência", "Só frequência"],
        index=0 if st.session_state.gerais.get('tipo_aprovacao', 'Média e frequência') == 'Média e frequência' else 1
    )

col_auto1, col_auto2, col_auto3 = st.columns([1, 1, 2])
with col_auto1:
    if st.button("⚡ Gerar Estrutura Automática", type="primary", use_container_width=True):
        if st.session_state.gerais['carga_horaria']:
            df_auto = gerar_cronograma_automatico(st.session_state.gerais['carga_horaria'])
            if df_auto is not None:
                st.session_state.df_cronograma = df_auto
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.success(f"✅ Estrutura gerada para {st.session_state.gerais['carga_horaria']}h!")
                st.rerun()
            else:
                st.info(f"ℹ️ {st.session_state.gerais['carga_horaria']}h: preenchimento manual. Use o botão 'Inserir Linha' para adicionar atividades.")
        else:
            st.warning("⚠️ Selecione uma carga horária primeiro!")

with col_auto2:
    if st.button("🔄 Resetar para 1 por semana", use_container_width=True):
        dados_iniciais = [{"Semana": str(i), "Data": "", "Duração": "2 h",
                          "Conteúdo": "", "Estratégia Didática": "", "Avaliação": ""}
                         for i in range(1, 18)]
        dados_iniciais.append({
            "Semana": "17",
            "Data": "",
            "Duração": "2 h",
            "Conteúdo": "Prova Final",
            "Estratégia Didática": "Avaliação Escrita",
            "Avaliação": "Prova"
        })
        st.session_state.df_cronograma = pd.DataFrame(dados_iniciais)
        st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
        st.success("Tabela resetada para 1 atividade por semana!")
        st.rerun()

with col_auto3:
    cargas_auto = get_cargas_com_auto()
    st.caption(f"✨ Geração automática disponível para: {', '.join(map(str, cargas_auto))}h")

if st.session_state.gerais['carga_horaria']:
    faltas_max, dias_falta = calcular_faltas_permitidas(st.session_state.gerais['carga_horaria'])
    st.info(f"📊 **Informações de Frequência:** Carga horária: {st.session_state.gerais['carga_horaria']}h | Máximo de faltas: {faltas_max}h ({dias_falta} dias de 2h)")

st.divider()

# --- CRONOGRAMA DE AULAS ---
st.subheader("2. Cronograma de Aulas")
st.write("📅 Clique no campo de data para abrir o calendário!")

opcoes_duracao = ["", "2 h", "3 h", "4 h"]
opcoes_estrategia = ["", "Aula Expositiva Dialogada", "Resolução de Exercícios / Problemas", "Aula Prática em Laboratório",
                     "Sala de Aula Invertida", "Apresentação de Seminários", "Estudo Dirigido / Leitura de Texto",
                     "Discussão em Grupo / Debate", "Trabalho de campo", "Atividade extensionista",
                     "Avaliação Escrita / Prova", "Outra"]
opcoes_avaliacao = ["", "Nenhuma", "Prova 1", "Prova 2", "Prova 3", "Prova", "Relatório", "Lista de exercício",
                    "Seminário", "Teste online", "Teste", "Trabalho", "Participação", "Projeto Prático",
                    "Apresentação Oral", "Outra"]

df_para_edicao = st.session_state.df_cronograma.copy()

if 'Data' in df_para_edicao.columns:
    df_para_edicao['Data'] = df_para_edicao['Data'].apply(converter_string_para_data)

df_editado = st.data_editor(
    df_para_edicao,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=False,
    key=f"data_editor_{st.session_state.get('editor_counter', 0)}",
    column_config={
        "Semana": st.column_config.TextColumn("Semana", required=False),
        "Data": st.column_config.DateColumn(
            "Data",
            format="DD/MM/YYYY",
            min_value=date(2020, 1, 1),
            max_value=date(2030, 12, 31),
            step=1,
            required=False
        ),
        "Duração": st.column_config.SelectboxColumn("Duração", options=opcoes_duracao, required=False),
        "Conteúdo": st.column_config.TextColumn("Conteúdo", required=False),
        "Estratégia Didática": st.column_config.SelectboxColumn("Estratégia Didática", options=opcoes_estrategia, required=False),
        "Avaliação": st.column_config.SelectboxColumn("Avaliação", options=opcoes_avaliacao, required=False)
    }
)

col_salvar, col_recarregar, col_espaco = st.columns([1, 1, 4])
with col_salvar:
    if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
        df_salvar = df_editado.copy()
        if 'Data' in df_salvar.columns:
            df_salvar['Data'] = df_salvar['Data'].apply(converter_data_para_string)
        st.session_state.df_cronograma = df_salvar
        st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
        st.success("Tabela salva com sucesso!")
        st.rerun()

with col_recarregar:
    if st.button("↻ Recarregar", use_container_width=True):
        st.rerun()

with st.expander("👁️ Preview do Cronograma (com cores por semana)"):
    preview_df = st.session_state.df_cronograma.copy()

    def color_semanas(row):
        semanas_unicas = preview_df['Semana'].unique()
        semana_atual = row['Semana']
        if semana_atual in semanas_unicas:
            idx = list(semanas_unicas).index(semana_atual)
            if idx % 2 == 0:
                return ['background-color: #ffffff'] * len(row)
            else:
                return ['background-color: #f5f5f5'] * len(row)
        return [''] * len(row)

    styled_df = preview_df.style.apply(color_semanas, axis=1)
    st.dataframe(styled_df, use_container_width=True)

st.markdown("#### ➕ Inserir Aula Agrupada na Mesma Semana")
col_add_select, col_add_button, col_add_info = st.columns([2, 1, 2])
semanas_existentes = st.session_state.df_cronograma['Semana'].unique().tolist()
semanas_existentes = [s for s in semanas_existentes if str(s).strip() != ""]

if semanas_existentes:
    with col_add_select:
        semana_selecionada = st.selectbox("Escolha a semana:", semanas_existentes, key="semana_select", label_visibility="collapsed")

    with col_add_button:
        if st.button("➕ Inserir Linha", use_container_width=True):
            df_atual = st.session_state.df_cronograma.copy()
            indices = df_atual[df_atual['Semana'] == semana_selecionada].index
            if len(indices) > 0:
                ultimo_indice = indices[-1]
                nova_linha = pd.DataFrame([{
                    "Semana": semana_selecionada,
                    "Data": "",
                    "Duração": "2 h",
                    "Conteúdo": "",
                    "Estratégia Didática": "",
                    "Avaliação": ""
                }])
                df_topo = df_atual.iloc[:ultimo_indice+1]
                df_fundo = df_atual.iloc[ultimo_indice+1:]
                st.session_state.df_cronograma = pd.concat([df_topo, nova_linha, df_fundo], ignore_index=True)
                st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
                st.success("Linha inserida!")
                st.rerun()

    with col_add_info:
        df_atual = st.session_state.df_cronograma
        qtd_atividades = len(df_atual[df_atual['Semana'] == semana_selecionada]) if semana_selecionada in df_atual['Semana'].values else 0
        st.info(f"Semana {semana_selecionada} tem {qtd_atividades} atividade(s)")
else:
    col_add_select.warning("Adicione semanas primeiro")

with st.expander("⚙️ Opções Avançadas"):
    if st.button("Resetar para 17 semanas (vazio)"):
        dados_iniciais = [{"Semana": str(i), "Data": "", "Duração": "2 h", "Conteúdo": "", "Estratégia Didática": "", "Avaliação": ""} for i in range(1, 18)]
        st.session_state.df_cronograma = pd.DataFrame(dados_iniciais)
        st.session_state['editor_counter'] = st.session_state.get('editor_counter', 0) + 1
        st.success("Tabela resetada!")
        st.rerun()

st.divider()

# --- EXAME FINAL, AVALIAÇÃO E BIBLIOGRAFIA ---
st.subheader("3. Exame Final, Avaliação e Bibliografia")
col_exame1, col_exame2 = st.columns([1, 2])
with col_exame1:
    tem_exame = st.radio("Há Exame Final?", ["Sim", "Não"], index=0 if st.session_state.extras.get('tem_exame', True) else 1)
    st.session_state.extras['tem_exame'] = (tem_exame == "Sim")
with col_exame2:
    if st.session_state.extras['tem_exame']:
        data_exame_atual = st.session_state.extras.get('data_exame')
        if isinstance(data_exame_atual, str):
            try:
                data_exame_atual = datetime.strptime(data_exame_atual, "%d/%m/%Y").date()
            except:
                data_exame_atual = None
        elif not isinstance(data_exame_atual, date):
            data_exame_atual = None

        st.session_state.extras['data_exame'] = st.date_input(
            "Data do Exame Final",
            value=data_exame_atual,
            min_value=date(2020, 1, 1),
            max_value=date(2030, 12, 31),
            format="DD/MM/YYYY"
        )
    else:
        st.info("Exame Final: Não aplicável")

st.session_state.extras['criterios'] = st.text_area("Critérios de Avaliação", st.session_state.extras.get('criterios', ''))
st.session_state.extras['bib_basica'] = st.text_area("Bibliografia Básica", st.session_state.extras.get('bib_basica', ''))
st.session_state.extras['bib_complementar'] = st.text_area("Bibliografia Complementar", st.session_state.extras.get('bib_complementar', ''))

st.divider()

# --- OBSERVAÇÕES ---
st.subheader("4. Observações e Instruções")

col_atualizar1, col_atualizar2 = st.columns([1, 3])
with col_atualizar1:
    if st.button("🔄 Atualizar Texto de Faltas", use_container_width=True):
        if st.session_state.gerais.get('carga_horaria'):
            st.session_state.extras['obs_faltas'] = atualizar_texto_faltas(st.session_state.gerais['carga_horaria'])
            st.success("Texto atualizado!")
            st.rerun()

with col_atualizar2:
    st.caption("Clique para gerar texto automático baseado na carga horária selecionada")

st.session_state.extras['obs_faltas'] = st.text_area(
    "Regras de Frequência e Faltas",
    st.session_state.extras.get('obs_faltas', ''),
    height=250
)

st.session_state.extras['obs_recomenda'] = st.text_area(
    "Recomendações para o Sucesso",
    st.session_state.extras.get('obs_recomenda', ''),
    height=150
)

st.divider()

# --- GERAR PDF ---
st.subheader("📄 Gerar e Baixar PDF UENF")

if st.button("🔄 1. Atualizar e Gerar PDF", use_container_width=True):
    with st.spinner("Gerando PDF..."):
        st.session_state.pdf_buffer = gerar_pdf_buffer(st.session_state.gerais, st.session_state.df_cronograma, st.session_state.extras)
        if st.session_state.pdf_buffer:
            st.success("✅ PDF gerado com sucesso!")

if 'pdf_buffer' in st.session_state and st.session_state.pdf_buffer is not None:
    st.download_button(
        label="📥 2. Baixar PDF Final",
        data=st.session_state.pdf_buffer,
        file_name=f"{nome_arquivo_final}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

st.divider()

# --- SAIR ---
st.subheader("🚪 Encerrar Sistema")
if st.button("Sair do Programa", use_container_width=True):
    st.error("Desligando o gerador... Você já pode fechar esta aba.")
    time.sleep(2)
    os._exit(0)
