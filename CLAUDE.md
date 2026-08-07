# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-page Streamlit app ("Calculadora de Matrículas Totais") used by IFFarroupilha (a Brazilian federal educational institute) to simulate and audit the **Matrícula Total (MT)** metric defined by **Portaria MEC nº 646/2022**. Results are simulations for internal conferência/planning — they don't replace the official Plataforma Nilo Peçanha (PNP) numbers. Deployed at https://iffarcalcmatriculatotal.streamlit.app/.

## Commands

```bash
pip install -r requirements.txt   # streamlit, pandas, st-gsheets-connection, openpyxl
streamlit run app.py              # run the app locally (http://localhost:8501)
```

There is no test suite, linter, or build step in this repo.

Secrets (Google Sheets connection credentials) go in `.streamlit/secrets.toml`, which is gitignored. `.streamlit/config.toml` holds only theme colors and is committed.

## Architecture

Everything lives in `app.py` (~780 lines) as a linear Streamlit script — there's no package structure, no classes, and no separate modules besides `correcoes_nomes.py` (a flat dict for normalizing accented Portuguese course/campus names, imported defensively with a fallback to `{}`).

The app has three mutually-exclusive modes selected via `st.session_state['modo']` and three nav buttons at the bottom of the initial screen:

- **`iffar`** — pulls live data from a Google Sheet via `st-gsheets-connection` (`carregar_dados_gsheets`, cached 10 min with `@st.cache_data`). Cascading selectboxes: Campus → Tipo de Curso → Curso → Ciclo.
- **`excel`** — same flow but for uploaded `.xlsx` files from other Institutos Federais (`carregar_dados_excel`). It scans sheets/rows heuristically to find the header row (looking for "INSTITUIÇÃO" + "NOME DO CURSO" + "CICLO"/"MATRÍCULA"), then applies the same column-cleanup logic as the Sheets path.
- **`manual`** — lets a user pick an existing course to prefill weight/hours, then override everything by hand for what-if scenarios.

All three modes converge on two shared functions that do the real work:

- **`limpar_padronizar_dataframe`** — normalizes incoming column headers to a fixed set of acronyms (DIC, DTC, CHC, CHMC, CHM, PC, QTDC, CHMD, CHA, FECH, DIP, DFP, QTM1P, QTM, DACP, FEDA, FECHDA, MECHDA, MP, BA, MT, Apto) by matching the first whitespace-token of each header, and adds a `Nome_Padronizado` column via `formatar_nome`/`correcoes_nomes`.
- **`exibir_calculadora_core(dados_linha, ano_default)`** — renders the parameter form (prefilled from a data row if provided, else blank/manual) and, on submit, runs the full MT calculation and detailed breakdown. This is the one place to look when the calculation itself needs to change.

### The MT calculation pipeline (in `exibir_calculadora_core`)

Follows Portaria 646/2022 methodology, step by step (see README.md "Detalhamento do Cálculo" for the full formulas): QTDC (dias no ciclo) → CHMD/CHA (equalização de carga horária) → FECH → DACP1–5 (dias ativos por sobreposição do ciclo com o ano-base, 5 mutually exclusive interval cases) → FEDA → FECHDA → MECHDA → MP (aplica peso PC) → BA (bônus de 50% se Agropecuária) → MT (ajustado por modalidade: Presencial, EAD Próprio = 80%, EAD Financiamento Externo = 25%).

**Important deliberate divergence from the Portaria text**: when `QTDC <= 365`, FEDA's denominator is set to the cycle's own duration (`QTDC`) instead of the calendar year length, which forces FEDA to 1.0. This intentionally matches how the official "Fase 4" budget-distribution spreadsheet behaves in practice, even though it diverges from a literal reading of the Portaria — this is explained to the user via an `st.warning` in the UI and must not be "fixed" without understanding this tradeoff (see the `# === AJUSTE DE LÓGICA DO FEDA ===` block).

A course is "jubilado" (ineligible, MT forced to 0) if `Apto == "NÃO"`, which is meant to reflect being more than 3 years past the cycle's expected end date.

### Data normalization quirks

- `formatar_nome` uppercases and strips names, then looks them up in `correcoes_nomes.nomes_cursos_substituicoes` to fix missing Portuguese accents (source data apparently lacks diacritics).
- `get_val(row, keys, default)` reads a row trying multiple possible column-name aliases in order (e.g. `['QTM1P', 'QTM']`), since column names vary between the live Sheets data and uploaded spreadsheets from other institutes.
- `calcular_chm` derives the "CH Matriz" suggestion from course type/offering type (FIC/Doutorado use CHC directly; PROEJA is fixed at 2400; INTEGRADO maps 800/1000/1200 → 3000/3100/3200).

### Keep-alive workflow

`.github/workflows/keep_alive.yml` runs `keep_alive_script.py` via GitHub Actions every 6 hours, using Playwright to visit the deployed Streamlit URL and screenshot it, purely to prevent the free-tier Streamlit Cloud app from sleeping. Unrelated to the calculation logic.
