# app.py
import streamlit as st
import pandas as pd
import datetime
import unicodedata
import os
from streamlit_gsheets import GSheetsConnection

from correcoes_nomes import nomes_cursos_substituicoes
from streamlit import config as _config
_config.set_option("theme.base", "light")

# Função para formatar nomes com acento e capitalização correta
def formatar_nome(x):
    x = str(x).strip().upper()
    return nomes_cursos_substituicoes.get(x, x).upper()

# Funções auxiliares
def calcular_chm(tipo_curso, tipo_oferta, nome_curso, chc, chmc):
    tipo_curso_upper = tipo_curso.upper()
    nome_curso_upper = nome_curso.upper()
    tipo_oferta_upper = str(tipo_oferta).strip().upper()


    if tipo_curso_upper in ["QUALIFICACAO PROFISSIONAL (FIC)", "DOUTORADO"]:
        return chc
    elif "PROEJA" in tipo_oferta_upper:
        return 2400
    elif tipo_oferta_upper == "INTEGRADO":
        if chmc == 800:
            return 3000
        elif chmc == 1000:
            return 3100
        elif chmc == 1200:
            return 3200
        else:
            return chmc
    else:
        return chmc


# Função carregar_dados ATUALIZADA
@st.cache_data(ttl=600) # ttl=600 limpa o cache a cada 10 min para atualizar dados se mudar na planilha
def carregar_dados():
    # Cria a conexão usando os segredos que configuramos
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Lê os dados da planilha
    # header=2 equivale ao skiprows=2 (considera que o cabeçalho real está na linha 3 do Sheets - índice 2)
    df = conn.read(header=2)
    
    # --- AQUI ENTRA SEU BLOCO DE LIMPEZA E PADRONIZAÇÃO (Aquele código novo) ---
    if 'Nome do curso' in df.columns:
        df = df[df['Nome do curso'].notnull()]
        
        siglas_alvo = [
            "DIC", "DTC", "CHC", "CHMC", "CHM", "PC", 
            "QTDC", "CHMD", "CHA", "FECH", 
            "DIP", "DFP", "QTM1P", "DACP", 
            "FEDA", "FECHDA", "MECHDA", "MP", "BA", "MT"
        ]
        
        novos_nomes = {}
        for col in df.columns:
            primeiro_token = str(col).strip().split()[0]
            primeiro_token_limpo = primeiro_token.strip()
            eh_sigla = any(primeiro_token_limpo.startswith(sigla) for sigla in siglas_alvo)
            
            if eh_sigla:
                novos_nomes[col] = primeiro_token_limpo
            else:
                novos_nomes[col] = ' '.join(str(col).split())

        df = df.rename(columns=novos_nomes)
        
    return df

# --- No corpo principal do código ---
try:
    df = carregar_dados()
except Exception as e:
    st.error("Erro ao conectar com a Planilha do Google. Verifique os Secrets.")
    st.exception(e)
    st.stop()

st.markdown("""
    <style>         
    .custom-header h1 {
        font-family: "Open Sans", Arial, Helvetica, sans-serif;
        font-size: 2.55em;
        line-height: 1em;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 5px;
        color: #195128;
    }
    .custom-header h4 {
        font-family: "Open Sans", Arial, Helvetica, sans-serif;
        font-size: 1.5em;
        color: #195128;
        margin-top: 0;
        font-weight: 300;
    }
    
    .custom-bar {
        background-color: #004d0d; /* verde escuro sólido */
        height: 1px;
        width: 100%;
        margin-bottom: 20px;
    }            
    

        
    </style>

    <div class="custom-header">
        <h1>Instituto Federal Farroupilha</h1>
        <h4>Calculadora de Matrículas Totais</h4>
    </div>

    <div class="custom-bar"></div>
""", unsafe_allow_html=True)

if "exibir_alerta" not in st.session_state:
    st.session_state["exibir_alerta"] = True

if st.session_state["exibir_alerta"]:
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.markdown("""
        <div style="
            border-left: 5px solid #ffc107;
            background-color: #fff8e1;
            padding: 15px;
            margin-top: -10px;
            margin-bottom: 25px;
            border-radius: 6px;
            font-size: 0.95rem;
            color: #5d4500;
        ">
            ⚠️ Esta ferramenta é um instrumento de apoio e deve ser usada com cautela ao comparar cursos. Sempre revise as informações utilizadas, especialmente no que se refere à <strong>carga horária</strong>, <strong>datas de início e fim de ciclo</strong> e o <strong>ano base</strong> considerado para análise.<br><br>
    Os dados pré-preenchidos são provenientes dos microdados da Plataforma Nilo Peçanha - PNP 2024 (Ano Base 2023) e foram utilizados no cálculo da Matriz Orçamentária 2025. A Pesquisa Institucional identificou que há dados de carga horária cadastrados incorretamente no Sistec por alguns CRAs e por isso, afetaram diretamente o cálculo apresentado.
</div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("X", key="fechar_alerta"):
            st.session_state["exibir_alerta"] = False



# Seção 1 - Selecione o Curso
st.header("Curso")


# Campus
campus = st.selectbox("Campus:", df['Unidade de Ensino'].unique(), format_func=formatar_nome)
df_filtrado_campus = df[df['Unidade de Ensino'] == campus]

# Tipo de Curso
tipo_curso = st.selectbox("Tipo de Curso:", df_filtrado_campus['Tipo de Curso'].unique(), format_func=formatar_nome)
df_filtrado_tipo = df_filtrado_campus[df_filtrado_campus['Tipo de Curso'] == tipo_curso]

# Se for TÉCNICO → mostrar Tipo de Oferta
if tipo_curso.upper() == "TECNICO":
    tipo_oferta_selecionado = st.selectbox("Tipo de Oferta:", df_filtrado_tipo['Tipo de Oferta'].unique())
    
    # Filtrar pelo Tipo de Oferta
    df_filtrado_tipo_oferta = df_filtrado_tipo[df_filtrado_tipo['Tipo de Oferta'] == tipo_oferta_selecionado]
    
    # Nome do Curso
    nome_curso_options = df_filtrado_tipo_oferta['Nome do curso'].unique().tolist()
    nome_curso = st.selectbox("Nome do Curso:", nome_curso_options, format_func=lambda x: formatar_nome(x) if x != "A DEFINIR" else x)
    

    # Definir linha_curso
    linha_curso = df_filtrado_tipo_oferta[df_filtrado_tipo_oferta['Nome do curso'].apply(lambda x: formatar_nome(x)) == formatar_nome(nome_curso)].copy()
    linha_curso['DIC'] = pd.to_datetime(linha_curso['DIC'], dayfirst=True, errors='coerce')
    linha_curso = linha_curso.sort_values(by='DIC', ascending=False).iloc[0]

else:
    # Para FIC → incluir "A DEFINIR"
    nome_curso_options = df_filtrado_tipo['Nome do curso'].unique().tolist()
    if tipo_curso.upper() == "QUALIFICACAO PROFISSIONAL (FIC)":
        nome_curso_options = ["A DEFINIR"] + nome_curso_options

    nome_curso = st.selectbox("Nome do Curso:", nome_curso_options, format_func=lambda x: formatar_nome(x) if x != "A DEFINIR" else x)

    # Definir linha_curso
    if nome_curso == "A DEFINIR":
        linha_curso = df_filtrado_tipo.copy()
        linha_curso['DIC'] = pd.to_datetime(linha_curso['DIC'], dayfirst=True, errors='coerce')
        linha_curso = linha_curso.sort_values(by='DIC', ascending=False).iloc[0]
    else:
        linha_curso = df_filtrado_tipo[df_filtrado_tipo['Nome do curso'].apply(lambda x: formatar_nome(x)) == formatar_nome(nome_curso)].copy()
        linha_curso['DIC'] = pd.to_datetime(linha_curso['DIC'], dayfirst=True, errors='coerce')
        linha_curso = linha_curso.sort_values(by='DIC', ascending=False).iloc[0]


# Seção 2 - Parâmetros do ciclo
st.header("Parâmetros do Ciclo")

# Datas
DIC = linha_curso['DIC'].date() if not pd.isnull(linha_curso['DIC']) else datetime.date.today()
DTC_raw = pd.to_datetime(linha_curso['DTC'], dayfirst=True, errors='coerce')
DTC = DTC_raw.date() if not pd.isnull(DTC_raw) else datetime.date.today()

DIC = st.date_input("Data de Início do Ciclo:", DIC, format="DD/MM/YYYY")
DTC = st.date_input("Data de Término do Ciclo:", DTC, format="DD/MM/YYYY")
if DTC <= DIC:
    st.error("⚠️ A Data de Término do Ciclo deve ser posterior à Data de Início.")

# CHC
chc = linha_curso['CHC']
chc = st.number_input("Carga Horária do Ciclo (CHC):", min_value=0, value=int(chc), step=10)

# CHMC e PC
chmc = linha_curso['CHMC']
pc = linha_curso['PC']
pc = float(str(pc).replace(',', '.'))

st.write(f"**PC (Peso do Curso):** {pc}")
st.write(f"**CHMC (Carga horária do Catálogo MEC):** {chmc}")

tipo_oferta = linha_curso['Tipo de Oferta']

# CHM calculada
chm = calcular_chm(tipo_curso, tipo_oferta, nome_curso, chc, chmc)
st.write(f"**CHM (Carga Horária para Matriz):** {chm}")

# Seção 3 - Período de Análise
st.header("Período de Análise")

ano_periodo = st.selectbox("Ano do Período:", list(range(2020, 2031)), index=4)

DIP = datetime.date(ano_periodo, 1, 1)
DFP = datetime.date(ano_periodo, 12, 31)

# Seção 4 - Matrículas e opções
st.header("Matrículas e Opções")
qtm_pre_preenchido = linha_curso['QTM1P']
qtm_pre_preenchido = 0 if pd.isnull(qtm_pre_preenchido) else qtm_pre_preenchido

#qtm = st.number_input("👥 Número de Matrículas Ativas no Período (QTM):", min_value=0, step=1)
qtm = st.number_input("Número de Matrículas Ativas no Período (QTM1P):", min_value=0, step=1, value=int(qtm_pre_preenchido))

agropecuaria_default = linha_curso['Curso de Agropecuária'].strip().capitalize()
agropecuaria = st.radio("Curso de Agropecuária?", ["Sim", "Não"], index=["Sim", "Não"].index(agropecuaria_default))

# Tipo de financiamento (editable)
tipo_financiamento_default = linha_curso['Situação de acordo com o tipo de financiamento']
tipo_financiamento = st.selectbox(" Modalidade / Tipo de Financiamento:", ["PRESENCIAL", "EAD FINANCIAMENTO EXTERNO", "EAD FINANCIAMENTO PRÓPRIO"], index=["PRESENCIAL", "EAD", "EAD FP"].index(tipo_financiamento_default) if tipo_financiamento_default in ["PRESENCIAL", "EAD", "EAD FP"] else 0)

# Seção 5 - Cálculo e Resultado
if 'calculado' not in st.session_state:
    st.session_state['calculado'] = False

st.markdown("""
    <style>
    /* Estiliza o st.button */
    .stButton > button {
        background-color: #17882c !important;
        color: white !important;
        font-size: 1.1em;
        font-weight: bold;
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        transition: background-color 0.3s ease;
        box-shadow: none !important; /* Zera o box-shadow */
        outline: none !important;     /* Remove a borda de foco */
    }

    .stButton > button:hover {
        background-color: #0f5e1f !important;
        box-shadow: none !important; /* Zera o box-shadow no hover */
        outline: none !important;
    }

    .stButton > button:active {
        background-color: #0f5e1f !important;
        box-shadow: none !important;
        outline: none !important;
    }

    .stButton > button:focus {
        background-color: #0f5e1f !important;
        box-shadow: none !important;
        outline: none !important;
    }
            

    </style>
""", unsafe_allow_html=True)



if st.button("🔍 Calcular Matrículas Totais"):
    st.session_state['calculado'] = True

if st.session_state['calculado']:

    QTDC = (DTC - DIC).days + 1
    CHMD = min(chm, chc) / QTDC
    CHA = CHMD * 365 if QTDC > 365 else chm
    FECH = CHA / 800 if QTDC > 365 else chc / 800

    DACP1 = (DFP - DIP).days + 1 if (DIC < DIP and DTC > DFP) else 0
    DACP2 = (DFP - DIC).days + 1 if (DIC >= DIP and DTC > DFP and DIC < DFP) else 0
    DACP3 = (DTC - DIP).days + 1 if (DIC < DIP and DTC <= DFP and DTC >= DIP) else 0
    DACP4 = (DTC - DIC).days + 1 if (DIC >= DIP and DTC <= DFP) else 0
    DACP5 = ((DFP - DIP).days + 1) / 2 if (DIC < DIP and DTC < DIP) else 0

    FEDA = (DACP1 + DACP2 + DACP3 + DACP4 + DACP5) / ((DFP - DIP).days + 1)
    FECHDA = FECH * FEDA


    if DACP5 == 0:
        MECHDA = FECHDA * qtm
    elif (DIP - DTC).days > 1095:
        MECHDA = 0
    else:
        MECHDA = FECHDA * (qtm / 2)

    MP = MECHDA * pc
    BA = MP * 0.5 if agropecuaria == "Sim" else 0

    if tipo_financiamento == "PRESENCIAL":
        MT = MP + BA
    elif tipo_financiamento == "EAD FINANCIAMENTO PRÓPRIO":
        CMTD80 = MP * 0.80
        MT = CMTD80
    elif tipo_financiamento == "EAD FINANCIAMENTO EXTERNO":
        CMTD25 = MP * 0.25
        MT = CMTD25

    # Resultados

    st.markdown(f"""
    <div style="
        border: 2px solid #17882c;
        border-radius: 10px;
        background-color: #e9f7ec;
        padding: 20px;
        margin-top: 20px;
        text-align: center;
    ">
        <span style="
            font-size: 2em;
            font-weight: 700;
            color: #17882c;
        ">
            MT (Matrículas Totais): {MT:.2f}
        </span>
    </div>
    """, unsafe_allow_html=True)

        # Cálculo do "cada matrícula corresponde a XX matrícula total"
    if qtm > 0:
        MT_por_matricula = MT / qtm
        st.markdown(f"""
        <div style="
            margin-top: 12px;
            margin-bottom: 12px;
            padding: 10px 15px;
            border-left: 5px solid #17882c;
            background-color: #f2faf4;
            font-size: 1.1em;
            color: #195128;
            font-weight: 600;
            border-radius: 6px;
            text-align: left;
            display: inline-block;
        ">
            📌 Cada matrícula corresponde a <b>{MT_por_matricula:.2f}</b> matrícula(s) total(is).
        </div>
        """, unsafe_allow_html=True)



    # Botão para mostrar detalhes
    if st.checkbox("Mostrar detalhes intermediários"):
        st.write(f"**QTDC (Quantidade de dias do Ciclo):** {QTDC}")
        st.write(f"**CHM (Carga Horária para Matriz):** {chm}")
        st.write(f"**CHMD (Carga Horária Média Diária):** {CHMD:.2f}")
        st.write(f"**CHA (Carga Horária Anualizada):** {CHA:.2f}")
        st.write(f"**FECH (Fator de Equalização de Carga Horária):** {FECH:.4f}")

        st.write(f"**DACP1 (Dias Ativos do Ciclo no Período 1 - começa antes do início do período e termina depois do final do período):** {DACP1}")
        st.write(f"**DACP2 (Dias Ativos do Ciclo no Período 2 - começa dentro do período e termina depois do final do período):** {DACP2}")
        st.write(f"**DACP3 (Dias Ativos do Ciclo no Período 3 - começa antes do início do período e termina antes do final do período):** {DACP3}")
        st.write(f"**DACP4 (Dias Ativos do Ciclo no Período 4 - começa depois do início do período e termina antes do final do período):** {DACP4}")
        st.write(f"**DACP5 (Dias Ativos do Ciclo no Período 5 - começa antes do início do período e termina antes do início do período):** {DACP5}")

        st.write(f"**FEDA (Fator de Equalização de Dias Ativos):** {FEDA:.4f}")
        st.write(f"**FECHDA (Fator de Equalização de Carga Horária e Dias Ativos):** {FECHDA:.4f}")
        st.write(f"**MECHDA (Matrículas Equalizadas por Carga Horária e Dias Ativos):** {MECHDA:.4f}")

        
        st.write(f"**BA (Bônus Agropecuária):** {BA:.2f}")

        if tipo_financiamento == "EAD FINANCIAMENTO EXTERNO":
            st.write(f"**CMTD25 (Matrícula EAD com fomento externo 25% da presencial):** {CMTD25:.2f}")
        elif tipo_financiamento == "EAD FINANCIAMENTO PRÓPRIO":
            st.write(f"**CMTD80 (Matrícula EAD fomento próprio 80% da presencial):** {CMTD80:.2f}")


# Rodapé
st.markdown("""
    <hr>
    <div style="text-align: left; font-size: small; color: gray;">
       <p> Ferramenta desenvolvida pela Diretoria de Planejamento e Desenvolvimento Institucional (DPDI) para apoio ao cálculo de matrículas totais no IFFarroupilha.
        Os dados foram retirados da planilha da Fase 4 da Matriz de Distribuição Orçamentária 2025 que usou dados da PNP Ano Base 2023. </p>
    </div>
""", unsafe_allow_html=True)
