import os
import re
import json
import google.generativeai as genai
from flask import Flask, jsonify, request, Response, render_template_string
from fpdf import FPDF
from datetime import datetime
from math import cos as _cos, sin as _sin
from collections import defaultdict

# --- 1. CONFIGURAÇÃO DA APLICAÇÃO FLASK E API GEMINI ---

app = Flask(__name__)

# Configuração da API Key
# O Render (serviço de deploy) irá injetar esta variável do "Environment"
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
        # SUCESSO! Usando o 'gemini-pro-latest' como modelo principal (O Confiável).
        model = genai.GenerativeModel('gemini-pro-latest')
        print("Modelo 'gemini-pro-latest' configurado com sucesso.")
        return model
    except Exception as e:
        print(f"Erro ao configurar o 'gemini-pro-latest': {e}")
        # Tenta o 'gemini-flash-latest' como fallback (O Rápido)
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
    model = get_model() # <- Corrigido para chamar a função correta
    if model is None:
        raise Exception("Modelo de IA não inicializado. Verifique a API Key e as permissões no Google Cloud.")

    try:
        # Configuração para forçar a saída em JSON se solicitado
        generation_config = {}
        if force_json:
            generation_config["response_mime_type"] = "application/json"

        response = model.generate_content(prompt_text, generation_config=generation_config)
        
        text = response.text
        
        # Limpeza robusta para extrair JSON de blocos de markdown
        if force_json or '[' in text or '{' in text:
            match = re.search(r'```(json)?(.*)```', text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(2).strip()
            
            # Tenta carregar o JSON
            return json.loads(text)
        
        # Retorna texto plano se não for JSON
        return text

    except Exception as e:
        print(f"Erro na geração de conteúdo da IA: {e}")
        print(f"Prompt que falhou: {prompt_text}")
        # Tenta extrair a resposta de erro da API se disponível
        try:
            # Tenta extrair a mensagem de erro específica do gRPC/Google
            if hasattr(e, 'message'):
                error_message = e.message
            elif hasattr(e, 'args') and e.args:
                error_message = str(e.args[0])
            else:
                error_message = str(e)

            # Verifica se o erro é o 404 que estávamos vendo
            if "is not found" in error_message:
                 print("!! ERRO 404 DETECTADO: Verifique o nome do modelo e as permissões da API Key !!")
                 raise Exception(f"Erro 404 da API Gemini: {error_message}")
            
            raise Exception(f"Falha ao gerar ou processar resposta da IA: {error_message}")

        except json.JSONDecodeError:
            print(f"Erro de JSON: A IA não retornou um JSON válido. Resposta: {text}")
            raise Exception(f"A IA não retornou um JSON válido. Resposta: {text}")
        except Exception as e_inner:
             raise e_inner # Mantém a exceção original


# --- 2. LÓGICA DE IA PEDAGÓGICA (PROMPTS OTIMIZADOS) ---

@app.route('/api/generate-themes', methods=['POST'])
def api_generate_themes():
    """
    (DUA - Recrutar Interesse)
    Gera temas com base nos interesses do aluno.
    """
    data = request.json
    interest = data.get('interest', 'amigos e escola')

    # PROMPT OTIMIZADO: Mais específico, focado no 6º ano, formato JSON forçado.
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

# --- NOVO ENDPOINT DE IDEIAS ESTÁTICAS ---
@app.route('/api/get-ideas', methods=['POST'])
def api_get_ideas():
    """
    (DUA - Suporte)
    Gera 5 ideias de progressão temática estáticas com base no tema.
    """
    data = request.json
    theme = data.get('theme')
    if not theme:
        return jsonify({"error": "Nenhum tema fornecido."}), 400

    # PROMPT OTIMIZADO: Pede 5 ideias focadas nos sentidos (BNCC/DUA).
    prompt = f"""
    Aja como um professor de escrita criativa. O tema do poema é '{theme}'.
    Gere uma lista de 5 ideias CURTAS (máximo 10 palavras cada) para um aluno do 6º ano.
    As ideias devem ser perguntas ou comandos para inspirar a escrita.

    REGRAS:
    1.  Foco nos 5 sentidos (visão, som, cheiro, tato, paladar).
    2.  Seja simples e lúdico.
    3.  Retorne APENAS uma lista de 5 strings em JSON.
    
    Exemplo de Resposta:
    ["O que você vê quando pensa em {theme}?", "Qual é o som do {theme}?", "Que cheiro tem o {theme}?", "Como seria tocar o {theme}?", "Tente comparar {theme} com um animal."]
    """
    try:
        ideas = generate_ai_content(prompt, force_json=True)
        if not isinstance(ideas, list) or len(ideas) == 0:
            raise Exception("A IA não retornou uma lista de ideias.")
        
        # Garante que temos exatamente 5 ideias
        if len(ideas) > 5:
            ideas = ideas[:5]
        elif len(ideas) < 5:
            # Fallback caso a IA falhe
            ideas = [
                f"Como é o cheiro de '{theme}'?",
                f"Qual é o som principal de '{theme}'?",
                f"Que cores você vê em '{theme}'?",
                f"O que '{theme}' faz você sentir?",
                f"Tente comparar '{theme}' com outra coisa."
            ]
            
        return jsonify({"ideas": ideas})
    except Exception as e:
        print(f"[API /api/get-ideas] Erro: {e}")
        return jsonify({"error": str(e)}), 500
# --- FIM DO NOVO ENDPOINT ---

@app.route('/api/find-rhymes', methods=['POST'])
def api_find_rhymes():
    """
    (BNCC - EF67LP31 - Recursos Sonoros)
    Busca rimas com alta precisão fonética.
    """
    data = request.json
    word = data.get('word')
    theme = data.get('theme')
    if not word:
        return jsonify({"error": "Nenhuma palavra fornecida."}), 400

    # PROMPT OTIMIZADO: Mantém a regra de precisão fonética (essencial), mas força JSON e melhora a definição.
    prompt = f"""
    Aja como um linguista computacional e poeta, especialista em fonética do português brasileiro.
    Sua tarefa é gerar uma lista de palavras que rimam com '{word}' para um aluno de 11 anos, com o tema '{theme}'.

    **REGRA 1: PRECISÃO FONÉTICA TOTAL (A MAIS IMPORTANTE)**
    A semelhança fonética a partir da sílaba tônica é obrigatória.
    - **Timbre da Vogal:** 'esc**ó**la' (aberto) rima com 'b**ó**la', mas NÃO rima com 'b**ô**la' (fechado).
    - **Sons Nasais:** 'coraç**ão**' rima com 'emoç**ão**'.

    **REGRA 2: RELEVÂNCIA (11-13 anos)**
    - Se possível, e apenas se a REGRA 1 for 100% cumprida, prefira palavras do tema '{theme}'.
    - Evite palavras arcaicas ou complexas.

    **Formato da Resposta:**
    Retorne uma lista de objetos JSON. Cada objeto deve ter:
    - "palavra": A palavra que rima.
    - "definicao": Uma definição muito curta e simples (máximo 5 palavras).
    Retorne no mínimo 8 sugestões, se possível.
    """
    try:
        rhymes = generate_ai_content(prompt, force_json=True)
        if not isinstance(rhymes, list):
            rhymes = []
        
        # Filtra a palavra original
        rhymes = [r for r in rhymes if isinstance(r, dict) and r.get('palavra', '').lower() != word.lower()]
        
        if not rhymes:
            rhymes = [{"palavra": "Puxa!", "definicao": f"Não encontrei rimas para '{word}'."}]
            
        return jsonify({"rhymes": rhymes})
    except Exception as e:
        print(f"[API /api/find-rhymes] Erro: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-poem', methods=['POST'])
def api_check_poem():
    """
    (BNCC - EF69LP51 - Revisão)
    Verifica ortografia e uso básico de maiúsculas, ignorando pontuação.
    """
    data = request.json
    text = data.get('text')
    if not text:
        return jsonify({"errors": []})

    lines = text.split('\n')
    numbered_text = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines) if line.strip())

    # PROMPT OTIMIZADO: Regras mais claras, foco em ignorar pontuação (liberdade poética).
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


# --- 3. LÓGICA DE GERAÇÃO DE PDF (fpdf2) ---

class PoemPDF(FPDF):
    """Classe customizada do FPDF para gerar o PDF com bordas e estilos da IA."""
    def __init__(self, style_guide, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style = style_guide
        # Converte cores hex para RGB
        try:
            self.bg_r, self.bg_g, self.bg_b = tuple(int(self.style.get('bg_color_hex', '#FFFFFF').lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            self.text_r, self.text_g, self.text_b = tuple(int(self.style.get('text_color_hex', '#000000').lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            self.title_r, self.title_g, self.title_b = tuple(int(self.style.get('title_color_hex', '#000000').lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            self.border_r, self.border_g, self.border_b = tuple(int(self.style.get('border_color_hex', '#4682B4').lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        except Exception as e:
            print(f"Erro ao converter cores HEX: {e}. Usando padrões.")
            self.bg_r, self.bg_g, self.bg_b = (240, 248, 255) # AliceBlue
            self.text_r, self.text_g, self.text_b = (47, 79, 79)     # DarkSlateGray
            self.title_r, self.title_g, self.title_b = (255, 99, 71)   # Tomato
            self.border_r, self.border_g, self.border_b = (70, 130, 180)  # SteelBlue

    def header(self):
        self.set_fill_color(self.bg_r, self.bg_g, self.bg_b)
        self.rect(0, 0, self.w, self.h, 'F')
        self.draw_border()

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Gerado pela Oficina de Poemas - {datetime.now().strftime("%d/%m/%Y")}', 0, 0, 'C')

    def draw_border(self):
        style = self.style.get('border_style', 'simples')
        self.set_draw_color(self.border_r, self.border_g, self.border_b)
        
        if style == 'dupla':
            self.set_line_width(1)
            self.rect(5, 5, self.w - 10, self.h - 10)
            self.set_line_width(0.5)
            self.rect(7, 7, self.w - 14, self.h - 14)
        elif style == 'ondas':
            self.draw_waves()
        elif style == 'estrelas':
            self.draw_stars()
        else: # Padrão 'simples'
            self.set_line_width(1)
            self.rect(5, 5, self.w - 10, self.h - 10)

    def draw_waves(self):
        margin, step, amplitude = 10, 5, 2
        self.set_line_width(0.5)
        for x in range(margin, int(self.w - margin), step):
            self.curve(x, margin, x + step / 2, margin - amplitude, x + step, margin)
            self.curve(x, self.h - margin, x + step / 2, self.h - margin + amplitude, x + step, self.h - margin)
        for y in range(margin, int(self.h - margin), step):
            self.curve(margin, y, margin - amplitude, y + step/2, margin, y + step)
            self.curve(self.w - margin, y, self.w - margin + amplitude, y + step/2, self.w - margin, y + step)

    def draw_stars(self):
        self.set_line_width(0.2)
        self.set_fill_color(self.border_r, self.border_g, self.border_b)
        self.draw_star(20, 20); self.draw_star(self.w - 20, 20)
        self.draw_star(20, self.h - 20); self.draw_star(self.w - 20, self.h - 20)

    def draw_star(self, x, y, size=10):
        p = []
        for i in range(5):
            angle = i * 2 * 3.14159 / 5 - 3.14159 / 2
            radius = size if i % 2 == 0 else size / 2.5
            p.append((x + radius * _cos(angle), y + radius * _sin(angle)))
        self.polygon(p, 'F')

@app.route('/api/generate-pdf', methods=['POST'])
def api_generate_pdf():
    """Gera o PDF estilizado e o retorna como um arquivo."""
    data = request.json
    required_fields = ['title', 'author', 'text', 'theme']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Dados incompletos para PDF"}), 400

    try:
        # PROMPT OTIMIZADO: Mais restrito para garantir saída JSON válida.
        style_prompt = f"""
        Aja como um designer gráfico. O tema do poema é "{data['theme']}".
        Retorne um objeto JSON com uma paleta de design lúdica.

        **Chaves obrigatórias no JSON:**
        - "font": Escolha UMA: "Courier", "Helvetica", "Times".
        - "bg_color_hex": Cor de fundo suave (ex: "#F0F8FF").
        - "text_color_hex": Cor de texto escura e legível (ex: "#333333").
        - "title_color_hex": Cor de destaque para o título (ex: "#FF6347").
        - "border_style": Escolha UM: "simples", "dupla", "ondas", "estrelas".
        - "border_color_hex": Cor para a borda (ex: "#4682B4").
        """
        
        try:
            style = generate_ai_content(style_prompt, force_json=True)
            if not isinstance(style, dict):
                raise Exception("Estilo retornado não é um dicionário.")
        except Exception as e:
            print(f"Falha ao gerar estilo de IA, usando padrão. Erro: {e}")
            style = {
                "font": "Helvetica", "bg_color_hex": "#F0F8FF", 
                "text_color_hex": "#2F4F4F", "title_color_hex": "#FF6347",
                "border_style": "simples", "border_color_hex": "#4682B4"
            }

        # Gera o PDF em memória
        pdf = PoemPDF(style)
        pdf.add_page()
        
        # Adiciona Título
        pdf.set_font(style.get('font', 'Helvetica'), 'B', 24)
        pdf.set_text_color(pdf.title_r, pdf.title_g, pdf.title_b)
        pdf.multi_cell(0, 15, data['title'], align='C')
        pdf.ln(20)
        
        # Adiciona Poema
        pdf.set_font(style.get('font', 'Helvetica'), '', 12)
        pdf.set_text_color(pdf.text_r, pdf.text_g, pdf.text_b)
        # Corrige encoding para FPDF (latin-1)
        poem_text_encoded = data['text'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, poem_text_encoded)
        pdf.ln(10)
        
        # Adiciona Autor
        pdf.set_font(style.get('font', 'Helvetica'), 'I', 14)
        author_encoded = data['author'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, f'- {author_encoded}', align='R')
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        # Retorna o PDF como um arquivo para download
        safe_filename = re.sub(r'[^a-z0-9]', '_', data['title'].lower(), re.IGNORECASE) or 'poema'
        
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-disposition": f"attachment; filename={safe_filename}.pdf"}
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return jsonify({"error": f"Erro interno ao gerar PDF: {e}"}), 500


# --- 4. TEMPLATE DO FRONTEND (HTML/CSS/JS) ---

# Frontend completo embutido em uma string Python.
# Usa TailwindCSS para um design moderno e acessível (DUA).
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oficina de Poemas - Python (Flask)</title>
    <!-- Carrega TailwindCSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Carrega Fontes (Lúdica + Padrão) -->
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Playpen+Sans:wght@400;600&display=swap" rel="stylesheet">
    <style>
        /* Estilos customizados (DUA/Lúdico) */
        body {
            font-family: 'Roboto', sans-serif;
            background-color: #f0f4f8; /* Fundo suave (slate-100) */
            color: #1e293b; /* Texto principal (slate-800) */
        }
        /* Fonte lúdica para títulos */
        .font-playful {
            font-family: 'Playpen Sans', cursive;
        }
        /* Botão principal (DUA - Chama a atenção) */
        .btn-primary {
            @apply bg-indigo-600 text-white font-bold py-3 px-6 rounded-full shadow-lg transition-transform transform hover:scale-105 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-50 disabled:bg-indigo-300;
        }
        /* Botão secundário */
        .btn-secondary {
            @apply bg-slate-200 text-slate-700 font-semibold py-2 px-4 rounded-full shadow-sm transition-colors hover:bg-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:bg-slate-100;
        }
        /* Botão de correção (DUA - Feedback) */
        .btn-correction {
             @apply bg-emerald-100 text-emerald-800 font-medium py-1 px-3 rounded-full text-sm transition-colors hover:bg-emerald-200 focus:outline-none focus:ring-2 focus:ring-emerald-400;
        }
        /* Card (DUA - separação de conteúdo) */
        .card {
            @apply bg-white rounded-2xl shadow-xl p-6 transition-all;
        }
        /* Foco acessível (WCAG) */
        textarea:focus, input:focus, button:focus-visible {
            @apply ring-2 ring-indigo-500 ring-opacity-75 outline-none;
        }
        /* Scrollbar customizado (para Chromebooks/Estética) */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #e0e7ff; }
        ::-webkit-scrollbar-thumb { background: #6366f1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #4f46e5; }
        
        /* Spinner de carregamento (dentro do overlay) */
        .loader {
            width: 48px; height: 48px;
            border: 5px solid #FFF;
            border-bottom-color: #6366f1;
            border-radius: 50%;
            display: inline-block;
            box-sizing: border-box;
            animation: rotation 1s linear infinite;
        }
        @keyframes rotation { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        /* Overlay de carregamento (DUA - Feedback de processo) */
        #loading-overlay {
            @apply fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 transition-opacity duration-300;
        }
        .loading-hidden {
            @apply opacity-0 pointer-events-none;
        }
        
        /* Efeito de fade-in para as etapas */
        .stage {
            animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen p-4">

    <!-- Container principal da aplicação (evita rolagem no body) -->
    <div class="w-full max-w-7xl mx-auto h-[95vh] flex flex-col">
    
        <!-- ETAPA 1: Interesses (DUA - Recrutar Interesse) -->
        <div id="stage-interest" class="card w-full max-w-2xl mx-auto my-auto text-center stage">
            <h1 class="text-4xl font-playful font-bold text-indigo-600 mb-4">Vamos Criar um Poema! 🚀</h1>
            <p class="text-lg text-slate-600 mb-6">Para começar, me conte do que você mais gosta. Pode ser um jogo, um animal, um lugar, ou um sentimento!</p>
            <textarea id="interest-input" class="w-full h-32 p-4 border border-slate-300 rounded-lg text-lg focus:ring-2 focus:ring-indigo-500" placeholder="Ex: Gosto de jogar futebol no parque, do meu cachorro e de olhar as estrelas..."></textarea>
            <button id="btn-get-themes" class="btn-primary mt-6">
                Gerar Ideias de Temas →
            </button>
            <p id="interest-error" class="text-red-500 mt-4 hidden">Por favor, escreva algo para começar!</p>
        </div>

        <!-- ETAPA 2: Escolha do Tema -->
        <div id="stage-theme" class="card w-full max-w-3xl mx-auto my-auto text-center stage hidden">
            <h1 class="text-4xl font-playful font-bold text-indigo-600 mb-4">Ótimas Ideias! ✨</h1>
            <p class="text-lg text-slate-600 mb-8">Pensei nestes temas com base no que você escreveu. Escolha um para começar:</p>
            <div id="theme-buttons" class="grid grid-cols-2 md:grid-cols-3 gap-4">
                <!-- Botões de tema serão inseridos aqui pelo JS -->
            </div>
            <button id="btn-back-interest" class="btn-secondary mt-8">← Voltar</button>
        </div>

        <!-- ETAPA 3: Oficina de Escrita (Layout principal) -->
        <div id="stage-writing" class="flex-1 h-full hidden flex-col md:flex-row gap-6 stage">
            
            <!-- Coluna Principal: Editor e Correções -->
            <main class="flex-[3] flex flex-col gap-6 h-full">
                <header class="card flex-shrink-0">
                    <h1 class="text-3xl font-playful font-bold text-indigo-600">✍️ Oficina de Escrita</h1>
                    <p class="text-lg text-slate-600">Tema: <strong id="chosen-theme-title" class="text-indigo-700"></strong></p>
                </header>
                
                <!-- Editor de Poema -->
                <div class="card flex-1 flex flex-col">
                    <label for="poem-editor" class="text-xl font-bold mb-2 text-slate-700">Escreva seu poema aqui:</label>
                    <textarea id="poem-editor" class="w-full flex-1 p-4 border border-slate-300 rounded-lg text-lg leading-relaxed focus:ring-2 focus:ring-indigo-500" placeholder="O sol se põe no horizonte..."></textarea>
                </div>
                
                <!-- Botões de Ação -->
                <div class="flex-shrink-0 flex flex-col sm:flex-row gap-4">
                    <button id="btn-check-spelling" class="btn-secondary flex-1 py-3">🕵️‍♀️ Revisar Ortografia</button>
                    <button id="btn-finish-poem" class="btn-primary flex-1">Concluir Poema 🏁</button>
                </div>
                
                <!-- Container de Correções (DUA - Feedback Construtivo) -->
                <div id="corrections-container" class="card flex-shrink-0 hidden max-h-[300px] overflow-y-auto">
                    <h3 class="text-xl font-bold mb-4 text-slate-700">Dicas do Assistente</h3>
                    <div id="corrections-list">
                        <!-- Correções serão inseridas aqui -->
                    </div>
                </div>
            </main>

            <!-- Coluna Lateral: Ferramentas de Apoio (DUA - Suporte) -->
            <aside class="flex-[2] flex flex-col gap-6 h-full max-h-full overflow-y-auto">
                <!-- Caça-Rimas (BNCC - EF67LP31) -->
                <div class="card">
                    <h3 class="text-xl font-bold mb-4 text-slate-700">🔎 Caça-Rimas</h3>
                    <div class="flex gap-2">
                        <input type="text" id="rhyme-input" class="w-full p-2 border border-slate-300 rounded-lg" placeholder="Digite uma palavra...">
                        <button id="btn-get-rhymes" class="btn-secondary px-4">Buscar</button>
                    </div>
                    <div id="rhyme-results" class="mt-4 max-h-40 overflow-y-auto text-sm">
                        <p class="text-slate-400 italic">Digite uma palavra e clique em "Buscar" para ver as rimas.</p>
                    </div>
                </div>

                <!-- *** MUDANÇA: Inspiração Criativa (Lista Estática) *** -->
                <div class="card">
                    <h3 class="text-xl font-bold mb-4 text-slate-700">💡 Inspiração Criativa</h3>
                    <div id="inspiration-area" class="space-y-3 overflow-y-auto p-3 bg-slate-50 rounded-lg max-h-48 min-h-[100px]">
                        <p class="text-slate-500 italic text-sm">Carregando ideias para o seu tema...</p>
                    </div>
                </div>
                <!-- *** FIM DA MUDANÇA *** -->
                
                <!-- Estatísticas -->
                <div class="card">
                    <h3 class="text-xl font-bold mb-4 text-slate-700">📊 Estatísticas</h3>
                    <div class="flex justify-around text-center">
                        <div>
                            <div id="stat-verses" class="text-4xl font-bold text-indigo-600">0</div>
                            <div class="text-sm text-slate-500">Versos</div>
                        </div>
                        <div>
                            <div id="stat-stanzas" class="text-4xl font-bold text-indigo-600">0</div>
                            <div class="text-sm text-slate-500">Estrofes</div>
                        </div>
                    </div>
                </div>
                <button id="btn-back-theme" class="btn-secondary w-full mt-auto">← Mudar Tema</button>
            </aside>
        </div>
        
        <!-- ETAPA 4: Finalização e PDF -->
        <div id="stage-pdf" class="card w-full max-w-lg mx-auto my-auto text-center stage hidden">
            <h1 class="text-4xl font-playful font-bold text-indigo-600 mb-4">Seu Poema está Lindo! 🏆</h1>
            <p class="text-lg text-slate-600 mb-6">Vamos dar os toques finais para criar seu PDF personalizado.</p>
            <div class="space-y-4">
                <input type="text" id="pdf-title" class="w-full p-3 border border-slate-300 rounded-lg text-lg" placeholder="Qual o título do poema?">
                <input type="text" id="pdf-author" class="w-full p-3 border border-slate-300 rounded-lg text-lg" placeholder="Qual o nome do(a) poeta? (Seu nome!)">
            </div>
            <p id="pdf-error" class="text-red-500 mt-4 hidden">Por favor, preencha o título e seu nome!</p>
            <button id="btn-generate-pdf" class="btn-primary mt-6">
                Gerar PDF Mágico ✨
            </button>
            <button id="btn-back-writing" class="btn-secondary mt-4">← Voltar para Edição</button>
        </div>
    </div>

    <!-- Overlay de Carregamento Global -->
    <div id="loading-overlay" class="loading-hidden">
        <div class="loader"></div>
    </div>

    <!-- JavaScript da Aplicação -->
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
                    stages[stageId].classList.add('stage'); // Adiciona classe para animação
                    // Garante que o layout flex seja aplicado corretamente
                    if (stageId === 'writing') {
                        stages[stageId].classList.add('flex');
                    } else {
                        stages[stageId].classList.remove('flex');
                    }
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
                    interestError.classList.remove('hidden');
                    return;
                }
                interestError.classList.add('hidden');
                
                const data = await fetchAPI('/api/generate-themes', { interest });
                if (data && data.themes) {
                    const themeButtons = document.getElementById('theme-buttons');
                    themeButtons.innerHTML = ''; // Limpa temas antigos
                    data.themes.forEach(theme => {
                        const button = document.createElement('button');
                        button.textContent = theme;
                        button.className = 'btn-secondary text-base md:text-lg p-4 h-24 truncate';
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
                
                // *** MUDANÇA: Limpa e busca 5 ideias estáticas ***
                const inspirationArea = document.getElementById('inspiration-area');
                inspirationArea.innerHTML = '<p class="text-slate-500 italic text-sm">Buscando ideias para o seu tema...</p>';
                
                showStage('writing');

                // Busca as 5 ideias estáticas APÓS mostrar a tela
                const data = await fetchAPI('/api/get-ideas', { theme });
                if (data && data.ideas) {
                    inspirationArea.innerHTML = ''; // Limpa
                    const list = document.createElement('ul');
                    list.className = 'list-disc list-inside space-y-2 text-slate-700';
                    data.ideas.forEach(idea => {
                        const li = document.createElement('li');
                        li.textContent = idea;
                        list.appendChild(li);
                    });
                    inspirationArea.appendChild(list);
                } else {
                    inspirationArea.innerHTML = '<p class="text-red-500">Não foi possível carregar as ideias.</p>';
                }
                // *** FIM DA MUDANÇA ***
            }

            // --- ETAPA 3: Lógica da Oficina de Escrita ---
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

            // *** REMOVIDO: Event listener do btn-get-feedback (Tutor Interativo) ***

            // Buscar Rimas
            document.getElementById('btn-get-rhymes').addEventListener('click', async () => {
                const word = rhymeInput.value.trim();
                if (!word) return;
                
                rhymeResults.innerHTML = '<p class="text-slate-400 italic">Buscando...</p>';
                const data = await fetchAPI('/api/find-rhymes', { word, theme: appState.chosenTheme });
                
                rhymeResults.innerHTML = ''; // Limpa
                if (data && data.rhymes) {
                    if (data.rhymes[0].palavra === "Erro" || data.rhymes[0].palavra === "Puxa!") {
                        rhymeResults.innerHTML = `<p class="text-slate-500">${data.rhymes[0].definicao}</p>`;
                    } else {
                        const list = document.createElement('ul');
                        list.className = 'space-y-1';
                        data.rhymes.forEach(r => {
                            const li = document.createElement('li');
                            li.innerHTML = `<strong class="text-indigo-600">${r.palavra}:</strong> <span class="text-slate-600">${r.definicao}</span>`;
                            list.appendChild(li);
                        });
                        rhymeResults.appendChild(list);
                    }
                } else {
                    rhymeResults.innerHTML = '<p class="text-red-500">Falha ao buscar rimas.</p>';
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
                    verseDiv.className = 'py-3 border-b border-slate-200 last:border-b-0';
                    verseDiv.innerHTML = `<h4 class="font-bold text-slate-600">No Verso ${verseNum}:</h4>`;
                    
                    errorsByVerse[verseNum].forEach(error => {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'ml-4 mt-2';
                        errorDiv.innerHTML = `<p>Você escreveu <strong class="text-red-600 line-through">${error.original}</strong></p>
                                            <p class="text-sm text-slate-500 italic mb-2">${error.reason}</p>`;
                        
                        const buttonsDiv = document.createElement('div');
                        buttonsDiv.className = 'flex flex-wrap gap-2';
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
                // Lógica de substituição mais segura
                const lines = poemEditor.value.split('\\n');
                const lineIndex = verseNum - 1;

                if (lines[lineIndex]) {
                    // Substitui apenas a primeira ocorrência na linha correta, mantendo o caso
                    const regex = new RegExp(`\\b${original}\\b`, 'i');
                    if (regex.test(lines[lineIndex])) {
                         lines[lineIndex] = lines[lineIndex].replace(regex, suggestion);
                    }
                }
                
                poemEditor.value = lines.join('\\n');
                poemEditor.dispatchEvent(new Event('input')); // Atualiza estatísticas

                // Remove o erro corrigido do estado
                appState.currentErrors = appState.currentErrors.filter(err => 
                    !(err.original === original && err.verse_number == verseNum)
                );
                
                // Re-renderiza a lista de correções
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
                    pdfError.classList.remove('hidden');
                    return;
                }
                pdfError.classList.add('hidden');
                
                const blob = await fetchAPI('/api/generate-pdf', {
                    title,
                    author,
                    text: appState.poemText,
                    theme: appState.chosenTheme
                });

                if (blob) {
                    // Cria um link de download e simula o clique
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

