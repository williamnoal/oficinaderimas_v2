import os
import re
import json
import google.generativeai as genai
from flask import Flask, jsonify, request, Response, render_template_string
from datetime import datetime
from collections import defaultdict
# NOVAS IMPORTAÇÕES PARA O MOTOR DE PDF
from weasyprint import HTML, CSS

# --- 1. CONFIGURAÇÃO DA APLICAÇÃO FLASK E API GEMINI ---
# (Toda a lógica do backend Python permanece inalterada)

app = Flask(__name__)

# Configuração da API Key
API_KEY = os.environ.get('GOOGLE_API_KEY')
model = None

def get_model():
    """Configura e retorna o modelo de IA. Lida com erros de chave."""
    global model
    if model:
        return model
    
    if not API_KEY:
        print("!! ERRO FATAL: GOOGLE_API_KEY não encontrada no ambiente. !!")
        return None
    
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-flash-latest')
        print("Modelo 'gemini-flash-latest' configurado com sucesso.")
        return model
    except Exception as e:
        print(f"Erro ao configurar o 'gemini-flash-latest': {e}")
        try:
            print("Tentando fallback para 'gemini-flash-latest'...")
            model = genai.GenerativeModel('gemini-flash-latest')
            print("Modelo 'gemini-flash-latest' configurado com sucesso.")
            return model
        except Exception as e2:
            print(f"Erro ao configurar 'gemini-flash-latest' também: {e2}")
            return None

def generate_ai_content(prompt_text, force_json=False):
    """Função central para chamadas de IA, com retry e parsing de JSON."""
    model = get_model()
    if model is None:
        raise Exception("Modelo de IA não inicializado. Verifique a API Key e as permissões no Google Cloud.")

    try:
        generation_config = {}
        if force_json:
            generation_config["response_mime_type"] = "application/json"

        response = model.generate_content(prompt_text, generation_config=generation_config)
        
        text = response.text
        
        if force_json or '[' in text or '{' in text:
            match = re.search(r'```(json)?(.*)```', text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(2).strip()
            
            return json.loads(text)
        
        return text

    except Exception as e:
        print(f"Erro na geração de conteúdo da IA: {e}")
        error_message = str(e)
        if "is not found" in error_message:
             print("!! ERRO 404 DETECTADO: Verifique o nome do modelo e as permissões da API Key !!")
             raise Exception(f"Erro 404 da API Gemini: {error_message}")
        
        raise Exception(f"Falha ao gerar ou processar resposta da IA: {error_message}")


# --- 2. LÓGICA DE IA PEDAGÓGICA (PROMPTS OTIMIZADOS - V3) ---
# (Toda a lógica do backend Python permanece inalterada)

@app.route('/api/generate-themes', methods=['POST'])
def api_generate_themes():
    data = request.json
    interest = data.get('interest', 'amigos e escola')
    prompt = f"""
    Aja como um pedagogo e poeta, especialista em alunos do 6º ano (11-13 anos).
    O aluno escreveu sobre seus interesses: "{interest}"
    Sua tarefa é gerar 9 temas de poemas.
    REGRAS:
    1.  Os temas devem ser CONCRETOS e VISUAIS (ex: "O barulho do sinal do recreio", "Meu tênis de futsal gasto").
    2.  Evite temas abstratos (ex: "A beleza da amizade").
    3.  Os temas devem ser curtos (3-5 palavras).
    4.  A linguagem deve ser lúdica e moderna.
    5.  Retorne uma lista de strings.
    Exemplo de Resposta:
    ["O cheiro da chuva no asfalto", "A cor do meu jogo favorito", "O silêncio do meu quarto à noite"]
    """
    try:
        themes = generate_ai_content(prompt, force_json=True)
        if not isinstance(themes, list) or len(themes) == 0:
            raise Exception("A IA não retornou uma lista de temas.")
        return jsonify({"themes": themes})
    except Exception as e:
        print(f"[API /api/generate-themes] Erro: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-ideas', methods=['POST'])
def api_get_ideas():
    data = request.json
    theme = data.get('theme')
    prompt = f"""
    Aja como um professor de escrita criativa experiente, guiando um aluno de 11 a 13 anos.
    O tema do poema é '{theme}'.
    Sua tarefa é criar uma lista de 5 ideias de como progredir na escrita, focando nos sentidos.
    REGRAS:
    1.  **Foco nos Sentidos:** Incentive o aluno a pensar em cheiros, sons, cores e sensações.
    2.  **Simplicidade:** Use um vocabulário direto e acessível.
    3.  **Formato:** As ideias devem ser perguntas curtas ou comandos criativos.
    4.  **NÃO ESCREVA VERSOS:** Apenas as 5 ideias.
    
    Formato da Resposta OBRIGATÓRIO (JSON):
    [
        "Ideia 1...",
        "Ideia 2...",
        "Ideia 3...",
        "Ideia 4...",
        "Ideia 5..."
    ]
    """
    try:
        ideas = generate_ai_content(prompt, force_json=True)
        if not isinstance(ideas, list) or len(ideas) != 5:
            ideas = [
                f"Que *cor* o tema '{theme}' teria?",
                f"Qual é o *cheiro* que te lembra '{theme}'?",
                f"Tente descrever o *som* principal de '{theme}'.",
                f"Como seria *tocar* em '{theme}'? (É macio, áspero, frio?)",
                "Tente usar uma *comparação* (ex: 'rápido como...' ou 'brilhante como...')."
            ]
        return jsonify({"ideas": ideas})
    except Exception as e:
        print(f"[API /api/get-ideas] Erro: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/find-rhymes', methods=['POST'])
def api_find_rhymes():
    data = request.json
    word = data.get('word')
    theme = data.get('theme')
    if not word:
        return jsonify({"error": "Nenhuma palavra fornecida."}), 400
    prompt = f"""
    Aja como um linguista computacional e poeta, especialista em fonética do português brasileiro.
    Sua tarefa é gerar uma lista de palavras que rimam com '{word}' para um aluno de 11 anos, com o tema '{theme}'.
    **REGRA 1: PRECISÃO FONÉTICA TOTAL (A MAIS IMPORTANTE)**
    A semelhança fonética a partir da sílaba tônica é obrigatória.
    - **Timbre da Vogal:** 'esc**ó**la' (aberto) rima com 'b**ó**la', mas NÃO rima com 'b**ô**la' (fechado). É importante redobrar a atenção com essa regra, por exemplo gol, fechado, não rima com sol, aberto. 
    - **Sons Nasais:** 'coraç**ão**' rima com 'emoç**ão**'.
    - Use todos os parâmetros fonéticos do português brasileiro. 
    **REGRA 2: RELEVÂNCIA (11-13 anos)**
    - Se possível, e apenas se a REGRA 1 for 100% cumprida, prefira palavras do tema '{theme}'.
    - Evite palavras arcaicas ou complexas.
    **Formato da Resposta OBRIGATÓRIO (JSON):**
    Retorne uma lista de objetos. Cada objeto deve ter:
    - "palavra": A palavra que rima.
    - "definicao": Uma definição muito curta e simples (máximo 5 palavras).
    Retorne no mínimo 8 sugestões, se possível.
    """
    try:
        rhymes = generate_ai_content(prompt, force_json=True)
        if not isinstance(rhymes, list):
            rhymes = []
        
        rhymes = [r for r in rhymes if isinstance(r, dict) and r.get('palavra', '').lower() != word.lower()]
        
        if not rhymes:
            rhymes = [{"palavra": "Puxa!", "definicao": f"Não encontrei rimas para '{word}'."}]
            
        return jsonify({"rhymes": rhymes})
    except Exception as e:
        print(f"[API /api/find-rhymes] Erro: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-poem', methods=['POST'])
def api_check_poem():
    data = request.json
    text = data.get('text')
    if not text:
        return jsonify({"errors": []})

    lines = text.split('\n')
    numbered_text = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines) if line.strip())
    prompt = f"""
    Aja como um professor de português experiente e compreensivo, revisando um poema de um aluno de 11 anos.
    O aluno pode usar liberdade poética.
    **Texto do poema (para Contexto):**
    ---
    {numbered_text}
    ---
    **Regras de Correção:**
    1.  **FOCO:** Apenas erros claros de ORTOGRAFIA (ex: 'caza' -> 'casa') e uso de MAIÚSCULAS em início de verso (se o aluno estiver tentando, mas errando).
    2.  **IGNORAR TOTALMENTE:** Não corrija pontuação (vírgulas, pontos), gírias ou separação de versos. ISSO É LIBERDADE POÉTICA.
    3.  **MÚLTIPLAS SUGESTÕES:** Ofereça até 2 correções prováveis.
    4.  **COMENTÁRIO:** Forneça um "motivo" (reason) muito curto e gentil.
    **Formato OBRIGATÓRIO da Resposta (JSON):**
    Retorne uma lista de objetos. Cada objeto deve ter:
    - "original": A palavra com problema (ex: "comeSou").
    - "suggestions": UMA LISTA de strings (ex: ["começou"]).
    - "reason": Uma única string com o motivo (ex: "Palavra escrita com 's' no lugar de 'ç'").
    - "verse_number": O número da linha (começando em 1).
    
    Se não houver erros, retorne uma lista vazia [].
    """
    try:
        errors = generate_ai_content(prompt, force_json=True)
        if not isinstance(errors, list):
            errors = []
        return jsonify({"errors": errors})
    except Exception as e:
        print(f"[API /api/check-poem] Erro: {e}")
        return jsonify({"error": str(e)}), 500


# --- 3. NOVO MOTOR DE GERAÇÃO DE PDF (WeasyPrint) ---
# (Toda a lógica do backend Python permanece inalterada)

@app.route('/api/generate-pdf', methods=['POST'])
def api_generate_pdf():
    data = request.json
    required_fields = ['title', 'author', 'text', 'theme']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Dados incompletos para PDF"}), 400

    try:
        # 1. GERAR O CSS COM A IA
        style_prompt = f"""
        Aja como um designer web e gráfico. O tema do poema é "{data['theme']}".
        Sua tarefa é gerar uma string de CSS para estilizar um PDF de poema.
        REGRAS:
        1.  Gere CSS para as tags: `body`, `h1`, `p`, e a classe `.author`.
        2.  O design deve ser LÚDICO, COLORIDO e FÁCIL DE LER (bom contraste).
        3.  Use fontes seguras (font-family): 'Times New Roman', 'Arial', 'Courier New', 'Helvetica', 'sans-serif'.
        4.  Para o `body`, defina `background-color` (uma cor suave) e `color` (uma cor escura para o texto).
        5.  Para o `h1` (título), defina `color` (uma cor de destaque), `font-size` e `text-align: center`.
        6.  Para o `p` (poema), defina `font-size` (ex: 12pt) e `line-height` (ex: 1.5).
        7.  Para a classe `.author` (autor), defina `text-align: right`, `font-style: italic`, e `margin-top: 20px`.
        8.  Retorne APENAS a string CSS, sem ````css` ou qualquer outra palavra.
        EXEMPLO DE RESPOSTA (APENAS O TEXTO CSS):
        body {{
            font-family: Arial, sans-serif;
            background-color: #F0F8FF;
            color: #333333;
        }}
        h1 {{
            font-family: 'Times New Roman', serif;
            color: #FF6347;
            font-size: 24pt;
            text-align: center;
            border-bottom: 2px solid #FF6347;
            padding-bottom: 10px;
        }}
        p {{
            font-size: 12pt;
            line-height: 1.6;
            margin-bottom: 10px; /* Espaço entre estrofes */
        }}
        .author {{
            text-align: right;
            font-style: italic;
            margin-top: 30px;
            font-size: 14pt;
            color: #555555;
        }}
        """
        
        try:
            css_string = generate_ai_content(style_prompt, force_json=False)
            if "{" not in css_string or "}" not in css_string:
                raise Exception("Estilo CSS retornado pela IA é inválido.")
        except Exception as e:
            print(f"Falha ao gerar estilo de IA, usando padrão. Erro: {e}")
            css_string = """
            body { font-family: Arial, sans-serif; background-color: #F0F8FF; color: #333; }
            h1 { color: #FF6347; font-size: 24pt; text-align: center; border-bottom: 2px solid #FF6347; padding-bottom: 10px; }
            p { font-size: 12pt; line-height: 1.6; margin-bottom: 10px; }
            .author { text-align: right; font-style: italic; margin-top: 30px; font-size: 14pt; }
            """

        # 2. GERAR O HTML
        poem_html = "".join(f"<p>{stanza.replace(os.linesep, '<br>')}</p>" for stanza in data['text'].split(os.linesep * 2))

        html_template = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <style>{css_string}</style>
            </head>
            <body>
                <h1>{data['title']}</h1>
                {poem_html}
                <p class="author">- {data['author']}</p>
            </body>
        </html>
        """

        # 3. RENDERIZAR O PDF (Motor WeasyPrint)
        html = HTML(string=html_template)
        pdf_bytes = html.write_pdf()
        
        # 4. RETORNAR O PDF
        safe_filename = re.sub(r'[^a-z0-9]', '_', data['title'].lower(), re.IGNORECASE) or 'poema'
        
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-disposition": f"attachment; filename={safe_filename}.pdf"}
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return jsonify({"error": f"Erro interno ao gerar PDF: {e}"}), 500


# --- 4. TEMPLATE DO FRONTEND (HTML/CSS/JS - V3 - VISUAL ATUALIZADO) ---

# Frontend completo embutido em uma string Python.
# Usa CSS puro inspirado no 'anos-iniciais.html'.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oficina de Poemas - Python (Flask)</title>
    <!-- Carrega Fonte 'Poppins' (do anos-iniciais.html) -->
    <link href="[https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap](https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap)" rel="stylesheet">
    <style>
        /* Paleta de cores e estilos baseados no 'anos-iniciais.html' */
        :root {
            --cor-primaria: #FFA726; /* Laranja */
            --cor-secundaria: #FF7043; /* Vermelho-Laranja */
            --cor-fundo: #FFF3E0; /* Creme/Pêssego claro */
            --cor-texto: #333;
            --cor-texto-secundario: #555;
            --cor-branco: #FFFFFF;
            --sombra: 0 10px 30px rgba(0, 0, 0, 0.1);
            --sombra-hover: 0 15px 35px rgba(0, 0, 0, 0.15);
        }

        /* --- Configuração Global --- */
        html, body {
            height: 100%;
            margin: 0;
            overflow: hidden; /* Evita scroll no body */
            font-family: 'Poppins', sans-serif;
        }

        body {
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: var(--cor-fundo);
            color: var(--cor-texto);
        }
        
        * {
            box-sizing: border-box;
        }

        /* --- Scrollbar Customizado (para Aside) --- */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--cor-fundo); }
        ::-webkit-scrollbar-thumb { background: var(--cor-primaria); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--cor-secundaria); }

        /* --- Layout Principal --- */
        #app-container {
            width: 95%;
            max-width: 1300px; /* Um pouco maior para a oficina */
            height: 95vh;
            display: flex;
            flex-direction: column;
            margin: auto;
        }

        /* --- Estilo de Card (Baseado no .game-card) --- */
        .card {
            background-color: var(--cor-branco);
            border-radius: 20px;
            padding: 30px;
            box-shadow: var(--sombra);
            transition: all 0.3s ease;
            animation: fadeIn 0.5s ease-out;
            width: 100%;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* --- Estilos de Botão (Baseados no .play-button) --- */
        .btn-primary, .btn-secondary, .btn-correction {
            display: inline-block;
            padding: 12px 30px;
            border-radius: 50px;
            font-weight: 600;
            text-decoration: none;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Poppins', sans-serif;
            font-size: 1em;
            margin-top: 10px;
        }

        .btn-primary {
            background-color: var(--cor-secundaria);
            color: var(--cor-branco);
        }
        .btn-primary:hover {
            background-color: #F4511E; /* Tom mais escuro do .play-button:hover */
            transform: translateY(-3px);
            box-shadow: var(--sombra-hover);
        }
        .btn-primary:disabled {
            background-color: #fab4a1;
            cursor: not-allowed;
        }

        .btn-secondary {
            background-color: var(--cor-branco);
            color: var(--cor-secundaria);
            border: 2px solid var(--cor-primaria);
        }
        .btn-secondary:hover {
            background-color: #fffaf0;
            transform: translateY(-3px);
            box-shadow: var(--sombra-hover);
        }
        .btn-secondary:disabled {
            background-color: #f0f0f0;
            border-color: #ccc;
            color: #999;
            cursor: not-allowed;
        }
        
        /* --- Estilos de Títulos e Textos (Baseados no .portal-header) --- */
        .card h1 {
            font-size: 2.5em; /* Ajustado para o app */
            font-weight: 800;
            color: var(--cor-primaria);
            margin: 0 0 15px;
            text-align: center;
        }
        
        .card p {
            font-size: 1.1em;
            color: var(--cor-secundaria);
            margin: 5px 0 20px;
            text-align: center;
            line-height: 1.6;
        }
        
        .card h3 {
             font-size: 1.5em;
            font-weight: 700;
            color: var(--cor-primaria);
            margin-bottom: 20px;
        }
        
        .card label {
            font-size: 1.2em;
            font-weight: 700;
            color: var(--cor-primaria);
            margin-bottom: 10px;
            display: block;
        }

        /* --- Estilos de Formulário (Inputs, Textarea) --- */
        textarea, input[type="text"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 15px;
            font-family: 'Poppins', sans-serif;
            font-size: 1em;
            box-sizing: border-box;
            margin-top: 10px;
            transition: all 0.3s ease;
        }
        
        textarea:focus, input[type="text"]:focus {
            border-color: var(--cor-primaria);
            outline: none;
            box-shadow: 0 0 12px rgba(255, 167, 38, 0.5);
        }
        
        textarea {
            resize: vertical;
        }
        
        .error-message {
            color: #D32F2F;
            font-weight: 600;
            margin-top: 10px;
            display: none; /* Controlado por JS */
        }
        .hidden {
            display: none !important; /* FORÇA a regra, superando os IDs */
        }

        /* --- Estilos por Etapa --- */

        /* Etapa 1 & 2 & 4 (Centralizadas) */
        #stage-interest, #stage-theme, #stage-pdf {
            width: 100%;
            max-width: 800px;
            margin: auto; /* Centraliza verticalmente e horizontalmente */
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        #interest-input {
            height: 120px;
        }

        /* Etapa 2: Grid de Temas */
        #theme-buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            width: 100%;
        }
        #theme-buttons .btn-secondary {
            width: 100%;
            height: 100px;
            font-size: 1.1em;
            white-space: normal;
            line-height: 1.4;
        }
        
        /* Etapa 4: Inputs de PDF */
        #stage-pdf input[type="text"] {
            font-size: 1.1em;
            text-align: center;
        }

        /* Etapa 3: Layout da Oficina */
        #stage-writing {
            display: flex;
            flex-direction: row;
            gap: 30px;
            height: 100%;
            width: 100%;
        }

        #stage-writing main {
            flex: 3;
            display: flex;
            flex-direction: column;
            gap: 20px;
            height: 100%; /* Ocupa altura total do container */
        }
        
        #stage-writing aside {
            flex: 2;
            display: flex;
            flex-direction: column;
            gap: 20px;
            height: 100%; /* Ocupa altura total */
            overflow-y: auto; /* Permite scroll APENAS na sidebar */
            padding-right: 10px; /* Evita que o scrollbar cole no conteúdo */
        }
        
        #stage-writing header.card {
            flex-shrink: 0; /* Não encolhe */
            padding: 20px;
        }
        #stage-writing header.card h1 {
            font-size: 2em;
            margin-bottom: 5px;
            text-align: left;
        }
        #stage-writing header.card p {
            font-size: 1.1em;
            text-align: left;
            margin: 0;
            color: var(--cor-texto-secundario);
        }
        
        /* Editor Principal */
        #editor-card {
            flex-grow: 1; /* Ocupa o espaço restante */
            display: flex;
            flex-direction: column;
        }
        #poem-editor {
            flex-grow: 1; /* Textarea ocupa espaço do card */
            font-size: 1.1em;
            line-height: 1.7;
        }
        
        #writing-actions {
            flex-shrink: 0;
            display: flex;
            flex-direction: row;
            gap: 20px;
        }
        #writing-actions .btn-secondary,
        #writing-actions .btn-primary {
            flex: 1;
        }

        /* Estatísticas */
        #stats-container {
            display: flex;
            justify-content: space-around;
            text-align: center;
        }
        #stats-container .stat-value {
            font-size: 2.5em;
            font-weight: 800;
            color: var(--cor-primaria);
        }
        #stats-container .stat-label {
            font-size: 0.9em;
            color: var(--cor-texto-secundario);
        }
        
        /* Caça-Rimas */
        #rhyme-search {
            display: flex;
            gap: 10px;
        }
        #rhyme-input {
            flex-grow: 1;
            margin-top: 0;
        }
        #btn-get-rhymes {
            flex-shrink: 0;
            margin-top: 0;
            padding: 10px 20px;
        }
        #rhyme-results {
            margin-top: 20px;
            max-height: 180px;
            overflow-y: auto;
            font-size: 0.9em;
        }
        #rhyme-results ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        #rhyme-results li {
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        #rhyme-results li strong {
            color: var(--cor-secundaria);
        }
        #rhyme-results .placeholder {
            color: #999;
            font-style: italic;
        }
        
        /* Inspiração */
        #progression-ideas-list {
            list-style: none;
            padding-left: 10px;
            margin: 0;
        }
        #progression-ideas-list li {
            padding: 8px 0;
            color: var(--cor-texto-secundario);
            font-size: 0.95em;
            line-height: 1.6;
            border-bottom: 1px dashed #eee;
        }
        #progression-ideas-list li::before {
            content: '💡';
            margin-right: 10px;
        }

        /* Correções */
        #corrections-container {
            flex-shrink: 0;
            max-height: 250px;
            overflow-y: auto;
        }
        #corrections-list .correction-verse {
            padding: 15px 0;
            border-bottom: 1px solid #eee;
        }
        #corrections-list .correction-verse:last-child {
            border-bottom: none;
        }
        #corrections-list h4 {
            font-weight: 700;
            color: var(--cor-texto);
            font-size: 1.1em;
        }
        #corrections-list .correction-item {
            margin-left: 10px;
            margin-top: 10px;
        }
        #corrections-list .original-word {
            color: #D32F2F;
            text-decoration: line-through;
            font-weight: 600;
        }
        #corrections-list .reason {
            font-style: italic;
            color: #666;
            font-size: 0.9em;
            margin: 5px 0 10px;
        }
        #corrections-list .suggestion-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .btn-correction {
            background-color: var(--cor-fundo);
            color: var(--cor-secundaria);
            border: 1px solid var(--cor-secundaria);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
        }
        .btn-correction:hover {
            background-color: var(--cor-secundaria);
            color: var(--cor-branco);
            transform: scale(1.05);
        }
        
        /* --- Animações de Loading (Baseado no app.py, re-colorido) --- */
        .loader {
            width: 50px; height: 50px;
            border: 6px solid var(--cor-branco);
            border-bottom-color: var(--cor-secundaria);
            border-radius: 50%;
            display: inline-block;
            box-sizing: border-box;
            animation: rotation 1s linear infinite;
        }
        @keyframes rotation { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        #loading-overlay {
            position: fixed;
            inset: 0;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 50;
            transition: opacity 0.3s;
        }
        .loading-hidden {
            opacity: 0;
            pointer-events: none;
        }

    </style>
</head>
<body>

    <!-- Container principal da aplicação -->
    <div id="app-container">
    
        <!-- ETAPA 1: Interesses (DUA - Recrutar Interesse) -->
        <div id="stage-interest" class="card stage">
            <h1>Vamos Criar um Poema! 🚀</h1>
            <p>Para começar, me conte do que você mais gosta. Pode ser um jogo, um animal, um lugar, ou um sentimento!</p>
            <textarea id="interest-input" placeholder="Ex: Gosto de jogar futebol no parque, do meu cachorro e de olhar as estrelas..."></textarea>
            <button id="btn-get-themes" class="btn-primary">
                Gerar Ideias de Temas →
            </button>
            <p id="interest-error" class="error-message">Por favor, escreva algo para começar!</p>
        </div>

        <!-- ETAPA 2: Escolha do Tema -->
        <div id="stage-theme" class="card stage hidden">
            <h1>Ótimas Ideias! ✨</h1>
            <p>Pensei nestes temas com base no que você escreveu. Escolha um para começar:</p>
            <div id="theme-buttons">
                <!-- Botões de tema serão inseridos aqui pelo JS -->
            </div>
            <button id="btn-back-interest" class="btn-secondary">← Voltar</button>
        </div>

        <!-- ETAPA 3: Oficina de Poemas (Layout principal) -->
        <div id="stage-writing" class="stage hidden">
            
            <!-- Coluna Principal: Editor e Correções -->
            <main>
                <header class="card">
                    <h1>✍️ Oficina de Poemas</h1>
                    <p>Tema: <strong id="chosen-theme-title"></strong></p>
                </header>
                
                <!-- Editor de Poema -->
                <div id="editor-card" class="card">
                    <label for="poem-editor">Escreva seu poema aqui:</label>
                    <textarea id="poem-editor" placeholder="O sol se põe no horizonte..."></textarea>
                </div>
                
                <!-- Botões de Ação -->
                <div id="writing-actions">
                    <button id="btn-check-spelling" class="btn-secondary">🕵️‍♀️ Revisar Ortografia</button>
                    <button id="btn-finish-poem" class="btn-primary">Concluir Poema 🏁</button>
                </div>
                
                <!-- Container de Correções (DUA - Feedback Construtivo) -->
                <div id="corrections-container" class="card hidden">
                    <h3>Dicas do Assistente</h3>
                    <div id="corrections-list">
                        <!-- Correções serão inseridas aqui -->
                    </div>
                </div>
            </main>

            <!-- Coluna Lateral: Ferramentas de Apoio (DUA - Suporte) -->
            <aside>
                <!-- Caça-Rimas (BNCC - EF67LP31) -->
                <div class="card">
                    <h3>🔎 Caça-Rimas</h3>
                    <div id="rhyme-search">
                        <input type="text" id="rhyme-input" placeholder="Digite uma palavra...">
                        <button id="btn-get-rhymes" class="btn-secondary">Buscar</button>
                    </div>
                    <div id="rhyme-results">
                        <p class="placeholder">Digite uma palavra e clique em "Buscar" para ver as rimas.</p>
                    </div>
                </div>

                <!-- 5 Ideias de Progressão (NOVO - V3) -->
                <div class="card">
                    <h3>💡 Inspiração Criativa</h3>
                    <ul id="progression-ideas-list">
                        <li class="placeholder">Aguardando ideias...</li>
                    </ul>
                </div>
                
                <!-- Estatísticas -->
                <div class="card">
                    <h3>📊 Estatísticas</h3>
                    <div id="stats-container">
                        <div>
                            <div id="stat-verses" class="stat-value">0</div>
                            <div class="stat-label">Versos</div>
                        </div>
                        <div>
                            <div id="stat-stanzas" class="stat-value">0</div>
                            <div class="stat-label">Estrofes</div>
                        </div>
                    </div>
                </div>
                <button id="btn-back-theme" class="btn-secondary">← Mudar Tema</button>
            </aside>
        </div>
        
        <!-- ETAPA 4: Finalização e PDF -->
        <div id="stage-pdf" class="card stage hidden">
            <h1>Seu Poema está Lindo! 🏆</h1>
            <p>Vamos dar os toques finais para criar seu PDF personalizado.</p>
            <div>
                <input type="text" id="pdf-title" placeholder="Qual o título do poema?">
                <input type="text" id="pdf-author" placeholder="Qual o nome do(a) poeta? (Seu nome!)">
            </div>
            <p id="pdf-error" class="error-message">Por favor, preencha o título e seu nome!</p>
            <button id="btn-generate-pdf" class="btn-primary">
                Gerar PDF Mágico ✨
            </button>
            <button id="btn-back-writing" class="btn-secondary">← Voltar para Edição</button>
        </div>
    </div>

    <!-- Overlay de Carregamento Global -->
    <div id="loading-overlay" class="loading-hidden">
        <div class="loader"></div>
    </div>

    <!-- JavaScript da Aplicação (Funcionalidade JS permanece inalterada) -->
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            // --- Variáveis de Estado e Elementos ---
            const appState = {
                chosenTheme: '',
                poemText: '',
                currentErrors: []
            };

            const stages = {
                interest: document.getElementById('stage-interest'),
                theme: document.getElementById('stage-theme'),
                writing: document.getElementById('stage-writing'),
                pdf: document.getElementById('stage-pdf')
            };

            const loadingOverlay = document.getElementById('loading-overlay');
            const allButtons = document.querySelectorAll('button');

            // --- Funções de UI (Navegação e Carregamento) ---
            function showStage(stageId) {
                Object.values(stages).forEach(stage => stage.classList.add('hidden'));
                if (stages[stageId]) {
                    stages[stageId].classList.remove('hidden');
                    // Não é mais necessário definir o style.display aqui,
                    // o CSS cuidará disso quando a classe .hidden for removida.
                }
            }

            function showLoading(show) {
                loadingOverlay.classList.toggle('loading-hidden', !show);
                allButtons.forEach(btn => btn.disabled = show);
            }
            
            function showToast(message, isError = false) {
                // (Em um app maior, usaríamos uma biblioteca de toast)
                alert(message);
                if(isError) console.error(message);
            }

            // --- Função de API Helper (Otimizada) ---
            async function fetchAPI(endpoint, body) {
                showLoading(true);
                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    
                    const contentType = response.headers.get("content-type");
                    
                    // Caso 1: Download de PDF
                    if (contentType && contentType.includes("application/pdf")) {
                        if (!response.ok) throw new Error('Falha ao gerar o PDF.');
                        return await response.blob();
                    }
                    
                    // Caso 2: Resposta JSON
                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.error || `Erro na API: ${response.statusText}`);
                    }
                    return data;

                } catch (error) {
                    console.error('Erro no fetchAPI:', error);
                    showToast(`Ocorreu um erro ao conectar com o assistente: ${error.message}`, true);
                    return null;
                } finally {
                    showLoading(false);
                }
            }

            // --- ETAPA 1: Lógica de Interesses ---
            const interestInput = document.getElementById('interest-input');
            const interestError = document.getElementById('interest-error');
            document.getElementById('btn-get-themes').addEventListener('click', async () => {
                const interest = interestInput.value.trim();
                if (!interest) {
                    interestError.style.display = 'block';
                    return;
                }
                interestError.style.display = 'none';
                
                const data = await fetchAPI('/api/generate-themes', { interest });
                if (data && data.themes) {
                    const themeButtons = document.getElementById('theme-buttons');
                    themeButtons.innerHTML = ''; // Limpa temas antigos
                    data.themes.forEach(theme => {
                        const button = document.createElement('button');
                        button.textContent = theme;
                        button.className = 'btn-secondary'; // Usa o novo estilo
                        button.title = theme;
                        button.onclick = () => handleThemeChoice(theme);
                        themeButtons.appendChild(button);
                    });
                    showStage('theme');
                }
            });

            // --- ETAPA 2: Lógica de Temas ---
            document.getElementById('btn-back-interest').addEventListener('click', () => showStage('interest'));

            async function handleThemeChoice(theme) {
                appState.chosenTheme = theme;
                document.getElementById('chosen-theme-title').textContent = theme;
                
                const ideasList = document.getElementById('progression-ideas-list');
                ideasList.innerHTML = '<li class="placeholder">A carregar ideias...</li>';
                
                const data = await fetchAPI('/api/get-ideas', { theme });
                
                ideasList.innerHTML = ''; // Limpa
                if (data && data.ideas) {
                    data.ideas.forEach(idea => {
                        const li = document.createElement('li');
                        li.textContent = idea;
                        ideasList.appendChild(li);
                    });
                } else {
                    ideasList.innerHTML = '<li class="placeholder" style="color: red;">Erro ao carregar ideias.</li>';
                }
                
                showStage('writing');
            }

            // --- ETAPA 3: Lógica da Oficina de Poemas ---
            const poemEditor = document.getElementById('poem-editor');
            const rhymeInput = document.getElementById('rhyme-input');
            const rhymeResults = document.getElementById('rhyme-results');
            const correctionsContainer = document.getElementById('corrections-container');
            const correctionsList = document.getElementById('corrections-list');

            // Voltar
            document.getElementById('btn-back-theme').addEventListener('click', () => showStage('theme'));

            // Estatísticas (DUA - Feedback imediato)
            poemEditor.addEventListener('input', () => {
                appState.poemText = poemEditor.value;
                const lines = appState.poemText.split('\\n');
                const verses = lines.filter(line => line.trim().length > 0).length;
                const stanzas = appState.poemText.split('\\n\\n').filter(s => s.trim().length > 0).length;
                
                document.getElementById('stat-verses').textContent = verses;
                document.getElementById('stat-stanzas').textContent = stanzas;
            });

            // Buscar Rimas
            document.getElementById('btn-get-rhymes').addEventListener('click', async () => {
                const word = rhymeInput.value.trim();
                if (!word) return;
                
                rhymeResults.innerHTML = '<p class="placeholder">Buscando...</p>';
                const data = await fetchAPI('/api/find-rhymes', { word, theme: appState.chosenTheme });
                
                rhymeResults.innerHTML = ''; // Limpa
                if (data && data.rhymes) {
                    if (data.rhymes[0].palavra === "Erro" || data.rhymes[0].palavra === "Puxa!") {
                        rhymeResults.innerHTML = `<p class="placeholder">${data.rhymes[0].definicao}</p>`;
                    } else {
                        const list = document.createElement('ul');
                        data.rhymes.forEach(r => {
                            const li = document.createElement('li');
                            li.innerHTML = `<strong>${r.palavra}:</strong> <span>${r.definicao}</span>`;
                            list.appendChild(li);
                        });
                        rhymeResults.appendChild(list);
                    }
                } else {
                    rhymeResults.innerHTML = '<p class="placeholder" style="color: red;">Falha ao buscar rimas.</p>';
                }
            });

            // Revisar Ortografia
            document.getElementById('btn-check-spelling').addEventListener('click', async () => {
                if (!appState.poemText) return;
                
                const data = await fetchAPI('/api/check-poem', { text: appState.poemText });
                if (data) {
                    appState.currentErrors = data.errors || [];
                    renderCorrections();
                }
            });
            
            function renderCorrections() {
                correctionsList.innerHTML = '';
                if (appState.currentErrors.length === 0) {
                    correctionsContainer.classList.add('hidden');
                    showToast("Nenhum problema de ortografia encontrado! 🎉");
                    return;
                }
                
                const errorsByVerse = {};
                appState.currentErrors.forEach(err => {
                    if (!errorsByVerse[err.verse_number]) errorsByVerse[err.verse_number] = [];
                    errorsByVerse[err.verse_number].push(err);
                });

                Object.keys(errorsByVerse).sort((a,b) => a-b).forEach(verseNum => {
                    const verseDiv = document.createElement('div');
                    verseDiv.className = 'correction-verse';
                    verseDiv.innerHTML = `<h4>No Verso ${verseNum}:</h4>`;
                    
                    errorsByVerse[verseNum].forEach(error => {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'correction-item';
                        errorDiv.innerHTML = `<p>Você escreveu <strong class="original-word">${error.original}</strong></p>
                                            <p class="reason">${error.reason}</p>`;
                        
                        const buttonsDiv = document.createElement('div');
                        buttonsDiv.className = 'suggestion-buttons';
                        error.suggestions.forEach(suggestion => {
                            const button = document.createElement('button');
                            button.textContent = suggestion;
                            button.className = 'btn-correction';
                            button.onclick = () => applyCorrection(error.original, suggestion, error.verse_number);
                            buttonsDiv.appendChild(button);
                        });
                        errorDiv.appendChild(buttonsDiv);
                        verseDiv.appendChild(errorDiv);
                    });
                    correctionsList.appendChild(verseDiv);
                });
                
                correctionsContainer.classList.remove('hidden');
            }

            function applyCorrection(original, suggestion, verseNum) {
                const lines = poemEditor.value.split('\\n');
                const lineIndex = verseNum - 1;

                if (lines[lineIndex]) {
                    const regex = new RegExp(`\\b${original}\\b`, 'i');
                    if (regex.test(lines[lineIndex])) {
                         lines[lineIndex] = lines[lineIndex].replace(regex, suggestion);
                    }
                }
                
                poemEditor.value = lines.join('\\n');
                poemEditor.dispatchEvent(new Event('input')); // Atualiza estatísticas

                appState.currentErrors = appState.currentErrors.filter(err => 
                    !(err.original === original && err.verse_number == verseNum)
                );
                
                renderCorrections();
            }

            // Concluir Poema
            document.getElementById('btn-finish-poem').addEventListener('click', () => {
                if (appState.poemText.trim().length < 10) {
                    showToast("Seu poema parece um pouco curto. Escreva mais um pouco!");
                    return;
                }
                showStage('pdf');
            });

            // --- ETAPA 4: Lógica do PDF ---
            const pdfTitle = document.getElementById('pdf-title');
            const pdfAuthor = document.getElementById('pdf-author');
            const pdfError = document.getElementById('pdf-error');

            document.getElementById('btn-back-writing').addEventListener('click', () => showStage('writing'));
            
            document.getElementById('btn-generate-pdf').addEventListener('click', async () => {
                const title = pdfTitle.value.trim();
                const author = pdfAuthor.value.trim();
                
                if (!title || !author) {
                    pdfError.style.display = 'block';
                    return;
                }
                pdfError.style.display = 'none';
                
                const blob = await fetchAPI('/api/generate-pdf', {
                    title,
                    author,
                    text: appState.poemText,
                    theme: appState.chosenTheme
                });

                if (blob) {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    const safeFilename = title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
                    a.download = `${safeFilename || 'meu_poema'}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                }
            });

            // --- Inicialização ---
            showLoading(false); // Garante que o loading esteja oculto
            showStage('interest');
        });
    </script>
</body>
</html>
"""

# --- 5. ROTA PRINCIPAL DO FLASK ---

@app.route('/')
def home():
    """Serve o frontend principal (HTML/CSS/JS)."""
    return render_template_string(HTML_TEMPLATE)

# --- 6. INICIALIZAÇÃO DA APLICAÇÃO ---

if __name__ == '__main__':
    # Verifica a chave de API na inicialização
    if not API_KEY:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!! AVISO: A GOOGLE_API_KEY não está configurada.         !!")
        print("!! Defina-a como uma variável de ambiente para a IA     !!")
        print("!! funcionar. (ex: export GOOGLE_API_KEY='sua_chave')   !!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    
    # Inicializa o modelo na inicialização para verificar a chave
    get_model()
    
    # Configura a porta para produção (Render) ou 5000 para desenvolvimento
    port = int(os.environ.get("PORT", 5000))
    # 'debug=False' é crucial para produção no Render.
    # 'host=0.0.0.0' é necessário para o Render.
    app.run(debug=False, host='0.0.0.0', port=port)

