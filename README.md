# Calculadora de Matrícula Total - IFFar

Esta ferramenta é um software institucional desenvolvido para apoiar o cálculo e a conferência da **Matrícula Total** dos cursos ofertados no Instituto Federal Farroupilha, seguindo rigorosamente a metodologia estabelecida na **Portaria MEC nº 646/2022**.

O projeto foi construído em Python utilizando a biblioteca Streamlit, garantindo agilidade na simulação de cenários e transparência nas fórmulas aplicadas.



## 🔗 Acesso à Ferramenta

A calculadora está disponível online e pode ser acessada através do link abaixo:

👉 **[ACESSE A CALCULADORA AQUI](https://iffarcalcmatriculatotal.streamlit.app/)**



## 🎯 Objetivo

O projeto visa:
- **Facilitar o entendimento** do cálculo da Matrícula Total pelos gestores e servidores do IFFarroupilha;
- **Simular cenários** com diferentes parâmetros (carga horária, datas de ciclo, tipo de financiamento, evasão, etc.);
- **Apoiar a análise orçamentária**, permitindo antever inconsistências nos dados cadastrados no Sistec antes do fechamento da Plataforma Nilo Peçanha (PNP).



## ⚠️ Importante

> **Natureza da Ferramenta:** > Os cálculos realizados por esta aplicação seguem as fórmulas da Portaria MEC nº 646/2022 e utilizam a lógica das planilhas da Fase 4 da Distribuição Orçamentária. No entanto, os resultados são **simulações**.  
> Eles servem para conferência e planejamento, mas **não substituem os resultados oficiais** publicados pelo MEC ou pela Plataforma Nilo Peçanha, visto que as bases de dados oficiais podem sofrer alterações.



## 🔍 Como funciona a Metodologia

A calculadora processa os dados seguindo quatro etapas lógicas principais:

1.  **Equalização**
    Ajusta o impacto dos cursos considerando a duração do ciclo (dias), a carga horária e os dias ativos no ano base analisado.

2.  **Ponderação**
    Aplica o peso do curso conforme a tabela de eixos tecnológicos definida na Portaria.

3.  **Bonificação (Agropecuária)**
    Adiciona 50% ao valor final da matrícula ponderada se o curso pertencer à área de Agropecuária.

4.  **Finalização da Matrícula Total (MT)**
    Ajusta o valor final conforme a modalidade (Presencial ou EaD) e a fonte de financiamento (Próprio ou Externo).



## 🛠️ Estrutura e Tecnologias

O projeto utiliza boas práticas de desenvolvimento de dados com a seguinte estrutura:

-   **Linguagem:** [Python 3.10+](https://www.python.org/)
-   **Interface:** [Streamlit](https://streamlit.io/)
-   **Manipulação de Dados:** [Pandas](https://pandas.pydata.org/)
-   **Arquivos do Repositório:**
    -   `app.py`: Código fonte da aplicação web.
    -   `correcoes_nomes.py`: Dicionário para padronização de nomenclaturas (Campi e Cursos).
    -   `dados/`: Planilhas base para carga de dados (ex: Fase 4).



## ⚖️ Referência Legal

* **Portaria MEC nº 646, de 25 de agosto de 2022:** Institui a metodologia para o cálculo dos indicadores de gestão das Instituições da Rede Federal de EPCT.



## 🧮 Detalhamento do Cálculo (Passo a Passo)

Para fins de transparência, o algoritmo segue este fluxo:

1.  **QTDC (Dias no Ciclo):** `(Data Término - Data Início) + 1`
2.  **CHMD (Média Diária):** `Carga Horária Matriz / QTDC`
3.  **CHA (Anualização):** Se `QTDC > 365`, então `CHMD * 365`; senão `Carga Horária Total`.
4.  **FECH (Fator Carga Horária):** `CHA / 800`.
5.  **DACP (Dias Ativos):** Cálculo dos dias em que o curso esteve ativo dentro do ano letivo analisado.
6.  **FEDA (Fator Dias Ativos):** `Dias Ativos / 365`.
7.  **FECHDA (Fator Combinado):** `FECH * FEDA`.
8.  **MECHDA (Matrículas Equalizadas):** `FECHDA * Quantidade de Matrículas (QTM)`.
9.  **MP (Matrícula Ponderada):** `MECHDA * Peso do Curso`.
10. **BA (Bônus Agro):** Se Agropecuária, `MP * 0,5`.
11. **MT (Matrícula Total):** `MP + BA` (com redutores aplicados para EaD se necessário).



## Licença

Este projeto é um software proprietário de **uso não comercial**, desenvolvido no âmbito do Instituto Federal Farroupilha.

✔ Uso institucional, acadêmico e educacional permitido.  
❌ Uso comercial, venda ou sublicenciamento **não permitido**.


<div align="center">
    <b>Diretoria de Planejamento e Desenvolvimento Institucional - IFFarroupilha</b>
</div>