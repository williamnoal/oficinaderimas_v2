import os
import re
import json
import google.generativeai as genai
from flask import Flask, jsonify, request, Response, render_template_string
from fpdf import FPDF
from datetime import datetime
from math import cos as _cos, sin as _sin
from collections import defaultdict

# --- 1. CONFIGURAÇÃO DO FLASK E API ---

app = Flask(__name__)

# Carrega a Chave da API a partir de variáveis de ambiente
# (Substitui o st.secrets do Streamlit)
API_KEY = os.environ.get('GOOGLE_API_KEY')
if not API_KEY:
    print("ERRO: A variável de ambiente GOOGLE_API_KEY não foi definida.")
    # Em um app real, você poderia lançar um erro aqui
    # raise ValueError("GOOGLE_API_KEY não definida")

genai.configure(api_key=API_KEY)
model = None

def get_ai_model():
    """Configura e retorna o modelo de IA."""
    global model
    if model is None:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            return model
        except Exception as e:
            print(f"Erro ao configurar o modelo Gemini: {e}")
            return None
    return model

# --- 2. LÓGICA DE IA (Adaptada dos seus arquivos) ---

# Prompts aprimorados para melhor feedback pedagógico (DUA/BNCC)

def get_ai_themes(interest_text):
    """Gera temas com base nos interesses do aluno."""
    model = get_ai_model()
    if model is None:
        return ["Erro: Modelo de IA não configurado."]
    
    prompt = f"""
    Aja como um gerador de ideias para um jovem escritor de 11 a 13 anos (6º ano).
    A tarefa é criar 10 temas para um poema baseados nas palavras que o aluno escreveu.
    Palavras de Inspiração do Aluno:
    "{interest_text}"
    Sua Missão:
    Ofereça dez temas para um poema que se relacionem DIRETAMENTE com o que ele colocou. Os temas devem ser concretos, curtos e estimulantes.
    Formato OBRIGATÓRIO da Resposta:
    Retorne APENAS uma lista Python válida contendo 10 strings.
    """
    try:
        response = model.generate_content(prompt)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            list_str = match.group(0)
            themes = eval(list_str)
            if isinstance(themes, list) and len(themes) > 0:
                return themes
        return ["O Assistente não conseguiu criar temas. Tente novamente."]
    except Exception:
        return ["O Assistente teve um problema para criar temas."]

def get_ai_ideas(theme):
    """
    Gera ideias de progressão (DUA/BNCC) focadas em recursos semânticos e sensoriais.
    Alinhado com (EF67LP31) - "utilizando recursos... semânticos e sonoros".
    """
    model = get_ai_model()
    if model is None:
        return ["Erro: Modelo de IA não configurado."]
    
    prompt = f"""
    Aja como um professor de escrita criativa (Ensino Fundamental II), guiando um aluno (11-13 anos) no tema: '{theme}'.
    Sua tarefa é criar 8 ideias de progressão (perguntas ou comandos) que incentivem o uso de recursos da BNCC (EF67LP31).

    **Diretrizes (DUA e BNCC):**
    1.  **Foco nos Sentidos:** Incentive o aluno a pensar em cheiros, sons, cores e sensações.
    2.  **Recursos Semânticos:** Sugira o uso de comparações ("Como se parece com...?") e metáforas simples ("Que cor teria esse sentimento?").
    3.  **Concretude:** Mantenha as ideias fáceis de visualizar.
    4.  **Simplicidade:** Vocabulário acessível, mas inspirador.
    5.  **NÃO ESCREVA VERSOS:** Apenas as ideias/perguntas.

    FORMATO DA RESPOSTA: Retorne APENAS uma lista Python com 8 strings.
    """
    try:
        response = model.generate_content(prompt)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            list_str = match.group(0)
            suggestions = eval(list_str)
            if isinstance(suggestions, list) and len(suggestions) > 0:
                return suggestions
        return ["O Assistente não conseguiu gerar ideias. Tente novamente!"]
    except Exception:
        return ["O Assistente teve um problema para gerar ideias."]

def get_ai_rhymes(word, theme):
    """Busca rimas fonéticas (lógica do seu rhyme_engine.py)."""
    model = get_ai_model()
    if model is None:
        return [{"palavra": "Erro", "definicao": "Erro na configuração da IA."}]

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
    Retorne uma lista de objetos JSON. Cada objeto deve ter "palavra" e "definicao" (curta e simples).
    Retorne no mínimo 8 sugestões, se possível.
    """
    try:
        generation_config = {"temperature": 0.8}
        response = model.generate_content(prompt, generation_config=generation_config)
        json_text = response.text.strip().replace("```json", "").replace("```", "").replace("python", "")
        rhymes = json.loads(json_text)
        rhymes = [r for r in rhymes if r['palavra'].lower() != word.lower()]
        return rhymes if rhymes else [{"palavra": "Puxa!", "definicao": f"Não encontrei rimas para '{word}'."}]
    except Exception:
        return [{"palavra": "Erro", "definicao": "O Assistente teve um problema para buscar rimas."}]

def get_ai_errors(text):
    """Verifica ortografia (lógica do seu spell_checker.py)."""
    model = get_ai_model()
    if model is None:
        return []
    
    lines = text.split('\n')
    numbered_text = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines))

    prompt = f"""
    Aja como um professor de português experiente, revisando um poema de um aluno de 11 anos.
    O aluno pode usar liberdade poética.

    **Texto do poema (para Contexto):**
    ---
    {numbered_text}
    ---

    **Regras de Correção:**
    1.  **Foco:** Apenas ortografia (palavras erradas) e uso de maiúsculas.
    2.  **Contexto é Rei:** As sugestões devem fazer sentido.
    3.  **IGNORE A PONTUAÇÃO:** Poemas têm liberdade poética.
    4.  **MÚLTIPLAS SUGESTÕES:** Ofereça até 3 correções.
    5.  **Comentários Simples:** Forneça um "motivo" (reason) curto.

    **Formato OBRIGATÓRIO da Resposta (JSON):**
    Retorne uma lista de objetos. Cada objeto deve ter:
    - "original": A palavra com problema.
    - "suggestions": UMA LISTA de strings (ex: ["tem", "tenho"]).
    - "reason": Uma única string com o motivo.
    - "verse_number": O número da linha (começando em 1).
    
    Se não houver erros, retorne uma lista vazia [].
    """
    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip().replace("```json", "").replace("```", "").replace("python", "")
        if not json_text or "[]" in json_text:
            return []
        return json.loads(json_text)
    except Exception:
        return []

# --- 3. LÓGICA DE GERAÇÃO DE PDF (Adaptada do seu pdf_generator.py) ---

def generate_pdf_style_ai(theme, poem_text):
    """Gera um estilo de design para o PDF, incluindo um estilo de borda."""
    model = get_ai_model()
    if model is None: 
        return {
            "font": "Helvetica", "bg_color_hex": "#F0F8FF", 
            "text_color_hex": "#2F4F4F", "title_color_hex": "#FF6347",
            "border_style": "simples", "border_color_hex": "#4682B4"
        }

    prompt = f"""
    Aja como um diretor de arte criando um layout para um poema infantil (11 anos).
    O tema é "{theme}".

    Sua tarefa é retornar um objeto JSON com uma paleta de design lúdica e moderna.

    **Chaves obrigatórias no JSON:**
    - "font": Escolha uma entre "Courier", "Helvetica", "Times".
    - "bg_color_hex": Uma cor de fundo suave em hexadecimal (ex: "#F0F8FF").
    - "text_color_hex": Uma cor de texto escura e legível, em hexadecimal.
    - "title_color_hex": Uma cor de destaque para o título, em hexadecimal.
    - "border_style": Escolha UM: "simples", "dupla", "ondas", "estrelas".
    - "border_color_hex": Uma cor para a borda, em hexadecimal.

    Retorne APENAS o objeto JSON.
    """
    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip().replace("```json", "").replace("```", "").replace("python", "")
        return json.loads(json_text)
    except Exception:
        # Estilo padrão em caso de falha
        return {
            "font": "Helvetica", "bg_color_hex": "#F0F8FF", 
            "text_color_hex": "#2F4F4F", "title_color_hex": "#FF6347",
            "border_style": "simples", "border_color_hex": "#4682B4"
        }

class PoemPDF(FPDF):
    def __init__(self, style_guide, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style = style_guide
        # Converte cores hex para RGB
        self.bg_r, self.bg_g, self.bg_b = tuple(int(self.style['bg_color_hex'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.text_r, self.text_g, self.text_b = tuple(int(self.style['text_color_hex'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.title_r, self.title_g, self.title_b = tuple(int(self.style['title_color_hex'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.border_r, self.border_g, self.border_b = tuple(int(self.style.get('border_color_hex', '#4682B4').lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    def header(self):
        self.set_fill_color(self.bg_r, self.bg_g, self.bg_b)
        self.rect(0, 0, self.w, self.h, 'F')
        self.draw_border()

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Gerado pela Oficina de Rimas - {datetime.now().strftime("%d/%m/%Y")}', 0, 0, 'C')

    def draw_border(self):
        """Chama a função de desenho de borda apropriada com base no estilo."""
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
            p.append((x + radius *_cos(angle), y + radius * _sin(angle)))
        self.polygon(p, 'F')

def create_poem_pdf(title, author, poem_text, style_guide):
    """Cria e retorna o PDF como bytes."""
    pdf = PoemPDF(style_guide)
    pdf.add_page()
    
    pdf.set_font(style_guide['font'], 'B', 24)
    pdf.set_text_color(pdf.title_r, pdf.title_g, pdf.title_b)
    pdf.multi_cell(0, 15, title, align='C')
    pdf.ln(20)
    
    pdf.set_font(style_guide['font'], '', 12)
    pdf.set_text_color(pdf.text_r, pdf.text_g, pdf.text_b)
    pdf.multi_cell(0, 10, poem_text)
    pdf.ln(10)
    
    pdf.set_font(style_guide['font'], 'I', 14)
    pdf.multi_cell(0, 10, f'- {author}', align='R')
    
    # Retorna como bytes, pronto para ser enviado pela API
    return pdf.output(dest='S').encode('latin-1')


# --- 4. TEMPLATE DO FRONTEND (HTML/CSS/JS) ---

# Este é o frontend completo embutido em uma string Python.
# Ele usa TailwindCSS para um design moderno e acessível (DUA).
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oficina de Poemas - Python</title>
    <!-- Carrega TailwindCSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Carrega a fonte (Roboto) -->
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Playpen+Sans:wght@400;600&display=swap" rel="stylesheet">
    <style>
        /* Estilos customizados (DUA/Lúdico) */
        body {
            font-family: 'Roboto', sans-serif;
            background-color: #f0f4f8; /* Fundo suave */
            color: #1e293b; /* Texto principal (slate-800) */
        }
        /* Fonte lúdica para títulos */
        .font-playful {
            font-family: 'Playpen Sans', cursive;
        }
        /* Botão principal */
        .btn-primary {
            @apply bg-indigo-600 text-white font-bold py-3 px-6 rounded-full shadow-lg transition-transform transform hover:scale-105 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-50;
        }
        /* Botão secundário */
        .btn-secondary {
            @apply bg-slate-200 text-slate-700 font-semibold py-2 px-4 rounded-full shadow-sm transition-colors hover:bg-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-400;
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
        
        /* Spinner de carregamento */
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
        /* Overlay de carregamento */
        #loading-overlay {
            @apply fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 hidden;
        }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen p-4">

    <!-- Container principal da aplicação (sem rolagem no body) -->
    <div class="w-full max-w-7xl mx-auto h-[95vh] flex flex-col">
    
        <!-- ETAPA 1: Interesses (DUA - Recrutar Interesse) -->
        <div id="stage-interest" class="card w-full max-w-2xl mx-auto my-auto text-center animate-fade-in">
            <h1 class="text-4xl font-playful font-bold text-indigo-600 mb-4">Vamos Criar um Poema! 🚀</h1>
            <p class="text-lg text-slate-600 mb-6">Para começar, me conte do que você mais gosta. Pode ser um jogo, um animal, um lugar, ou um sentimento!</p>
            <textarea id="interest-input" class="w-full h-32 p-4 border border-slate-300 rounded-lg text-lg focus:ring-2 focus:ring-indigo-500" placeholder="Ex: Gosto de jogar futebol no parque, do meu cachorro e de olhar as estrelas..."></textarea>
            <button id="btn-get-themes" class="btn-primary mt-6">
                Gerar Ideias de Temas →
            </button>
            <p id="interest-error" class="text-red-500 mt-4 hidden">Por favor, escreva algo para começar!</p>
        </div>

        <!-- ETAPA 2: Escolha do Tema -->
        <div id="stage-theme" class="card w-full max-w-3xl mx-auto my-auto text-center hidden">
            <h1 class="text-4xl font-playful font-bold text-indigo-600 mb-4">Ótimas Ideias! ✨</h1>
            <p class="text-lg text-slate-600 mb-8">Pensei nestes temas com base no que você escreveu. Escolha um para começar:</p>
            <div id="theme-buttons" class="grid grid-cols-2 md:grid-cols-3 gap-4">
                <!-- Botões de tema serão inseridos aqui pelo JS -->
            </div>
            <button id="btn-back-interest" class="btn-secondary mt-8">← Voltar</button>
        </div>

        <!-- ETAPA 3: Oficina de Escrita (Layout principal) -->
        <div id="stage-writing" class="flex-1 h-full hidden flex-col md:flex-row gap-6">
            
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
                
                <!-- Container de Correções (DUA - Feedback) -->
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
                        <!-- Rimas serão inseridas aqui -->
                    </div>
                </div>

                <!-- Inspiração (DUA - Guiar) -->
                <div class="card">
                    <h3 class="text-xl font-bold mb-4 text-slate-700">💡 Inspiração Criativa</h3>
                    <ul id="ideas-list" class="list-disc list-inside space-y-2 text-slate-600 max-h-48 overflow-y-auto">
                        <!-- Ideias de progressão serão inseridas aqui -->
                    </ul>
                </div>
                
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
        <div id="stage-pdf" class="card w-full max-w-lg mx-auto my-auto text-center hidden">
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
    <div id="loading-overlay">
        <div class="loader"></div>
    </div>

    <!-- JavaScript da Aplicação -->
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            // --- Variáveis de Estado e Elementos ---
            let appState = {
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

            // --- Funções de Navegação e UI ---
            function showStage(stageId) {
                Object.values(stages).forEach(stage => stage.classList.add('hidden'));
                if (stages[stageId]) {
                    stages[stageId].classList.remove('hidden');
                    // Garante que o layout flex seja aplicado corretamente
                    if (stageId === 'writing') {
                        stages[stageId].classList.add('flex');
                    } else {
                        stages[stageId].classList.remove('flex');
                    }
                }
            }

            function showLoading(show) {
                loadingOverlay.classList.toggle('hidden', !show);
            }

            // --- Função de API Helper ---
            async function fetchAPI(endpoint, body) {
                showLoading(true);
                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    if (!response.ok) {
                        throw new Error(`Erro na API: ${response.statusText}`);
                    }
                    // Verifica se a resposta é JSON ou um arquivo (PDF)
                    const contentType = response.headers.get("content-type");
                    if (contentType && contentType.includes("application/pdf")) {
                        return await response.blob();
                    }
                    return await response.json();
                } catch (error) {
                    console.error('Erro no fetchAPI:', error);
                    alert(`Ocorreu um erro ao conectar com o assistente: ${error.message}`);
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
                
                const data = await fetchAPI('/api/themes', { interest });
                if (data && data.themes) {
                    const themeButtons = document.getElementById('theme-buttons');
                    themeButtons.innerHTML = ''; // Limpa temas antigos
                    data.themes.forEach(theme => {
                        const button = document.createElement('button');
                        button.textContent = theme;
                        button.className = 'btn-secondary text-base md:text-lg p-4 h-24';
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
                
                const data = await fetchAPI('/api/ideas', { theme });
                if (data && data.ideas) {
                    const ideasList = document.getElementById('ideas-list');
                    ideasList.innerHTML = ''; // Limpa ideias antigas
                    data.ideas.forEach(idea => {
                        const li = document.createElement('li');
                        li.textContent = idea;
                        ideasList.appendChild(li);
                    });
                }
                showStage('writing');
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

            // Buscar Rimas
            document.getElementById('btn-get-rhymes').addEventListener('click', async () => {
                const word = rhymeInput.value.trim();
                if (!word) return;
                
                const data = await fetchAPI('/api/rhymes', { word, theme: appState.chosenTheme });
                if (data && data.rhymes) {
                    rhymeResults.innerHTML = '';
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
                }
            });

            // Revisar Ortografia
            document.getElementById('btn-check-spelling').addEventListener('click', async () => {
                if (!appState.poemText) return;
                
                const data = await fetchAPI('/api/check', { text: appState.poemText });
                if (data) {
                    appState.currentErrors = data.errors || [];
                    renderCorrections();
                }
            });
            
            function renderCorrections() {
                correctionsList.innerHTML = '';
                if (appState.currentErrors.length === 0) {
                    correctionsContainer.classList.add('hidden');
                    alert("Nenhum problema de ortografia encontrado! 🎉");
                    return;
                }
                
                const errorsByVerse = {};
                appState.currentErrors.forEach(err => {
                    if (!errorsByVerse[err.verse_number]) {
                        errorsByVerse[err.verse_number] = [];
                    }
                    errorsByVerse[err.verse_number].push(err);
                });

                Object.keys(errorsByVerse).sort((a,b) => a-b).forEach(verseNum => {
                    const verseDiv = document.createElement('div');
                    verseDiv.className = 'py-3 border-b border-slate-200 last:border-b-0';
                    verseDiv.innerHTML = `<h4 class="font-bold text-slate-600">No Verso ${verseNum}:</h4>`;
                    
                    errorsByVerse[verseNum].forEach(error => {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'ml-4 mt-2';
                        errorDiv.innerHTML = `<p>Problema: <strong class="text-red-600">${error.original}</strong></p>
                                            <p class="text-sm text-slate-500 italic mb-2">${error.reason}</p>`;
                        
                        const buttonsDiv = document.createElement('div');
                        buttonsDiv.className = 'flex flex-wrap gap-2';
                        error.suggestions.forEach(suggestion => {
                            const button = document.createElement('button');
                            button.textContent = suggestion;
                            button.className = 'btn-secondary text-sm';
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
                    // Substitui apenas a primeira ocorrência na linha correta
                    const regex = new RegExp(`\\b${original}\\b`, 'i');
                    if (regex.test(lines[lineIndex])) {
                         lines[lineIndex] = lines[lineIndex].replace(regex, suggestion);
                    }
                }
                
                poemEditor.value = lines.join('\\n');
                poemEditor.dispatchEvent(new Event('input')); // Atualiza estatísticas

                // Re-valida
                document.getElementById('btn-check-spelling').click();
            }

            // Concluir Poema
            document.getElementById('btn-finish-poem').addEventListener('click', () => {
                if (appState.poemText.trim().length < 10) {
                    alert("Seu poema parece um pouco curto. Escreva mais um pouco!");
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
                
                const blob = await fetchAPI('/api/pdf', {
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
                    // Limpa o nome do arquivo
                    const safeFilename = title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
                    a.download = `${safeFilename || 'meu_poema'}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                }
            });

            // --- Inicialização ---
            showStage('interest');
            // showStage('writing'); // Para debug
            // appState.chosenTheme = "Teste";
            // document.getElementById('chosen-theme-title').textContent = "Teste";
        });
    </script>
</body>
</html>
"""

# --- 5. DEFINIÇÃO DAS ROTAS DO FLASK ---

@app.route('/')
def home():
    """Serve o frontend principal."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/themes', methods=['POST'])
def api_themes():
    """Endpoint da API para gerar temas."""
    data = request.json
    if 'interest' not in data:
        return jsonify({"error": "Interesse não fornecido"}), 400
    
    themes = get_ai_themes(data['interest'])
    return jsonify({"themes": themes})

@app.route('/api/ideas', methods=['POST'])
def api_ideas():
    """Endpoint da API para gerar ideias de progressão."""
    data = request.json
    if 'theme' not in data:
        return jsonify({"error": "Tema não fornecido"}), 400
    
    ideas = get_ai_ideas(data['theme'])
    return jsonify({"ideas": ideas})

@app.route('/api/rhymes', methods=['POST'])
def api_rhymes():
    """Endpoint da API para buscar rimas."""
    data = request.json
    if 'word' not in data or 'theme' not in data:
        return jsonify({"error": "Dados incompletos"}), 400
    
    rhymes = get_ai_rhymes(data['word'], data['theme'])
    return jsonify({"rhymes": rhymes})

@app.route('/api/check', methods=['POST'])
def api_check():
    """Endpoint da API para verificar ortografia."""
    data = request.json
    if 'text' not in data:
        return jsonify({"error": "Texto não fornecido"}), 400
    
    errors = get_ai_errors(data['text'])
    return jsonify({"errors": errors})

@app.route('/api/pdf', methods=['POST'])
def api_pdf():
    """Endpoint da API para gerar e retornar o PDF."""
    data = request.json
    required_fields = ['title', 'author', 'text', 'theme']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Dados incompletos para PDF"}), 400

    try:
        # 1. Pede à IA um estilo
        style = generate_pdf_style_ai(data['theme'], data['text'])
        if not style:
            raise Exception("Falha ao gerar estilo de IA")

        # 2. Gera o PDF em memória
        pdf_bytes = create_poem_pdf(
            data['title'], 
            data['author'], 
            data['text'], 
            style
        )
        
        # 3. Retorna o PDF como um arquivo para download
        safe_filename = re.sub(r'[^a-z0-9]', '_', data['title'].lower(), re.IGNORECASE) or 'poema'
        
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-disposition": f"attachment; filename={safe_filename}.pdf"}
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return jsonify({"error": f"Erro interno ao gerar PDF: {e}"}), 500

# --- 6. INICIALIZAÇÃO DA APLICAÇÃO ---

if __name__ == '__main__':
    if not API_KEY:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!! AVISO: A GOOGLE_API_KEY não está configurada.         !!")
        print("!! Defina-a como uma variável de ambiente para a IA     !!")
        print("!! funcionar. (ex: export GOOGLE_API_KEY='sua_chave')   !!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    
    # Busca a porta na variável de ambiente (comum em produção) ou usa 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
