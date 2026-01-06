import streamlit as st
import pandas as pd
import datetime
import warnings
import os
from streamlit_gsheets import GSheetsConnection


st.set_page_config(
    page_title="Calculadora Matrículas Totais",
    page_icon="📊",
    layout="wide"
)

image_file = "banner2.png"

if os.path.exists(image_file):
    st.image(image_file, width="stretch") 
else:
    st.write("# Calculadora de Matrículas Totais")

warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

try:
    from correcoes_nomes import nomes_cursos_substituicoes
except ImportError:
    nomes_cursos_substituicoes = {}

st.markdown("""
    <style>
    
    [data-testid="stAppViewContainer"] {
        background-color: #5FD967; 
        background-image: linear-gradient(135deg, #5FD967 0%, #1A7A6F 100%);
    }

    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0); 
        color: white;
    }
    
    
    [data-testid="stToolbar"] {
        right: 2rem;
    }
    
    .block-container {
        background-color: #FFFFFF;
        padding: 3rem 3rem;     
        border-radius: 20px;     
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        margin-top: 40px; 
        max-width: 900px;
    }
 
    h1, h2, h3, h4, p, span, div {
        color: #333333;
    }
    
    div.stButton > button:first-child {
        background-color: #39A46C; !important
        color: #FFFFFF; !important
        border-radius: 12px;
        border: none;
        height: 55px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    div.stButton > button:first-child p {
        color: #FFFFFF !important;
    }
            
    div.stButton > button:first-child:hover {
        background-color: #1a7a6f;
        color: #FFFFFF !important;
        border: none;
        transform: scale(1.02);
    }
            
    div.stButton > button:first-child:active, 
    div.stButton > button:first-child:focus {
        background-color: #107347 !important;
        color: #FFFFFF !important;
        box-shadow: none;
    }

    .block-container {
        padding-top: 2rem;
    }
    

    footer {visibility: hidden;}
    
    </style>
""", unsafe_allow_html=True)

# Gerenciamento de Estado para Navegação
if 'modo' not in st.session_state:
    st.session_state['modo'] = None

def set_modo(novo_modo):
    st.session_state['modo'] = novo_modo

# =======================================================
# 1. FUNÇÕES AUXILIARES E LÓGICA
# =======================================================

def formatar_nome(x):
    if pd.isnull(x): return ""
    x = str(x).strip().upper()
    return nomes_cursos_substituicoes.get(x, x).upper()

def calcular_chm(tipo_curso, tipo_oferta, chc, chmc):
    tipo_curso_upper = str(tipo_curso).upper() if pd.notnull(tipo_curso) else ""
    tipo_oferta_upper = str(tipo_oferta).strip().upper() if pd.notnull(tipo_oferta) else ""

    if tipo_curso_upper in ["QUALIFICACAO PROFISSIONAL (FIC)", "DOUTORADO"]:
        return chc
    elif "PROEJA" in tipo_oferta_upper:
        return 2400
    elif tipo_oferta_upper == "INTEGRADO":
        if chmc == 800: return 3000
        elif chmc == 1000: return 3100
        elif chmc == 1200: return 3200
        else: return chmc
    else:
        return chmc

def get_val(row, keys, default=None):
    if row is None: return default
    if isinstance(keys, str): keys = [keys]
    for k in keys:
        if k in row.index and pd.notnull(row[k]):
            return row[k]
    return default

def converter_para_data(valor):
    if pd.isnull(valor) or valor == "": return None
    if isinstance(valor, (pd.Timestamp, datetime.datetime)): return valor.date()
    if isinstance(valor, datetime.date): return valor
    try:
        dt = pd.to_datetime(valor, dayfirst=True, errors='coerce')
        return dt.date() if pd.notnull(dt) else None
    except:
        return None

def limpar_padronizar_dataframe(df):
    siglas_alvo = [
        "DIC", "DTC", "CHC", "CHMC", "CHM", "PC", 
        "QTDC", "CHMD", "CHA", "FECH", 
        "DIP", "DFP", "QTM1P", "QTM", "DACP", 
        "FEDA", "FECHDA", "MECHDA", "MP", "BA", "MT","Apto"
    ]
    novos_nomes = {}
    for col in df.columns:
        primeiro_token = str(col).strip().split()[0]
        primeiro_token_limpo = primeiro_token.strip()
        if any(primeiro_token_limpo.startswith(sigla) for sigla in siglas_alvo):
             novos_nomes[col] = primeiro_token_limpo
        else:
            novos_nomes[col] = ' '.join(str(col).split())
    df = df.rename(columns=novos_nomes)
    
    if 'Nome do curso' in df.columns:
        df = df[df['Nome do curso'].notnull()]
        df['Nome_Padronizado'] = df['Nome do curso'].apply(formatar_nome)
    else:
        df['Nome_Padronizado'] = "A DEFINIR"
    return df

@st.cache_data(ttl=600)
def carregar_dados_gsheets():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(header=2)
    df = limpar_padronizar_dataframe(df)
    return df

def carregar_dados_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        for nome_aba in xls.sheet_names:
            try:
                df_preview = pd.read_excel(xls, sheet_name=nome_aba, header=None, nrows=15)
                header_row_index = -1
                for idx, row in df_preview.iterrows():
                    row_str = row.astype(str).str.cat(sep=' ').upper()
                    if "INSTITUIÇÃO" in row_str and "NOME DO CURSO" in row_str and ("CICLO" in row_str or "MATRÍCULA" in row_str):
                        header_row_index = idx
                        break
                
                if header_row_index != -1:
                    df = pd.read_excel(xls, sheet_name=nome_aba, skiprows=header_row_index)
                    df.columns = [' '.join(str(c).split()) for c in df.columns]
                    df = limpar_padronizar_dataframe(df)
                    st.success(f"✅ Dados encontrados na aba: **{nome_aba}**")
                    return df
            except: continue
        st.error("❌ Estrutura não encontrada. Envie a planilha Fase 4 da Matriz de Distribuição Orçamentária disponibilizada no sistema.")
        return None
    except Exception as e:
        st.error(f"Erro ao abrir arquivo: {e}")
        return None

def interface_selecao_ciclo(df_curso):
    if df_curso.empty:
        st.warning("⚠️ Nenhum dado encontrado para este filtro.")
        return None

    df_temp = df_curso.copy()
    df_temp['DIC_dt'] = pd.to_datetime(df_temp['DIC'], dayfirst=False, errors='coerce')
    df_temp = df_temp.sort_values(by='DIC_dt', ascending=False)
    
    opcoes_map = {}
    for idx, row in df_temp.iterrows():
        dic_str = row['DIC']
        if pd.notnull(row['DIC_dt']):
            dic_str = row['DIC_dt'].strftime('%d/%m/%Y')
        
        oferta = str(row.get('Tipo de Oferta', 'N/A'))
        qtm = str(row.get('QTM1P', row.get('QTM', 0)))
        
        if qtm.strip().lower() == 'nan': continue
        
        label = f"Início: {dic_str} {'' if str(oferta).upper().strip() in ['NÃO SE APLICA', 'N/A', 'NAN'] else f'| Oferta: {oferta}'} | Matrículas: {qtm}"
        opcoes_map[idx] = label

    if not opcoes_map:
         st.warning("Nenhum ciclo com matrículas válidas encontrado.")
         return None


    with st.container():
        st.markdown("Ciclo")
        indice_selecionado = st.selectbox(
            "Ciclos encontrados:",
            options=list(opcoes_map.keys()),
            format_func=lambda x: opcoes_map[x],
            label_visibility="collapsed"
        )
    return df_temp.loc[indice_selecionado]


def exibir_calculadora_core(dados_linha=None, ano_default=2024):
    def_dic = get_val(dados_linha, 'DIC')
    def_dtc = get_val(dados_linha, 'DTC')
    val_dic = converter_para_data(def_dic) if def_dic else datetime.date.today()
    val_dtc = converter_para_data(def_dtc) if def_dtc else datetime.date.today()
    val_chc = int(get_val(dados_linha, 'CHC', 0))
    val_chmc = int(get_val(dados_linha, 'CHMC', 0))
    raw_pc = get_val(dados_linha, 'PC', 1.0)
    try: val_pc = float(str(raw_pc).replace(',', '.'))
    except: val_pc = 1.0
    raw_agro = get_val(dados_linha, ['Agropecuária','AGROPECUÁRIA', 'Curso de Agropecuária'], "Não")
    is_agro_sim = str(raw_agro).strip().upper() in ['SIM', 'S', 'TRUE', '1']
    val_finan = get_val(dados_linha, 'Situação de acordo com o tipo de financiamento', "PRESENCIAL")
    val_qtm = int(get_val(dados_linha, ['QTM1P', 'QTM'], 0))
    tipo_curso_val = get_val(dados_linha, 'Tipo de Curso', '')
    tipo_oferta_val = get_val(dados_linha, 'Tipo de Oferta', '')
    
    with st.container(border=True):
        st.markdown("#### Parâmetros do Cálculo")
        
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            DIC = st.date_input("Início do Ciclo (DIC)", val_dic, format="DD/MM/YYYY")
        with col1_2:
            DTC = st.date_input("Término do Ciclo (DTC)", val_dtc, format="DD/MM/YYYY")
        
        if DTC <= DIC: 
            st.error("⚠️ Data de término deve ser maior que início.")


        col2_1, col2_2, col2_3 = st.columns(3)
        with col2_1:
            pc = st.number_input("Peso do Curso (PC)", min_value=0.0, value=val_pc, step=0.1, format="%.2f")
        with col2_2:
            opt_fin = ["PRESENCIAL", "EAD FINANCIAMENTO EXTERNO", "EAD PRÓPRIO"]
            try: idx_fin = opt_fin.index(val_finan) 
            except: 
                if "EAD FP" in str(val_finan).upper(): idx_fin = 2
                elif "EAD" in str(val_finan).upper(): idx_fin = 1
                else: idx_fin = 0
            tipo_financiamento = st.selectbox("Financiamento", opt_fin, index=idx_fin)
        with col2_3:
            agro_idx = 0 if is_agro_sim else 1

            st.write("") 
            st.write("")
            agropecuaria = st.radio("Curso Agropecuária?", ["Sim", "Não"], index=agro_idx, horizontal=True)


        col3_1, col3_2, col3_3 = st.columns(3)
        with col3_1:
            chc = st.number_input("CH Ciclo (CHC)", min_value=0, value=val_chc, step=1)
        with col3_2:
            chmc = st.number_input("CH Catálogo (CHMC)", min_value=0, value=val_chmc, step=10)
        with col3_3:
            # Cálculo dinâmico para sugestão do CHM
            chm_calculado = calcular_chm(tipo_curso_val, tipo_oferta_val, chc, chmc)
            chm = st.number_input("CH Matriz (CHM)", min_value=0, value=int(chm_calculado))
            if dados_linha is not None: 
                st.caption(f"ℹ️ Selecionado: {chm_calculado}")

        col4_1, col4_2 = st.columns(2)
        with col4_1:
            qtm = st.number_input("Matrículas Atendidas (QTM)", min_value=0, value=val_qtm)
        with col4_2:

            lista_anos = list(range(2020, 2031))
            if ano_default in lista_anos:
                idx_ano = lista_anos.index(ano_default)
            else:
                idx_ano = 0
            
            ano_periodo = st.selectbox("Ano de Análise", lista_anos, index=idx_ano)
  
        btn_calcular = st.button("CALCULAR MATRÍCULA TOTAL", type="primary", use_container_width=True)

    if btn_calcular:
        DIP = datetime.date(ano_periodo, 1, 1)
        DFP = datetime.date(ano_periodo, 12, 31)
        
        QTDC = (DTC - DIC).days + 1
        CHMD = min(chm, chc) / QTDC if QTDC > 0 else 0
        CHA = CHMD * 365 if QTDC > 365 else chm
        FECH = CHA / 800 if QTDC > 365 else chc / 800

        # Dias ativos
        DACP1 = (DFP - DIP).days + 1 if (DIC < DIP and DTC > DFP) else 0
        DACP2 = (DFP - DIC).days + 1 if (DIC >= DIP and DTC > DFP and DIC < DFP) else 0
        DACP3 = (DTC - DIP).days + 1 if (DIC < DIP and DTC <= DFP and DTC >= DIP) else 0
        DACP4 = (DTC - DIC).days + 1 if (DIC >= DIP and DTC <= DFP) else 0
        DACP5 = ((DFP - DIP).days + 1) / 2 if (DIC < DIP and DTC < DIP) else 0

        denominador = (DFP - DIP).days + 1
        FEDA = (DACP1 + DACP2 + DACP3 + DACP4 + DACP5) / denominador if denominador > 0 else 0
        FECHDA = FECH * FEDA

        if DACP5 == 0: MECHDA = FECHDA * qtm
        elif (DIP - DTC).days > 1095: MECHDA = 0
        else: MECHDA = FECHDA * (qtm / 2)

        MP = MECHDA * pc
        BA = MP * 0.5 if agropecuaria == "Sim" else 0

        MT = 0
        CMTD80 = 0
        CMTD25 = 0
        
        if tipo_financiamento == "PRESENCIAL": MT = MP + BA
        elif tipo_financiamento == "EAD PRÓPRIO": 
            CMTD80 = MP * 0.80
            MT = CMTD80
        elif tipo_financiamento == "EAD FINANCIAMENTO EXTERNO": 
            CMTD25 = MP * 0.25
            MT = CMTD25
        
        # Verificação Apto/Jubilado
        raw_apto = get_val(dados_linha, 'Apto', "SIM")
        is_jubilado = str(raw_apto).strip().upper() == "NÃO"

        if is_jubilado:
            st.markdown(f"""
            <div style="border: 2px solid #d32f2f; border-radius: 12px; background-color: #fdecea; padding: 25px; text-align: center; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <span style="font-size: 3em; font-weight: 800; color: #d32f2f;">0,00</span>
                <br><strong style="color: #d32f2f; font-size: 1.2em;">CICLO JUBILADO</strong>
                <p style="color: #555; margin-top: 10px;">Mais de três anos após data prevista de término do ciclo</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="border: 2px solid #2E7D32; border-radius: 12px; background-color: #E8F5E9; padding: 25px; text-align: center; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <span style="font-size: 3.5em; font-weight: 800; color: #2E7D32;">{MT:.2f}</span>
                <br><strong style="color: #1B5E20; font-size: 1.2em; text-transform: uppercase;">Matrícula(s) Total(is)</strong>
            </div>
            """, unsafe_allow_html=True)
            
            if qtm > 0: 
                st.info(f"Cada matrícula neste ciclo gera **{MT / qtm:.2f}** matrícula(s) total(is) em {ano_periodo}.")

        with st.expander("Cálculo Detalhado"):
            t1, t2 = st.tabs(["Variáveis de Tempo", "Fatores e Ponderação"])
            
            with t1:
                st.write(f"**QTDC (Quantidade de Dias do Ciclo)**: {QTDC} dias")
                st.write(f"**CHM (Carga Horária para Matriz):** {chm}")
                st.write(f"**CHMD (Carga Horária Média Diária):** {CHMD:.2f}")
                st.write(f"**CHA (Carga Horária Anualizada):** {CHA:.2f}")
                st.write(f"**FECH (Fator de Equalização de Carga Horária):** {FECH:.4f}")
                st.markdown("---")
                st.write("**Dias Ativos por Período (DACP):**")
                st.write(f"1 - começa antes do início do período e termina depois do final do período): {DACP1}")
                st.write(f"2 - começa dentro do período e termina depois do final do período): {DACP2}")
                st.write(f"3 - começa antes do início do período e termina antes do final do período): {DACP3}")
                st.write(f"4 - começa depois do início do período e termina antes do final do período): {DACP4}")
                st.write(f"5 - começa antes do início do período e termina antes do início do período): {DACP5}")

            with t2:
                st.write(f"**FEDA (Fator de Equalização de Dias Ativos):** {FEDA:.4f}")
                st.write(f"**FECHDA (Fator de Equalização de Carga Horária e Dias Ativos):** {FECHDA:.4f}")
                st.write(f"**MECHDA (Matrículas Equalizadas por Carga Horária e Dias Ativos):** {MECHDA:.4f}")
                st.write(f"**Bônus Agro (BA):** {BA:.2f}")
                
                if tipo_financiamento == "EAD FINANCIAMENTO EXTERNO":
                    st.write("---")
                    st.write(f"**Curso EAD**")
                    st.write(f"CMTD25 (Fomento externo vale 25% da presencial): {CMTD25:.2f}")
                elif tipo_financiamento == "EAD PRÓPRIO":
                    st.write("---")
                    st.write(f"**Curso EAD**")
                    st.write(f"CMTD80 (Fomento próprio vale 80% da presencial): {CMTD80:.2f}")


st.write("Esta ferramenta foi desenvolvida baseada na Portaria MEC nº 646, de 25 de agosto de 2022, que estabelece a metodologia da Matriz de Distribuição Orçamentária dos Institutos Federais. Os dados são calculados a partir das fórmulas da planilha 'Fase 4 ', que é disponibilizada para os Institutos Federais. Assim, é possível verificar quanto cada matrícula contribui no cálculo de matrículas totais, bem como simular outros cenários.")
st.write("Selecione uma das opções para iniciar:")

col_nav1, col_nav2, col_nav3 = st.columns(3)

with col_nav1:
    tipo_btn = "primary" if st.session_state['modo'] == 'iffar' else "secondary"
    if st.button("🔍 Matrículas Totais do IFFar", type=tipo_btn, use_container_width=True):
        set_modo('iffar')

with col_nav2:
    tipo_btn = "primary" if st.session_state['modo'] == 'excel' else "secondary"
    if st.button("📂 Outros Institutos Federais", type=tipo_btn, use_container_width=True):
        set_modo('excel')

with col_nav3:
    tipo_btn = "primary" if st.session_state['modo'] == 'manual' else "secondary"
    if st.button("✏️ Simulador Manual", type=tipo_btn, use_container_width=True):
        set_modo('manual')

st.write("") # Espaçamento


if st.session_state['modo'] == 'iffar':
    st.markdown("## Matrículas do IFFarroupilha")
    st.markdown("##### Dados da PNP Ano Base 2024 que foram usados pela MDO 2026")
    st.info("Escolha um campus, tipo de curso, nome do curso e qual ciclo deseja conferir os dados.")
    st.write("")

    try:
        df = carregar_dados_gsheets()

        c1, c2 = st.columns(2)
        
        with c1:
            lista_campus = sorted(df['Unidade de Ensino'].unique().tolist())

            campus_sel = st.selectbox(
                "1. Campus", 
                options=[""] + lista_campus, 
                format_func=lambda x: "Selecione..." if x == "" else formatar_nome(x)
            )

        # Só prossegue se um campus foi selecionado
        if campus_sel:
            df_c = df[df['Unidade de Ensino'] == campus_sel]
            
            with c2:
                lista_tipos = sorted(df_c['Tipo de Curso'].unique().tolist())
                tipo_sel = st.selectbox(
                    "2. Tipo de Curso", 
                    options=[""] + lista_tipos,
                    format_func=lambda x: "Selecione..." if x == "" else formatar_nome(x)
                )
            
            # Só prossegue se um tipo de curso foi selecionado
            if tipo_sel:
                df_t = df_c[df_c['Tipo de Curso'] == tipo_sel]
                
                lista_cursos = sorted(df_t['Nome_Padronizado'].unique().tolist())
                curso_sel = st.selectbox(
                    "3. Curso", 
                    options=[""] + lista_cursos,
                    format_func=lambda x: "Selecione..." if x == "" else x
                )

                # Só exibe o cálculo se o curso final foi selecionado
                if curso_sel:
                    df_final = df_t[df_t['Nome_Padronizado'] == curso_sel]
                    
                    linha_selecionada = interface_selecao_ciclo(df_final)
                    
                    if linha_selecionada is not None:
                        exibir_calculadora_core(linha_selecionada)

    except Exception as e:
        st.error("Erro ao conectar com a base de dados (Google Sheets). Informe para dpdi@iffarroupilha.edu.br")
        st.exception(e)

elif st.session_state['modo'] == 'excel':
    st.markdown("### 📂 Análise de Arquivo (Outros IFs)")
    st.info("Faça upload da planilha **Fase 4 da Matriz de Distribuição Orçamentária** (.xlsx) para conferência.")
    
    arq = st.file_uploader("Selecione o arquivo", type=["xlsx"])
    
    if arq:
        try:
            df_up = carregar_dados_excel(arq)

            if df_up is not None:
                mapa_auxiliar = {
                        'Unidade de Ensino': 'Campus',
                        'Unidade': 'Campus',
                        'Tipo Curso': 'Tipo de Curso'
                    }
                df_up = df_up.rename(columns=mapa_auxiliar)

                cols_existentes = df_up.columns
                
                col_nome_real = None
                # Lista de tentativas comuns
                tentativas = [c for c in cols_existentes if 'NOME' in str(c).upper() and 'CURSO' in str(c).upper()]
                
                if tentativas:
                    col_nome_real = tentativas[0] # Pega a primeira correspondência (ex: "Nome do Curso", "Nome Curso")
                elif 'Curso' in cols_existentes:
                    col_nome_real = 'Curso'
                
                # Verifica as outras colunas de filtro
                tem_campus = 'Campus' in cols_existentes
                tem_tipo = 'Tipo de Curso' in cols_existentes

                if col_nome_real:
                    st.divider()
                    st.markdown("#### 🔍 Filtros de Seleção")
                    
                    col_f1, col_f2, col_f3 = st.columns(3)

                    campus_sel = None
                    with col_f1:
                        if tem_campus:
                            lista_campus = sorted(df_up['Campus'].astype(str).unique())
                            campus_sel = st.selectbox("Campus", [""] + lista_campus)
                        else:
                            st.warning("Coluna 'Campus'/Unidade não identificada.")

                    tipo_sel = None
                    with col_f2:
                        if tem_tipo:
                            # Filtra opções baseado no campus (se selecionado)
                            df_temp = df_up[df_up['Campus'] == campus_sel] if campus_sel else df_up
                            lista_tipos = sorted(df_temp['Tipo de Curso'].astype(str).unique())
                            tipo_sel = st.selectbox("Tipo de Curso", [""] + lista_tipos)
                        else:
                            st.warning("Coluna 'Tipo de Curso' não identificada.")

                    curso_sel = None
                    with col_f3:
                        # Aplica os filtros em cascata
                        df_filtrado = df_up.copy()
                        if campus_sel:
                            df_filtrado = df_filtrado[df_filtrado['Campus'] == campus_sel]
                        if tipo_sel:
                            df_filtrado = df_filtrado[df_filtrado['Tipo de Curso'] == tipo_sel]
                        
                        # Carrega a lista usando a coluna original encontrada
                        lista_cursos = sorted(df_filtrado[col_nome_real].astype(str).unique())
                        
                        # Exibe o selectbox com o label correto da coluna
                        label_filtro = f"Selecionar {col_nome_real}"
                        curso_sel = st.selectbox(label_filtro, [""] + lista_cursos)


                    if curso_sel:

                        df_final = df_up[df_up[col_nome_real] == curso_sel]
                        
                        # Reforça filtros de consistência
                        if campus_sel: df_final = df_final[df_final['Campus'] == campus_sel]
                        if tipo_sel: df_final = df_final[df_final['Tipo de Curso'] == tipo_sel]
                        
                        st.markdown("---")
                        # Passa para a tabela de seleção
                        linha_selecionada = interface_selecao_ciclo(df_final)
                        
                        if linha_selecionada is not None:
                            exibir_calculadora_core(linha_selecionada)
                else:
                    st.error("⚠️ Não foi encontrada uma coluna contendo 'Nome' e 'Curso'. Verifique o cabeçalho da planilha.")
                    st.write("Colunas identificadas:", list(cols_existentes))
        
        except Exception as e:
            st.error("Erro ao processar o arquivo.")
            st.error(e)
            

elif st.session_state['modo'] == 'manual':
    st.markdown("### ✏️ Simulação Manual")
    st.info("Utilize os filtros abaixo para carregar peso e carga horária de um curso existente ou deixe em branco para preencher tudo manualmente.")

    linha_simulacao = None
    
    # Container de Pré-preenchimento
    with st.expander("📂 Carregar base de dados de curso existente", expanded=True):
        try:
            # Carrega dados para popular os selects
            df = carregar_dados_gsheets()
            
            c_filtro1, c_filtro2, c_filtro3 = st.columns(3)
            
            with c_filtro1:
                # 1. Filtro Tipo de Curso
                lista_tipos = sorted(df['Tipo de Curso'].astype(str).unique())
                tipo_sel = st.selectbox("Tipo de Curso", [""] + lista_tipos)
            
            with c_filtro2:
                # 2. Filtro Tipo de Oferta (Aparece dinamicamente se for Técnico)
                oferta_sel = None
                if tipo_sel and "TECNICO" in tipo_sel.upper():
                    # Filtra o DF pelo tipo para ver as ofertas disponíveis
                    df_tipo = df[df['Tipo de Curso'] == tipo_sel]
                    lista_ofertas = sorted(df_tipo['Tipo de Oferta'].astype(str).unique())
                    oferta_sel = st.selectbox("Tipo de Oferta", [""] + lista_ofertas)
                else:
                    st.selectbox("Tipo de Oferta", ["N/A"], disabled=True)
            
            with c_filtro3:
                lista_cursos = []
                if tipo_sel:
                    # Começa filtrando pelo tipo
                    df_filtrado = df[df['Tipo de Curso'] == tipo_sel]
                    
                    # Se tiver oferta selecionada (caso dos técnicos), filtra também pela oferta
                    if oferta_sel:
                        df_filtrado = df_filtrado[df_filtrado['Tipo de Oferta'] == oferta_sel]
                    
                    lista_cursos = sorted(df_filtrado['Nome_Padronizado'].unique())
                    curso_base_sel = st.selectbox("Nome do Curso", [""] + lista_cursos)
                else:
                    curso_base_sel = st.selectbox("Nome do Curso", [], disabled=True, placeholder="Selecione o Tipo primeiro")

            if curso_base_sel:
                
                df_final_busca = df[df['Nome_Padronizado'] == curso_base_sel]
                if oferta_sel:
                    df_final_busca = df_final_busca[df_final_busca['Tipo de Oferta'] == oferta_sel]
                
                linha_base = df_final_busca.iloc[0].copy()
                
                linha_base['DIC'] = datetime.date(2026, 2, 19)
                linha_base['DTC'] = datetime.date(2026, 2, 19)
                linha_base['QTM'] = 30 
                linha_base['QTM1P'] = 30
                if 'CHMC' in linha_base:
                    linha_base['CHC'] = linha_base['CHMC']
                
                linha_base['Apto'] = 'SIM' 

                linha_simulacao = linha_base
                st.success(f"**{curso_base_sel}**{f', oferta do tipo {oferta_sel}' if tipo_sel and 'TECNICO' in tipo_sel.upper() else ''}, peso do curso **{linha_base.get('PC')}**, carga horária na matriz **{linha_base.get('CHM', 0)}h**")

        except Exception as e:
            st.error("Não foi possível carregar a base de dados. Simule os valores digitando manualmente.")
    exibir_calculadora_core(linha_simulacao, ano_default=2026)


st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8em;">
        © 2025 | Diretoria de Planejamento e Desenvolvimento Institucional do IFFarroupilha - dpdi@iffarroupilha.edu.br
    </div>
""", unsafe_allow_html=True)