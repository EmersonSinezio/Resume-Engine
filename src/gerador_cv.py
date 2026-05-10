import json
import os
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# === CONFIGURAÇÕES ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
ARQUIVO_JSON = "data/meus_dados.json"
VAGA_DESCRICAO = """
[COLE A DESCRIÇÃO DA VAGA AQUI - EXEMPLO:]
Procuramos um Engenheiro Backend Pleno com forte experiência em Node.js e AWS.
É diferencial ter trabalhado com migração de sistemas e bancos de dados PostgreSQL.
"""

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL if OPENAI_BASE_URL else None
)

def filtrar_dados_com_ia(dados_json, vaga):
    print("🤖 Analisando a vaga e filtrando suas experiências (Isso pode levar alguns segundos)...")
    
    prompt_sistema = """
    Você é um especialista em recrutamento técnico. Seu objetivo é analisar o JSON mestre do candidato e a descrição da vaga fornecida.
    
    REGRAS OBRIGATÓRIAS:
    1. Retorne APENAS um objeto JSON válido (sem markdown como ```json).
    2. NUNCA invente ou minta. Use apenas os dados fornecidos no JSON original.
    3. Crie um campo "resumo" de 3 linhas focando no alinhamento do candidato com a vaga.
    4. Selecione as 2 experiências e 1 projeto que mais possuem tecnologias em comum com a vaga.
    5. Reescreva os "bullets" (conquistas/tarefas) usando a fórmula: Verbo de Ação + Tarefa + Resultado. Destaque palavras-chave da vaga.
    6. Se a vaga pedir algo que o candidato não tem, não inclua. Foque no que ele tem de correlato.
    7. Filtre a lista de "habilidades" mantendo no máximo as 10 mais relevantes para a vaga.
    """

    resposta = client.chat.completions.create(
        model=OPENAI_MODEL, 
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"JSON DO CANDIDATO:\n{json.dumps(dados_json)}\n\nDESCRIÇÃO DA VAGA:\n{vaga}"}
        ]
    )
    
    # Retorna o JSON processado pela IA
    return json.loads(resposta.choices[0].message.content)

def gerar_pdf(dados_filtrados):
    print("📄 Injetando dados no HTML e gerando PDF...")
    
    # 1. Carregar Template HTML usando Jinja2
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('template.html')
    html_renderizado = template.render(dados_filtrados)
    
    # 2. Salvar temporariamente o HTML (Opcional, bom para debugar)
    with open("output/temp_cv.html", "w", encoding="utf-8") as f:
        f.write(html_renderizado)
        
    # 3. Converter HTML para PDF com WeasyPrint (Otimizado para ATS)
    arquivo_saida = "output/Curriculo_Otimizado.pdf"
    HTML(string=html_renderizado).write_pdf(arquivo_saida)
    
    print(f"✅ Sucesso! Seu currículo foi gerado: {arquivo_saida}")

def main():
    # 0. Verificar API Key
    if not OPENAI_API_KEY or "sua_chave" in OPENAI_API_KEY or "chave_aqui" in OPENAI_API_KEY:
        print("❌ Erro: API Key inválida ou não configurada no arquivo .env")
        print("Abra o arquivo .env e cole APENAS sua chave, sem os textos 'sua_chave_aqui'.")
        return

    # 1. Ler os dados mestre
    if not os.path.exists(ARQUIVO_JSON):
        print(f"❌ Erro: O arquivo {ARQUIVO_JSON} não foi encontrado.")
        return

    with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
        meus_dados = json.load(f)
    # 2. Filtrar dados via IA
    try:
        dados_otimizados = filtrar_dados_com_ia(meus_dados, VAGA_DESCRICAO)
    except Exception as e:
        print(f"❌ Erro ao processar com IA: {e}")
        return
    
    # Manter os dados pessoais originais intactos
    dados_otimizados["dados_pessoais"] = meus_dados["dados_pessoais"]
    
    # 3. Gerar Currículo PDF
    try:
        gerar_pdf(dados_otimizados)
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")

if __name__ == "__main__":
    main()
