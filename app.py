import streamlit as st
import pandas as pd
import datetime
import unicodedata
import warnings
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO INICIAL E SILENCIAMENTO DE AVISOS ---
from streamlit import config as _config
_config.set_option("theme.base", "light")

# Silencia warnings de data do Pandas
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

# Tenta importar o dicionário de correções
try:
    from correcoes_nomes import nomes_cursos_substituicoes
except ImportError:
    nomes_cursos_substituicoes = {}

# =======================================================
# 1. FUNÇÕES AUXILIARES
# =======================================================

def formatar_nome(x):
    """Padroniza nomes removendo espaços extras e aplicando substituições conhecidas."""
    if pd.isnull(x): return ""
    x = str(x).strip().upper()
    return nomes_cursos_substituicoes.get(x, x).upper()

def calcular_chm(tipo_curso, tipo_oferta, chc, chmc):
    tipo_curso_upper = str(tipo_curso).upper() if pd.notnull(tipo_curso) else ""
    tipo_oferta_upper = str(tipo_oferta).strip().upper() if pd.notnull(tipo_oferta) else ""

    #valores adotados pela metodologia da Matriz
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
    """Converte valor para date de forma segura."""
    if pd.isnull(valor) or valor == "": return None
    if isinstance(valor, (pd.Timestamp, datetime.datetime)): return valor.date()
    if isinstance(valor, datetime.date): return valor
    try:
        dt = pd.to_datetime(valor, dayfirst=True, errors='coerce')
        return dt.date() if pd.notnull(dt) else None
    except:
        return None

# =======================================================
# 2. CARREGAMENTO E LIMPEZA
# =======================================================

def limpar_padronizar_dataframe(df):
    """Renomeia colunas e cria Nome_Padronizado."""
    
    # 1. Renomeação
    siglas_alvo = [
        "DIC", "DTC", "CHC", "CHMC", "CHM", "PC", 
        "QTDC", "CHMD", "CHA", "FECH", 
        "DIP", "DFP", "QTM1P", "QTM", "DACP", 
        "FEDA", "FECHDA", "MECHDA", "MP", "BA", "MT",
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

    # 2. Criação da Coluna Padronizada
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
                # Busca cabeçalho inteligente
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
        st.error("❌ Estrutura de colunas não encontrada. Envie a planilha denominada 4º Fase - Conferência matrículas recebida pela Matriz de Distribuição Orçamentária")
        return None
    except Exception as e:
        st.error(f"Erro ao abrir arquivo: {e}")
        return None

# =======================================================
# 3. NÚCLEO DA CALCULADORA
# =======================================================

def exibir_calculadora_core(dados_linha=None):
    # --- PREPARAÇÃO ---
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
    nome_curso_val = get_val(dados_linha, 'Nome do curso', '')

    # --- INPUTS ---
    st.markdown("---")
    st.header("📝 Parâmetros do Cálculo")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Ciclo e Carga Horária")
        
        # Inputs de Data
        DIC = st.date_input("Data de Início do Ciclo (DIC):", val_dic, format="DD/MM/YYYY")
        DTC = st.date_input("Data de Término do Ciclo (DTC):", val_dtc, format="DD/MM/YYYY")
        if DTC <= DIC: st.error("⚠️ Data de Término deve ser maior que Início.")
        
        chc = st.number_input("Carga Horária do Ciclo (CHC):", min_value=0, value=val_chc, step=1)
        chmc = st.number_input("Carga Horária Catálogo/MEC (CHMC):", min_value=0, value=val_chmc, step=10)
        
        chm_calculado = calcular_chm(tipo_curso_val, tipo_oferta_val, chc, chmc)
        chm = st.number_input("Carga Horária Matriz (CHM):", min_value=0, value=int(chm_calculado))
        if dados_linha is not None: st.caption(f"ℹ️ CHM adotada: {chm_calculado}")

    with c2:
        st.subheader("Pesos e Matrículas")
        pc = st.number_input("Peso do Curso (PC):", min_value=0.0, value=val_pc, step=0.1, format="%.2f")
        
        opt_agro = ["Sim", "Não"]
        idx_agro = 0 if is_agro_sim else 1
        agropecuaria = st.radio("Curso de Agropecuária?", opt_agro, index=idx_agro, horizontal=True)
        
        opt_fin = ["PRESENCIAL", "EAD FINANCIAMENTO EXTERNO", "EAD FINANCIAMENTO PRÓPRIO"]
        try: idx_fin = opt_fin.index(val_finan) 
        except: 
            if "PRÓPRIO" in str(val_finan).upper(): idx_fin = 2
            elif "EXTERNO" in str(val_finan).upper(): idx_fin = 1
            else: idx_fin = 0
            
        tipo_financiamento = st.selectbox("Tipo de Financiamento:", opt_fin, index=idx_fin)
        qtm = st.number_input("Matrículas Ativas no Ano Base (QTM):", min_value=0, value=val_qtm)

    st.subheader("🗓️ Período de Análise")
    ano_sugerido = 2024
    ano_periodo = st.selectbox("Ano do Período:", list(range(2020, 2031)), index=list(range(2020, 2031)).index(ano_sugerido))
    DIP = datetime.date(ano_periodo, 1, 1)
    DFP = datetime.date(ano_periodo, 12, 31)

    # --- CÁLCULO ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("CALCULAR MATRÍCULA TOTAL", type="primary", use_container_width=True):
        QTDC = (DTC - DIC).days + 1
        CHMD = min(chm, chc) / QTDC if QTDC > 0 else 0
        CHA = CHMD * 365 if QTDC > 365 else chm
        FECH = CHA / 800 if QTDC > 365 else chc / 800

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
        if tipo_financiamento == "PRESENCIAL": MT = MP + BA
        elif tipo_financiamento == "EAD FINANCIAMENTO PRÓPRIO": 
            CMTD80 = MP * 0.80
            MT = CMTD80
        elif tipo_financiamento == "EAD FINANCIAMENTO EXTERNO": 
            CMTD25 = MP * 0.25
            MT = CMTD25
            

        st.markdown(f"""
        <div style="border: 2px solid #17882c; border-radius: 10px; background-color: #e9f7ec; padding: 20px; text-align: center; margin: 20px 0;">
            <span style="font-size: 2.5em; font-weight: 800; color: #17882c;">MT: {MT:.2f}</span>
            <br><span style="color: #17882c; font-weight: 600;">Matrículas Totais</span>
        </div>
        """, unsafe_allow_html=True)
        
        if qtm > 0: st.info(f"📌 Cada matrícula corresponde a **{MT / qtm:.2f}** matrícula(s) total(is).")

        with st.expander("Ver Detalhes do Cálculo"):
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

            #c1, c2 = st.columns(2)
            #with c1:
            #    st.write(f"**QTDC:** {QTDC} | **CHMD:** {CHMD:.3f} | **CHA:** {CHA:.2f} | **FECH:** {FECH:.4f}")
            #with c2:
            #    st.write(f"**FEDA:** {FEDA:.4f} | **FECHDA:** {FECHDA:.4f} | **MP:** {MP:.2f} | **BA:** {BA:.2f}")

# =======================================================
# 4. LÓGICA DE SELEÇÃO DE CICLO (CORRIGIDA)
# =======================================================

def interface_selecao_ciclo(df_curso):
    """
    Mostra um selectbox com TODOS os ciclos ordenados e permite o usuário escolher.
    Usa ÍNDICES para evitar erro de comparação de Series do Pandas.
    """
    if df_curso.empty:
        st.error("Nenhum dado encontrado para este curso.")
        return None

    # 1. Preparar dados para ordenação (trabalhando na cópia)
    df_temp = df_curso.copy()


    df_temp['DIC_dt'] = pd.to_datetime(df_temp['DIC'], dayfirst=False, errors='coerce')
    
    # Ordena do mais recente para o mais antigo
    df_temp = df_temp.sort_values(by='DIC_dt', ascending=False)
    
    # 2. Criar um DICIONÁRIO {indice_dataframe: texto_bonito}
    # Isso evita guardar a Linha (Series) dentro do selectbox
    opcoes_map = {}
    
    for idx, row in df_temp.iterrows():
        dic_str = row['DIC']
        if pd.notnull(row['DIC_dt']):
            dic_str = row['DIC_dt'].strftime('%d/%m/%Y')
        
        oferta = str(row.get('Tipo de Oferta', 'N/A'))
        qtm = str(row.get('QTM1P', row.get('QTM', 0)))

        # --- FILTRO DE EXCLUSÃO ---
        # Se o QTM for 'nan', PULA esta linha (não adiciona ao mapa)
        if qtm.strip().lower() == 'nan':
            continue
        
        label = f"Início: {dic_str} {'' if str(oferta).upper().strip() in ['NÃO SE APLICA', 'N/A', 'NAN'] else f'| Tipo de Oferta: {oferta}'} | Matrículas no ano base: {qtm}"
        opcoes_map[idx] = label

    # 3. Exibir Selectbox usando apenas os índices como chaves
    st.info("💡 Múltiplos ciclos com matrículas atendidas no ano base. Selecione abaixo:")
    
    indice_selecionado = st.selectbox(
        "Selecione o ciclo específico:",
        options=list(opcoes_map.keys()), # Passa apenas a lista de índices (números)
        format_func=lambda x: opcoes_map[x] # Usa o índice para buscar o texto
    )
    
    # 4. Retorna a linha original correspondente ao índice escolhido
    return df_temp.loc[indice_selecionado]

# =======================================================
# 5. LAYOUT E NAVEGAÇÃO
# =======================================================

st.markdown("""
    <style> 
    .custom-header h1 { font-family: "Open Sans", sans-serif; font-size: 2.2em; color: #195128; margin-bottom: 0; }
    .custom-header h4 { font-family: "Open Sans", sans-serif; font-size: 1.1em; color: #195128; font-weight: 300; margin-top: 0; }
    .custom-bar { background-color: #004d0d; height: 4px; width: 100%; margin-bottom: 25px; }            
    </style>
    <div class="custom-header">
        <h1>Instituto Federal Farroupilha</h1>
        <h4>Calculadora de Matrículas Totais</h4>
    </div>
    <div class="custom-bar"></div>
""", unsafe_allow_html=True)

st.sidebar.title("Navegação")
modo = st.sidebar.radio("Escolha o Modo:", ("1. Matrículas IFFar", "2. Outros IFs (upload de planilha da fase 4", "3. Simulador Manual"))
st.title(f"Modo: {modo}")

# --- MODO 1: IFFAR ---
if modo.startswith("1"):
    try:
        df = carregar_dados_gsheets()
        
        campus = st.selectbox("Campus:", df['Unidade de Ensino'].unique(), format_func=formatar_nome)
        df_c = df[df['Unidade de Ensino'] == campus]
        
        tipo = st.selectbox("Tipo de Curso:", df_c['Tipo de Curso'].unique(), format_func=formatar_nome)
        df_t = df_c[df_c['Tipo de Curso'] == tipo]
        
        if str(tipo).upper() == "TECNICO":
            lst_cursos = df_t['Nome_Padronizado'].unique()
            curso_sel = st.selectbox("Curso (Todos os Técnicos):", lst_cursos)
            df_final = df_t[df_t['Nome_Padronizado'] == curso_sel]
        else:
            lst_cursos = df_t['Nome_Padronizado'].unique()
            curso_sel = st.selectbox("Curso:", lst_cursos)
            df_final = df_t[df_t['Nome_Padronizado'] == curso_sel]

        linha_selecionada = interface_selecao_ciclo(df_final)
        
        if linha_selecionada is not None:
            exibir_calculadora_core(linha_selecionada)

    except Exception as e:
        st.error("Erro de conexão com Google Sheets.")
        st.exception(e)

# --- MODO 2: UPLOAD EXCEL ---
elif modo.startswith("2"):
    st.info("Faça upload da planilha da Fase 4 da MDO (.xlsx).")
    arq = st.file_uploader("Carregar Planilha Fase 4", type=["xlsx"])
    
    if arq:
        df_up = carregar_dados_excel(arq)
        if df_up is not None:
            col_nome = 'Nome_Padronizado' if 'Nome_Padronizado' in df_up.columns else 'Nome do curso'
            if col_nome in df_up.columns:
                lista = df_up[col_nome].unique()
                curso_sel = st.selectbox("Selecione o Curso:", lista)
                df_final = df_up[df_up[col_nome] == curso_sel]
                
                linha_selecionada = interface_selecao_ciclo(df_final)
                if linha_selecionada is not None:
                    exibir_calculadora_core(linha_selecionada)
            else:
                st.warning("Coluna de nomes não identificada.")
                idx = st.number_input("Linha:", 0, len(df_up)-1)
                exibir_calculadora_core(df_up.iloc[idx])

# --- MODO 3: SIMULADOR ---
elif modo.startswith("3"):
    st.info("Preencha manualmente.")
    exibir_calculadora_core(None)