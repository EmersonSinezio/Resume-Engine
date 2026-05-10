import streamlit as st
import json
import os
import re
import pdfplumber
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from dotenv import load_dotenv
from datetime import datetime, timedelta
import uuid
from collections import Counter
import pandas as pd
import csv
from io import StringIO

# Carrega variáveis do arquivo .env
load_dotenv()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Resume Engine AI", page_icon="📄", layout="wide")

ARQUIVO_JSON = "data/meus_dados.json"
TEMPLATE_HTML = "template.html"
ARQUIVO_SAIDA = "output/Curriculo_Otimizado.pdf"
ARQUIVO_APLICACOES = "data/aplicacoes.json"

# Pegar configurações do .env como padrão
ENV_API_KEY = os.getenv("OPENAI_API_KEY", "")
ENV_MODEL = os.getenv("OPENAI_MODEL", "gemini-1.5-flash")
ENV_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

# --- FUNÇÕES UTILITÁRIAS ---
def carregar_dados():
    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
            return f.read()
    return "{}"

def salvar_dados(dados_str):
    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        f.write(dados_str)

def carregar_aplicacoes():
    """Carrega o histórico de aplicações do JSON."""
    if os.path.exists(ARQUIVO_APLICACOES):
        with open(ARQUIVO_APLICACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"aplicacoes": []}

def salvar_aplicacoes(dados):
    """Salva o histórico de aplicações no JSON."""
    with open(ARQUIVO_APLICACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def registrar_aplicacao(empresa, cargo, vaga_descricao, dados_cv_gerado, stacks_vaga, api_key, model, base_url, status="enviado"):
    """
    Registra ou atualiza uma aplicação com o status informado.
    Se já existir um rascunho para mesma empresa+cargo, atualiza-o.
    """
    aplicacoes = carregar_aplicacoes()
    
    # Tenta encontrar rascunho existente para mesma empresa+cargo
    app_existente = None
    for app in aplicacoes["aplicacoes"]:
        if (app.get("empresa", "").lower() == empresa.lower() and 
            app.get("cargo", "").lower() == cargo.lower() and
            app.get("status") == "rascunho"):
            app_existente = app
            break
    
    gaps = analisar_gaps_com_ia(api_key, model, base_url, dados_cv_gerado, vaga_descricao)
    
    dados_atualizados = {
        "vaga_descricao": vaga_descricao.strip(),
        "curriculo_gerado": {
            "resumo": dados_cv_gerado.get("resumo", ""),
            "tecnologias_destacadas": dados_cv_gerado.get("habilidades", []),
            "experiencias_selecionadas": [e["cargo"] for e in dados_cv_gerado.get("experiencias", [])],
            "projetos_selecionados": [p["nome"] for p in dados_cv_gerado.get("projetos", [])]
        },
        "stacks_requisitadas": stacks_vaga,
        "stacks_possuidas": list(set(dados_cv_gerado.get("habilidades", [])) & set(stacks_vaga)),
        "gaps_identificados": gaps,
        "status": status,
        "data_atualizacao": datetime.now().isoformat(),
        "proximos_passos": f"Estudar: {', '.join(gaps[:3])}" if gaps else "Manter preparação técnica"
    }
    
    if app_existente:
        # Atualiza rascunho existente
        app_existente.update(dados_atualizados)
    else:
        # Cria nova aplicação
        nova_aplicacao = {
            "id": str(uuid.uuid4()),
            "data_criacao": datetime.now().isoformat(),
            "empresa": empresa.strip(),
            "cargo": cargo.strip(),
            **dados_atualizados
        }
        aplicacoes["aplicacoes"].append(nova_aplicacao)
    
    salvar_aplicacoes(aplicacoes)
    return app_existente["id"] if app_existente else nova_aplicacao["id"]

def criar_rascunho_aplicacao(empresa, cargo, vaga_descricao, dados_cv_gerado, stacks_vaga, api_key, model, base_url):
    """
    Cria um rascunho automático de aplicação assim que o CV é gerado.
    Status inicial: "rascunho"
    """
    aplicacoes = carregar_aplicacoes()
    
    # Extrai gaps via IA
    gaps = analisar_gaps_com_ia(api_key, model, base_url, dados_cv_gerado, vaga_descricao)
    
    # Extrai empresa da descrição se não foi informada
    empresa_nome = empresa.strip() if empresa.strip() else extrair_empresa_da_vaga(vaga_descricao)
    
    rascunho = {
        "id": str(uuid.uuid4()),
        "data_criacao": datetime.now().isoformat(),
        "data_atualizacao": datetime.now().isoformat(),
        "empresa": empresa_nome,
        "cargo": cargo.strip() if cargo.strip() else "Não especificado",
        "vaga_descricao": vaga_descricao.strip(),
        "curriculo_gerado": {
            "resumo": dados_cv_gerado.get("resumo", ""),
            "tecnologias_destacadas": dados_cv_gerado.get("habilidades", []),
            "experiencias_selecionadas": [e["cargo"] for e in dados_cv_gerado.get("experiencias", [])],
            "projetos_selecionados": [p["nome"] for p in dados_cv_gerado.get("projetos", [])]
        },
        "stacks_requisitadas": stacks_vaga,
        "stacks_possuidas": list(set(dados_cv_gerado.get("habilidades", [])) & set(stacks_vaga)),
        "gaps_identificados": gaps,
        "status": "rascunho",
        "feedback": None,
        "proximos_passos": f"Estudar: {', '.join(gaps[:3])}" if gaps else "Manter preparação técnica"
    }
    
    aplicacoes["aplicacoes"].append(rascunho)
    salvar_aplicacoes(aplicacoes)
    return rascunho["id"]

def extrair_empresa_da_vaga(vaga_texto):
    """
    Tenta extrair o nome da empresa da descrição da vaga (heurística simples).
    """
    import re
    # Procura padrões como "Empresa X", "na Empresa Y", "Vaga para Empresa Z"
    padroes = [
        r'(?:na|da|da empresa|empresa)\s+([A-Z][A-Za-z\s\.&]+?)(?:\s*[-–|,]|$)',
        r'^([A-Z][A-Za-z\s\.&]+?)\s*(?:-|\|)',  # No início do texto
    ]
    for padrao in padroes:
        match = re.search(padrao, vaga_texto)
        if match:
            return match.group(1).strip()
    return "Empresa não identificada"

def confirmar_aplicacao(id_aplicacao):
    """
    Atualiza o status de "rascunho" para "enviado".
    """
    aplicacoes = carregar_aplicacoes()
    for app in aplicacoes["aplicacoes"]:
        if app["id"] == id_aplicacao:
            app["status"] = "enviado"
            app["data_atualizacao"] = datetime.now().isoformat()
            salvar_aplicacoes(aplicacoes)
            return True
    return False

def descartar_rascunho(id_aplicacao):
    """
    Marca o rascunho como "descartado".
    """
    aplicacoes = carregar_aplicacoes()
    for app in aplicacoes["aplicacoes"]:
        if app["id"] == id_aplicacao:
            app["status"] = "descartado"
            app["data_atualizacao"] = datetime.now().isoformat()
            salvar_aplicacoes(aplicacoes)
            return True
    return False

def limpar_rascunhos_antigos(dias=7):
    """
    Remove rascunhos com mais de X dias que não foram confirmados nem descartados.
    """
    aplicacoes = carregar_aplicacoes()
    limite = datetime.now() - timedelta(days=dias)
    
    antes = len(aplicacoes["aplicacoes"])
    aplicacoes["aplicacoes"] = [
        app for app in aplicacoes["aplicacoes"]
        if app.get("status") != "rascunho" or 
           datetime.fromisoformat(app.get("data_criacao", datetime.now().isoformat())) > limite
    ]
    depois = len(aplicacoes["aplicacoes"])
    
    if antes != depois:
        salvar_aplicacoes(aplicacoes)
        return antes - depois
    return 0

def analisar_gaps_com_ia(api_key, model, base_url, dados_cv, vaga):
    """
    Usa a IA para identificar gaps específicos entre CV e vaga.
    Retorna lista de tecnologias/conceitos a estudar.
    """
    client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)
    
    prompt = """
    Analise o currículo gerado vs a vaga e liste APENAS as tecnologias/conceitos 
    que o candidato NÃO menciona mas a vaga exige. Seja específico e prático.
    
    Retorne APENAS um array JSON de strings, exemplo: ["Next.js", "Docker", "Testes com Jest"]
    """
    
    try:
        resposta = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"CV GERADO:\n{json.dumps(dados_cv)}\n\nVAGA:\n{vaga}"}
            ],
            temperature=0.1
        )
        gaps_bruto = limpar_json_gemini(resposta.choices[0].message.content)
        return json.loads(gaps_bruto)
    except:
        return []

def gerar_estatisticas_aplicacoes():
    """
    Gera métricas e insights a partir do histórico de aplicações.
    """
    dados = carregar_aplicacoes()
    aplicacoes = dados.get("aplicacoes", [])
    
    if not aplicacoes:
        return {
            "total_aplicacoes": 0,
            "stacks_mais_requisitadas": [],
            "gaps_comuns": [],
            "empresas_por_status": {},
            "sugestoes_estudo": []
        }
    
    # Contagem total
    total = len(aplicacoes)
    
    # Stacks mais requisitadas (top 10)
    todas_stacks = []
    for app in aplicacoes:
        todas_stacks.extend(app.get("stacks_requisitadas", []))
    stacks_counter = Counter(todas_stacks)
    stacks_top = stacks_counter.most_common(10)
    
    # Gaps mais comuns (o que mais falta aprender)
    todos_gaps = []
    for app in aplicacoes:
        todos_gaps.extend(app.get("gaps_identificados", []))
    gaps_counter = Counter(todos_gaps)
    gaps_top = gaps_counter.most_common(10)
    
    # Status das aplicações
    status_counter = Counter(app.get("status", "desconhecido") for app in aplicacoes)
    
    # Sugestões de estudo baseadas em gaps frequentes + relevância
    sugestoes = [
        {"tecnologia": gap, "frequencia": freq, "prioridade": "alta" if freq >= total * 0.3 else "média"}
        for gap, freq in gaps_top[:5]
    ]
    
    return {
        "total_aplicacoes": total,
        "stacks_mais_requisitadas": stacks_top,
        "gaps_comuns": gaps_top,
        "empresas_por_status": dict(status_counter),
        "sugestoes_estudo": sugestoes,
        "data_ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

def exportar_aplicacoes(formato="json"):
    """
    Exporta o histórico de aplicações em JSON ou CSV.
    """
    dados = carregar_aplicacoes()
    
    if formato == "json":
        return json.dumps(dados, ensure_ascii=False, indent=2)
    
    elif formato == "csv":
        output = StringIO()
        aplicacoes = dados.get("aplicacoes", [])
        if not aplicacoes:
            return "Nenhuma aplicação registrada."
        
        # Cabeçalhos
        campos = ["data_aplicacao", "empresa", "cargo", "status", "stacks_requisitadas", "gaps_identificados"]
        writer = csv.DictWriter(output, fieldnames=campos, extrasaction='ignore')
        writer.writeheader()
        
        for app in aplicacoes:
            linha = {
                "data_aplicacao": app.get("data_aplicacao", ""),
                "empresa": app.get("empresa", ""),
                "cargo": app.get("cargo", ""),
                "status": app.get("status", ""),
                "stacks_requisitadas": "; ".join(app.get("stacks_requisitadas", [])),
                "gaps_identificados": "; ".join(app.get("gaps_identificados", []))
            }
            writer.writerow(linha)
        
        return output.getvalue()

def limpar_json_gemini(texto_bruto):
    """Ignora pensamentos <thought> e formatação markdown, pegando apenas o JSON puro."""
    texto = re.sub(r"<thought>.*?</thought>", "", texto_bruto, flags=re.DOTALL)
    inicio = texto.find('{')
    fim = texto.rfind('}')
    if inicio != -1 and fim != -1:
        return texto[inicio:fim+1]
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\n?", "", texto)
        texto = re.sub(r"\n?```$", "", texto)
    return texto.strip()

def limpar_citacoes(obj):
    """
    Remove marcadores [cite: ...] de todas as strings em um objeto JSON (dict/list/str).
    Executa limpeza recursiva para garantir que nenhum campo fique com citações.
    """
    if isinstance(obj, str):
        return re.sub(r'\s*\[cite:\s*[\d,\s]+\]', '', obj, flags=re.IGNORECASE).strip()
    elif isinstance(obj, dict):
        return {key: limpar_citacoes(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [limpar_citacoes(item) for item in obj]
    else:
        return obj

def extrair_texto_pdf(arquivo):
    """Extrai o texto de um arquivo PDF carregado pelo usuário usando pdfplumber."""
    texto = ""
    with pdfplumber.open(arquivo) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() or ""
    return texto

# --- FUNÇÕES DE IA ---
def filtrar_dados_com_ia(api_key, model, base_url, dados_json, vaga):
    client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)
    prompt_sistema = """
    Você é um especialista em recrutamento técnico. Analise o JSON do candidato e a vaga.
    
    OBRIGATÓRIO: Retorne EXATAMENTE um objeto JSON estruturado. NÃO USE markdown. Comece com { e termine com }.
    NÃO inclua marcadores de referência como [cite: X], [1], ou similares. Retorne texto limpo.
    
    Estrutura esperada:
    {
      "resumo": "Texto de 3 linhas focado na vaga. Use o 'resumo_base' original como forte inspiração.",
      "experiencias": [lista de objetos: empresa, cargo, periodo, conquistas (lista), tecnologias (lista)],
      "projetos": [lista de objetos: nome, link, bullets (lista), tecnologias (lista)],
      "educacao": [lista de objetos: instituicao, curso, periodo, destaque],
      "habilidades": ["Hab 1", "Hab 2"]
    }

    REGRAS:
    1. NUNCA invente ou minta. Use apenas os dados originais.
    2. Selecione as experiências e projetos mais aderentes à vaga.
    3. Reescreva as conquistas usando: Verbo de Ação + Tarefa + Resultado, destacando palavras-chave da vaga.
    4. Inclua as formações acadêmicas e os cursos. Priorize os mais relevantes para a vaga.
    5. Filtre a lista de "habilidades": extraia no máximo 10 itens das categorias mais relevantes para a vaga e retorne como array simples: ["React.js", "Node.js", ...]
    6. Escolha o melhor título da lista "titulos_alternativos" que faça sentido para a vaga, ou use o "titulo_base".
    """
    resposta = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"JSON DO CANDIDATO:\n{json.dumps(dados_json)}\n\nDESCRIÇÃO DA VAGA:\n{vaga}"}
        ],
        temperature=0.2
    )
    json_bruto = json.loads(limpar_json_gemini(resposta.choices[0].message.content))
    return limpar_citacoes(json_bruto)

def analisar_ats(api_key, model, base_url, dados_json, vaga):
    client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)
    prompt_sistema = """
    Você é um robô de ATS (Applicant Tracking System) rigoroso e um Tech Recruiter sênior.
    Sua missão é cruzar o perfil do candidato (JSON) com a vaga e gerar um relatório de compatibilidade.
    
    OBRIGATÓRIO: Retorne EXATAMENTE um objeto JSON estruturado. NÃO USE markdown. Comece com { e termine com }.
    NÃO inclua marcadores de referência como [cite: X], [1], ou similares. Retorne texto limpo.
    
    Estrutura esperada:
    {
      "score": 85,
      "veredicto": "Resumo de 2 linhas sobre o quão aderente o candidato é à vaga.",
      "palavras_chave_encontradas": ["React", "Node.js", "AWS"],
      "palavras_chave_faltantes": ["Docker", "Kubernetes"],
      "pontos_fortes": ["Requisito 1 que ele atende", "Requisito 2 que ele atende"],
      "pontos_faltantes": ["Requisito da vaga que ele NÃO tem", "Outro requisito que falta"],
      "dica_entrevista": "Uma dica prática do que ele deve focar caso seja chamado para a entrevista."
    }
    """
    resposta = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"PERFIL DO CANDIDATO:\n{json.dumps(dados_json)}\n\nDESCRIÇÃO DA VAGA:\n{vaga}"}
        ],
        temperature=0.2
    )
    json_bruto = json.loads(limpar_json_gemini(resposta.choices[0].message.content))
    return limpar_citacoes(json_bruto)

def analisar_cv_texto_vs_vaga(api_key, model, base_url, cv_texto, vaga):
    """
    Analisa um currículo em texto puro contra uma descrição de vaga.
    Retorna score em %, pontos fortes, gaps e dicas.
    """
    client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)
    
    prompt_sistema = """
    Você é um especialista em recrutamento técnico e ATS.
    Analise o currículo (texto) do candidato versus a descrição da vaga.
    
    OBRIGATÓRIO: Retorne APENAS um objeto JSON válido. Sem markdown. Comece com { e termine com }.
    NÃO inclua marcadores de referência como [cite: X].
    
    Estrutura esperada:
    {
      "score": 75,
      "veredicto": "Frase curta sobre o nível de aderência.",
      "palavras_chave_encontradas": ["React", "Node.js", "PostgreSQL"],
      "palavras_chave_faltantes": ["Docker", "AWS"],
      "pontos_fortes": ["Experiência com X", "Domínio de Y"],
      "pontos_faltantes": ["Falta experiência em Z", "Não mencionou W"],
      "dica_entrevista": "Sugestão prática para o candidato se destacar.",
      "sugestoes_de_melhoria": ["Adicione exemplo de X", "Destaque Y no resumo"]
    }
    
    REGRAS:
    - Score deve refletir aderência real, não inflacionar.
    - Palavras-chave devem vir da descrição da vaga.
    - Seja objetivo e técnico, sem jargões genéricos.
    """
    
    resposta = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"CURRÍCULO DO CANDIDATO:\n{cv_texto}\n\nDESCRIÇÃO DA VAGA:\n{vaga}"}
        ],
        temperature=0.2
    )
    
    json_bruto = json.loads(limpar_json_gemini(resposta.choices[0].message.content))
    return limpar_citacoes(json_bruto)

def gerar_pdf(dados_filtrados):
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template(TEMPLATE_HTML)
    html_renderizado = template.render(dados_filtrados)
    HTML(string=html_renderizado).write_pdf(ARQUIVO_SAIDA)

# --- INTERFACE DO USUÁRIO (UI) ---
st.title("🚀 Personal Resume Engine (IA)")
st.markdown("Automatize a criação de currículos e analise seu match com as vagas.")

# Abas da interface
tab_gerador, tab_ats, tab_analise_cv, tab_tracker, tab_dados, tab_config = st.tabs([
    "🎯 Gerar Currículo", 
    "📊 Simulador ATS", 
    "🔍 Analisar CV + Vaga",
    "📈 Estatísticas", 
    "⚙️ Editar Meus Dados (JSON)", 
    "🔧 Configurações"
])

# ABA 5: CONFIGURAÇÕES
with tab_config:
    st.subheader("Configurações da API")
    api_key = st.text_input("Chave da API", value=ENV_API_KEY, type="password")
    model_name = st.text_input("Modelo da IA", value=ENV_MODEL)
    base_url = st.text_input("Base URL", value=ENV_BASE_URL, help="Deixe vazio se usar OpenAI original.")
    if st.button("Salvar no .env"):
        with open(".env", "w") as f:
            f.write(f"OPENAI_API_KEY={api_key}\n")
            f.write(f"OPENAI_MODEL={model_name}\n")
            f.write(f"OPENAI_BASE_URL={base_url}\n")
        st.success("Configurações salvas no arquivo .env!")

# ABA 2: SIMULADOR ATS
with tab_ats:
    col_ats1, col_ats2 = st.columns([1, 1])

    with col_ats1:
        st.subheader("Analisar Vaga (baseado no JSON Mestre)")
        vaga_ats = st.text_area("Cole a descrição da vaga aqui para análise:", height=250, key="vaga_ats")

        if st.button("🔍 Calcular Match (ATS)", use_container_width=True):
            if not api_key:
                st.error("⚠️ Insira a chave da API na aba Configurações.")
            elif not vaga_ats:
                st.warning("⚠️ Cole a descrição da vaga antes de analisar.")
            else:
                try:
                    with st.spinner("🤖 O robô ATS está analisando seu perfil contra a vaga..."):
                        meus_dados = json.loads(carregar_dados())
                        resultado_ats = analisar_ats(api_key, model_name, base_url, meus_dados, vaga_ats)
                        st.session_state['resultado_ats'] = resultado_ats
                except Exception as e:
                    st.error(f"🚨 Ocorreu um erro: {e}")

    with col_ats2:
        st.subheader("Resultado da Análise")
        if 'resultado_ats' in st.session_state:
            res = st.session_state['resultado_ats']

            score = res.get('score', 0)
            if score >= 80:
                st.success(f"### Score de Match: {score}% 🏆")
            elif score >= 50:
                st.warning(f"### Score de Match: {score}% ⚠️")
            else:
                st.error(f"### Score de Match: {score}% 🛑")

            st.progress(score / 100)
            st.write(f"**Veredicto do Recrutador:** {res.get('veredicto', '')}")

            st.markdown("---")

            kw_encontradas = res.get('palavras_chave_encontradas', [])
            kw_faltantes = res.get('palavras_chave_faltantes', [])
            if kw_encontradas:
                st.markdown("🔑 **Palavras-chave detectadas no seu perfil:**")
                st.success(", ".join(kw_encontradas))
            if kw_faltantes:
                st.markdown("⚠️ **Palavras-chave que faltam no seu perfil:**")
                st.warning(", ".join(kw_faltantes))

            st.markdown("---")
            st.markdown("✅ **O que você tem (Pontos Fortes):**")
            for item in res.get('pontos_fortes', []):
                st.markdown(f"- {item}")

            st.markdown("❌ **O que a vaga pede e você não tem:**")
            if not res.get('pontos_faltantes'):
                st.markdown("- *Nenhum ponto crítico faltante!*")
            else:
                for item in res.get('pontos_faltantes', []):
                    st.markdown(f"- {item}")

            st.info(f"💡 **Dica de Ouro para a Entrevista:**\n{res.get('dica_entrevista', '')}")
        else:
            st.info("👈 Cole a vaga e clique em analisar para ver seu Score de aderência.")

# ABA 3: ANALISAR CV + VAGA
with tab_analise_cv:
    st.subheader("🔍 Analisar Currículo vs Vaga")
    st.markdown("Faça upload de um PDF, ou cole seu currículo em texto e a descrição da vaga para receber um score de compatibilidade.")
    
    col_cv1, col_cv2 = st.columns([1, 1])
    
    with col_cv1:
        arquivo_cv = st.file_uploader("📎 Faça upload do seu CV em PDF (Opcional)", type=["pdf"])
        
        # Quando o arquivo for enviado e for novo, extrai o texto e coloca no state do text_area
        if arquivo_cv is not None:
            if st.session_state.get("arquivo_atual") != arquivo_cv.name:
                texto_extraido = extrair_texto_pdf(arquivo_cv)
                st.session_state["cv_texto_input"] = texto_extraido
                st.session_state["arquivo_atual"] = arquivo_cv.name
                
        cv_texto = st.text_area(
            "📄 Ou cole seu currículo em texto (copie do Word):", 
            height=300, 
            key="cv_texto_input",
            placeholder="Ex: João Silva\nDesenvolvedor Full Stack\nExperiência com React, Node.js...\n..."
        )
    
    with col_cv2:
        vaga_analise = st.text_area(
            "🎯 Cole a descrição da vaga:", 
            height=300, 
            key="vaga_analise_input",
            placeholder="Ex: Procuramos Dev Full Stack com React, Node.js, PostgreSQL..."
        )
    
    if st.button("🚀 Analisar Compatibilidade", use_container_width=True, key="btn_analisar_cv"):
        if not api_key:
            st.error("⚠️ Insira a chave da API na aba Configurações.")
        elif not cv_texto.strip() or not vaga_analise.strip():
            st.warning("⚠️ Preencha ambos os campos: currículo e vaga.")
        elif len(cv_texto.strip()) < 100:
            st.warning("⚠️ Seu currículo parece muito curto. Cole o texto completo para uma análise precisa.")
        elif len(vaga_analise.strip()) < 50:
            st.warning("⚠️ A descrição da vaga parece incompleta. Cole o texto integral da vaga.")
        else:
            try:
                with st.spinner("🤖 IA analisando seu currículo contra a vaga..."):
                    resultado = analisar_cv_texto_vs_vaga(
                        api_key, model_name, base_url, cv_texto, vaga_analise
                    )
                    st.session_state['resultado_cv_vaga'] = resultado
                    
            except json.JSONDecodeError as e:
                st.error("🚨 A IA não retornou um JSON válido. Tente novamente.")
                with st.expander("Ver resposta bruta (debug)"):
                    st.code(str(e))
            except Exception as e:
                st.error(f"🚨 Erro: {e}")
    
    # Exibir resultados
    if 'resultado_cv_vaga' in st.session_state:
        res = st.session_state['resultado_cv_vaga']
        
        # Score com barra e cor dinâmica
        score = res.get('score', 0)
        if score >= 80:
            st.success(f"## 🏆 Score de Compatibilidade: {score}%")
        elif score >= 60:
            st.warning(f"## ⚠️ Score de Compatibilidade: {score}%")
        else:
            st.error(f"## 🛑 Score de Compatibilidade: {score}%")
        
        st.progress(score / 100)
        st.write(f"**Veredicto:** {res.get('veredicto', '')}")
        
        st.markdown("---")
        
        # Palavras-chave
        col_kw1, col_kw2 = st.columns(2)
        with col_kw1:
            kw_ok = res.get('palavras_chave_encontradas', [])
            if kw_ok:
                st.markdown("✅ **Palavras-chave detectadas:**")
                st.success(", ".join(kw_ok))
        with col_kw2:
            kw_falta = res.get('palavras_chave_faltantes', [])
            if kw_falta:
                st.markdown("❌ **Palavras-chave que faltam:**")
                st.warning(", ".join(kw_falta))
        
        st.markdown("---")
        
        # Pontos fortes e faltantes
        col_pf, col_pm = st.columns(2)
        with col_pf:
            st.markdown("💪 **Pontos Fortes:**")
            for item in res.get('pontos_fortes', []):
                st.markdown(f"- {item}")
        with col_pm:
            st.markdown("🎯 **O que a vaga pede e não está no CV:**")
            for item in res.get('pontos_faltantes', []):
                st.markdown(f"- {item}")
        
        st.markdown("---")
        
        # Dicas e melhorias
        st.info(f"💡 **Dica para a entrevista:**\n{res.get('dica_entrevista', '')}")
        
        sugestoes = res.get('sugestoes_de_melhoria', [])
        if sugestoes:
            st.markdown("🔧 **Sugestões para melhorar seu currículo:**")
            for sug in sugestoes:
                st.markdown(f"- {sug}")

# ABA 1: GERADOR
with tab_gerador:
    # Notificação de rascunhos antigos
    aplicacoes_info = carregar_aplicacoes()
    rascunhos_antigos = [
        app for app in aplicacoes_info.get("aplicacoes", [])
        if app.get("status") == "rascunho" and 
           datetime.fromisoformat(app.get("data_criacao", datetime.now().isoformat())) < datetime.now() - timedelta(days=3)
    ]
    if rascunhos_antigos:
        st.warning(f"⚠️ Você tem {len(rascunhos_antigos)} rascunho(s) com mais de 3 dias. Acesse '📈 Estatísticas' para revisar.")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Instruções")
        st.info("💡 Como usar:\n1. Cole a descrição da vaga ao lado.\n2. Clique em Gerar.\n3. Baixe o PDF.\n4. Se quiser, analise o currículo na aba 🔍 Analisar CV + Vaga.")
    with col2:
        st.subheader("Descrição da Vaga")
        vaga_descricao = st.text_area("Cole aqui todo o texto da vaga:", height=250, key="vaga_gerador")

        if st.button("✨ Gerar Currículo Otimizado", use_container_width=True):
            if not api_key:
                st.error("⚠️ Insira a chave da API na aba Configurações.")
            elif not vaga_descricao:
                st.warning("⚠️ Cole a descrição da vaga antes de gerar.")
            else:
                try:
                    with st.spinner("🤖 A IA está reescrevendo seu CV..."):
                        meus_dados = json.loads(carregar_dados())
                        dados_otimizados = filtrar_dados_com_ia(api_key, model_name, base_url, meus_dados, vaga_descricao)
                        dados_otimizados["dados_pessoais"] = meus_dados.get("dados_pessoais", {})
                        if "educacao" not in dados_otimizados:
                            dados_otimizados["educacao"] = meus_dados.get("educacao", [])
                        gerar_pdf(dados_otimizados)
                        st.session_state['ultimo_cv_gerado'] = dados_otimizados
                        st.session_state['ultima_vaga_descricao'] = vaga_descricao
                        
                        # --- CRIAÇÃO DE RASCUNHO AUTOMÁTICO ---
                        with st.spinner("💾 Salvando rascunho da aplicação..."):
                            empresa_extraida = extrair_empresa_da_vaga(vaga_descricao)
                            stacks_extraidas = list(set(
                                re.findall(r'\b(React|Node\.js|TypeScript|Python|Java|AWS|Docker|PostgreSQL|MongoDB|Git|HTML|CSS|JavaScript|Next\.js|Tailwind|Express|JWT|REST|GraphQL|Kubernetes|CI/CD)\b', 
                                          vaga_descricao, re.IGNORECASE)
                            ))
                            
                            id_rascunho = criar_rascunho_aplicacao(
                                empresa=empresa_extraida,
                                cargo="Não especificado",
                                vaga_descricao=vaga_descricao,
                                dados_cv_gerado=dados_otimizados,
                                stacks_vaga=stacks_extraidas,
                                api_key=api_key,
                                model=model_name,
                                base_url=base_url
                            )
                            st.session_state['id_rascunho_atual'] = id_rascunho

                    st.success("✅ Currículo gerado + rascunho salvo automaticamente!")

                    with open(ARQUIVO_SAIDA, "rb") as pdf_file:
                        st.download_button(
                            "⬇️ Baixar Currículo em PDF",
                            data=pdf_file,
                            file_name="Meu_Curriculo_Otimizado.pdf",
                            mime="application/pdf",
                            type="primary"
                        )

                except json.JSONDecodeError as e:
                    st.error("🚨 A IA não retornou um formato JSON válido. Tente gerar novamente.")
                    with st.expander("Ver resposta bruta da IA (Para debugar)"):
                        st.code(e.doc)
                except Exception as e:
                    st.error(f"🚨 Erro: {e}")

        # --- BOTÕES DE AÇÃO RÁPIDA ---
        if 'id_rascunho_atual' in st.session_state:
            st.markdown("---")
            st.subheader("📬 Você se candidatou a esta vaga?")
            
            col_confirm, col_descartar, col_editar = st.columns(3)
            
            with col_confirm:
                if st.button("✅ Sim, enviei!", use_container_width=True, key="btn_confirmar"):
                    confirmar_aplicacao(st.session_state['id_rascunho_atual'])
                    st.success("🎉 Aplicação confirmada! Status: Enviado.")
                    st.session_state.pop('id_rascunho_atual', None)
                    st.rerun()
            
            with col_descartar:
                if st.button("❌ Não, descartar", use_container_width=True, key="btn_descartar"):
                    descartar_rascunho(st.session_state['id_rascunho_atual'])
                    st.info("🗑️ Rascunho descartado. Você pode revisar depois na aba Estatísticas.")
                    st.session_state.pop('id_rascunho_atual', None)
                    st.rerun()
            
            with col_editar:
                if st.button("✏️ Editar depois", use_container_width=True, key="btn_editar"):
                    st.info("💾 Rascunho mantido. Acesse '📈 Estatísticas' para revisar depois.")
                    st.session_state.pop('id_rascunho_atual', None)
        else:
            st.info("💡 Dica: Após gerar um currículo, você pode confirmar ou descartar a aplicação aqui.")

# ABA: ESTATÍSTICAS
with tab_tracker:
    st.subheader("📊 Dashboard de Aplicações")
    
    # Botões de ação
    col_acoes, col_export = st.columns([3, 1])
    with col_acoes:
        if st.button("🔄 Atualizar Estatísticas", use_container_width=True):
            stats = gerar_estatisticas_aplicacoes()
            st.session_state['stats'] = stats
            st.rerun()
    
    with col_export:
        formato_export = st.selectbox("Exportar:", ["JSON", "CSV"], index=0)
        if st.button("📥 Exportar Dados", use_container_width=True):
            dados_export = exportar_aplicacoes(formato=formato_export.lower())
            st.download_button(
                label=f"⬇️ Baixar .{formato_export.lower()}",
                data=dados_export,
                file_name=f"aplicacoes_emerson.{formato_export.lower()}",
                mime="application/json" if formato_export == "JSON" else "text/csv"
            )
    
    st.markdown("---")
    
    # Carrega estatísticas
    if 'stats' not in st.session_state:
        stats = gerar_estatisticas_aplicacoes()
        st.session_state['stats'] = stats
    else:
        stats = st.session_state['stats']
    
    # Cards de métricas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Aplicações", stats['total_aplicacoes'])
    with col2:
        enviados = stats['empresas_por_status'].get('enviado', 0)
        st.metric("Currículos Enviados", enviados)
    with col3:
        gaps = len(stats['gaps_comuns'])
        st.metric("Gaps Identificados", f"{gaps} tecnologias")
    with col4:
        stacks = len(stats['stacks_mais_requisitadas'])
        st.metric("Stacks Únicas", stacks)
    
    st.markdown("---")
    
    # --- RASCUNHOS PENDENTES ---
    st.subheader("📝 Rascunhos Pendentes")

    aplicacoes_data = carregar_aplicacoes()
    rascunhos = [app for app in aplicacoes_data.get("aplicacoes", []) if app.get("status") == "rascunho"]

    if rascunhos:
        st.warning(f"Você tem **{len(rascunhos)} rascunho(s)** pendente(s). Confirme ou descarte para organizar seu histórico.")
        
        for rasc in rascunhos:
            with st.expander(f"🏢 {rasc['empresa']} — {rasc['cargo']}"):
                st.write(f"**Criado em:** {rasc.get('data_criacao', '')[:16].replace('T', ' ')}")
                st.write(f"**Stacks requisitadas:** {', '.join(rasc.get('stacks_requisitadas', [])[:5])}")
                if rasc.get('gaps_identificados'):
                    st.warning(f"**Gaps:** {', '.join(rasc['gaps_identificados'][:3])}")
                
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    if st.button("✅ Confirmar", key=f"conf_{rasc['id']}"):
                        confirmar_aplicacao(rasc['id'])
                        st.success("Confirmado!")
                        st.rerun()
                with col_a2:
                    if st.button("❌ Descartar", key=f"desc_{rasc['id']}"):
                        descartar_rascunho(rasc['id'])
                        st.info("Descartado.")
                        st.rerun()
    else:
        st.success("🎉 Nenhum rascunho pendente! Seu histórico está organizado.")

    # Botão de limpeza automática
    with st.expander("🧹 Limpeza Automática"):
        st.write("Remover rascunhos com mais de 7 dias não confirmados:")
        if st.button("Executar Limpeza"):
            removidos = limpar_rascunhos_antigos(dias=7)
            st.info(f"🗑️ {removidos} rascunho(s) antigo(s) removido(s).")
            st.rerun()

    st.markdown("---")
    
    # Gráfico: Stacks mais requisitadas
    st.subheader("🔥 Top 10 Tecnologias Mais Requisitadas")
    if stats['stacks_mais_requisitadas']:
        df_stacks = pd.DataFrame(stats['stacks_mais_requisitadas'], columns=["Tecnologia", "Ocorrências"])
        st.bar_chart(df_stacks.set_index("Tecnologia"), use_container_width=True)
    else:
        st.info("Nenhuma aplicação registrada ainda.")
    
    # Gráfico: Gaps de aprendizado
    st.subheader("🎯 O que estudar em seguida?")
    if stats['sugestoes_estudo']:
        for sug in stats['sugestoes_estudo']:
            emoji = "🔴" if sug['prioridade'] == 'alta' else "🟡"
            st.markdown(f"{emoji} **{sug['tecnologia']}** — Apareceu em {sug['frequencia']} vagas")
    else:
        st.success("🎉 Nenhum gap crítico identificado! Continue se preparando.")
    
    # Tabela: Histórico recente
    st.subheader("📋 Últimas Aplicações")
    apps = carregar_aplicacoes().get("aplicacoes", [])[-10:]  # Últimas 10
    if apps:
        for app in reversed(apps):
            with st.expander(f"{app['empresa']} — {app['cargo']} ({app['status']})"):
                st.write(f"**Data:** {app['data_aplicacao'][:10]}")
                st.write(f"**Stacks requisitadas:** {', '.join(app['stacks_requisitadas'][:5])}")
                if app['gaps_identificados']:
                    st.warning(f"**Gaps:** {', '.join(app['gaps_identificados'][:3])}")
                st.write(f"**Próximos passos:** {app['proximos_passos']}")
    else:
        st.info("Nenhuma aplicação registrada ainda.")

# ABA 4: EDITAR DADOS
with tab_dados:
    st.subheader("Base de Dados Mestra")
    st.markdown("Aqui você guarda **toda** a sua história profissional. A IA filtra com base na vaga.")
    dados_atuais = carregar_dados()
    dados_editados = st.text_area("Edite seu JSON:", value=dados_atuais, height=500)
    if st.button("💾 Salvar Dados"):
        try:
            json.loads(dados_editados)
            salvar_dados(dados_editados)
            st.success("✅ JSON salvo e validado!")
        except json.JSONDecodeError as e:
            st.error(f"❌ Erro de formatação no JSON. Detalhe: {e}")
