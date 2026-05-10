# Resume Engine - Personalizador de Currículos Inteligente 🚀📄🤖

Aplicação Fullstack (Streamlit + Python) projetada para otimizar currículos para vagas específicas usando Inteligência Artificial (OpenAI/Gemini). Aumente suas chances de ser chamado para entrevistas com um currículo focado em ATS e relevância técnica.

> ✨ **Novidades na versão atual:**
>
> - 🎯 **Gerador Inteligente:** Reescreve seu currículo mestre focando nas palavras-chave da vaga.
> - 📊 **Simulador ATS:** Analisa seu match com a vaga e dá um score de compatibilidade.
> - 📈 **Tracker de Aplicações:** Registre suas candidaturas e mantenha um histórico organizado.
> - 📊 **Dashboard de Estatísticas:** Visualize tecnologias mais pedidas e seus gaps de aprendizado.
> - 🔍 **Análise Comparativa:** Compare qualquer PDF ou texto de currículo contra uma descrição de vaga.
> - ⚙️ **JSON Mestre:** Mantenha todos os seus dados em um único lugar e deixe a IA filtrar o que importa.
> - 🔧 **Configuração Flexível:** Suporte para múltiplos modelos (GPT-4, Gemini, etc) via OpenRouter ou OpenAI.

## 🛠 Tecnologias Utilizadas

### Core & Frontend

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32.0-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Jinja2](https://img.shields.io/badge/Jinja2-3.1.3-B41717?logo=jinja&logoColor=white)](https://palletsprojects.com/p/jinja/)
[![WeasyPrint](https://img.shields.io/badge/WeasyPrint-61.1-525252)](https://weasyprint.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.2.1-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)

### IA & Processamento

[![OpenAI](https://img.shields.io/badge/OpenAI_API-Compatible-412991?logo=openai&logoColor=white)](https://openai.com/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-Ready-8E75B2?logo=googlegemini&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![pdfplumber](https://img.shields.io/badge/pdfplumber-0.10.4-orange)](https://github.com/jsvine/pdfplumber)

## ✨ Funcionalidades Principais

### 🎯 Gerador de Currículo Otimizado
A IA analisa sua base de dados completa (`data/meus_dados.json`) e a descrição da vaga fornecida. Ela seleciona as experiências mais relevantes e reescreve suas conquistas usando a fórmula **Verbo de Ação + Tarefa + Resultado**.

### 📊 Simulador de ATS
Receba um feedback detalhado de como um software de recrutamento (ATS) veria seu perfil. Descubra palavras-chave faltantes e pontos fortes do seu currículo.

### 🔍 Análise de CV Externo
Fez um currículo no Word ou Canvas? Faça o upload do PDF e veja se ele realmente dá match com a vaga que você deseja.

## 🔧 Instalação e Execução

### Pré-requisitos
- Python 3.10+
- Chave de API da OpenAI ou Google Gemini (via OpenRouter/Vertex)

1. **Clone o repositório:**
```bash
git clone https://github.com/EmersonSinezio/Gerador-de-curriculos.git
cd Gerador-de-curriculos
```

2. **Configure o ambiente:**
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure as variáveis de ambiente:**
Crie um arquivo `.env` na raiz do projeto:
```env
OPENAI_API_KEY=sua_chave_aqui
OPENAI_MODEL=gemini-1.5-flash
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

4. **Inicie a aplicação:**
```bash
streamlit run app.py
```

## 📂 Estrutura do Projeto

```text
├── data/               # Banco de dados JSON com sua história profissional
├── src/                # Scripts de lógica e versão CLI
├── templates/          # Templates HTML para geração do PDF
├── output/             # Currículos gerados (PDF)
├── app.py              # Interface Streamlit principal
└── requirements.txt    # Dependências do projeto
```

## 📬 Contato

**Emerson Sinezio**
[![Email](https://img.shields.io/badge/-Gmail-%23333?style=for-the-badge&logo=gmail&logoColor=white)](mailto:emerson.sineziio@gmail.com)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-%230077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/emerson-sineziio)
[![GitHub](https://img.shields.io/badge/-GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/emerson-sineziio)

---
**Nota:** Este projeto utiliza WeasyPrint para geração de PDFs, o que garante currículos limpos e legíveis por sistemas de leitura automática (ATS).
