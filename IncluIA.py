import streamlit as st
import os
import io
import tempfile
import textstat
from textstat import flesch_reading_ease, flesch_kincaid_grade, smog_index
import google.generativeai as genai
import auth_utils
import subprocess

# --- Configurações Iniciais da Página ---
st.set_page_config(
    page_title="IncluIA - Adaptação",
    page_icon="🧩",
    initial_sidebar_state="expanded"
)

# Linguagem das métricas de NLP
#textstat.set_lang("pt")

# --- CSS CUSTOMIZADO PARA MODO CLARO E ESCURO ---
st.markdown("""
    <style>
    textarea[disabled] {
        -webkit-text-fill-color: #2e3136;
        color: #2e3136;
        background-color: #f0f2f6;
    }

    body[data-theme="dark"] textarea[disabled] {
        -webkit-text-fill-color: #fafafa;
        color: #fafafa;
        background-color: #1c1f2b;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BLOCO DE AUTENTICAÇÃO ---
auth_successful = auth_utils.authenticate_user()
if not auth_successful:
    st.stop()

# --- INICIALIZAÇÃO DO SESSION STATE ---
if "instrucoes_adicionais" not in st.session_state:
    st.session_state.instrucoes_adicionais = ""
if "output_adaptado" not in st.session_state:
    st.session_state.output_adaptado = ""
if "output_justificativas" not in st.session_state:
    st.session_state.output_justificativas = ""

# --- Funções de Conversão dos Documentos ---

def convert_pdf_bytes_to_image_bytes(pdf_bytes, dpi=300):
    """Converte bytes de um PDF para uma lista de bytes de imagens (uma por página) usando a biblioteca Fitz."""
    try:
        import fitz
        from PIL import Image
    except ImportError:
        st.error("Bibliotecas 'Fitz' ou 'PIL' não encontradas. Não foi possível ler o documento.")
        return []

    image_bytes_list = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            byte_arr = io.BytesIO()
            img_pil.save(byte_arr, format='JPEG', quality=95)
            image_bytes_list.append(byte_arr.getvalue())
        
        doc.close()
        return image_bytes_list
    
    except Exception as e:
        st.error(f"Erro na conversão do documento. Não foi possível ler o documento: {e}")
        return []

# --- Trecho Corrigido (usando LibreOffice) ---

def convert_docx_bytes_to_image_bytes(docx_bytes, dpi=300):
    """Converte bytes de um DOCX para uma lista de bytes de imagens, usando LibreOffice e Fitz."""
    # A biblioteca docx2pdf foi removida pois não funciona em Linux sem MS Word.
    
    tmp_docx_path = None
    tmp_pdf_path = None
    
    try:
        # 1. Salva o DOCX enviado em um arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
            tmp_docx.write(docx_bytes)
            tmp_docx_path = tmp_docx.name

        # 2. Define o diretório de saída e o nome do arquivo PDF esperado
        output_dir = os.path.dirname(tmp_docx_path)
        tmp_pdf_path = os.path.splitext(tmp_docx_path)[0] + ".pdf"
        
        # 3. Executa o comando do LibreOffice para converter o DOCX em PDF
        command = f"libreoffice --headless --convert-to pdf --outdir {output_dir} {tmp_docx_path}"
        
        process = subprocess.run(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=60 # Adiciona um timeout de 60 segundos para evitar que o processo trave
        )

        # 4. Verifica se a conversão foi bem-sucedida e se o PDF foi criado
        if process.returncode != 0:
            # Se o comando falhou, mostra o erro do LibreOffice
            st.error(f"Erro na conversão com LibreOffice. Detalhes:")
            st.code(process.stderr.decode('utf-8', 'ignore'))
            return []

        if not os.path.exists(tmp_pdf_path):
            st.error("Erro na conversão: o arquivo PDF não foi encontrado após a execução do LibreOffice.")
            return []

        # 5. Lê os bytes do PDF recém-criado
        with open(tmp_pdf_path, "rb") as f_pdf:
            pdf_bytes_from_docx = f_pdf.read()
        
        # 6. Chama a sua outra função para converter os bytes do PDF em imagens
        image_bytes_list = convert_pdf_bytes_to_image_bytes(pdf_bytes_from_docx, dpi=dpi)
        return image_bytes_list
        
    except subprocess.TimeoutExpired:
        st.error("Erro: A conversão do documento demorou muito e foi interrompida.")
        return []
    except Exception as e:
        st.error(f"Erro no processo de conversão do documento: {e}")
        return []
    finally:
        # 7. Limpa os arquivos temporários criados (DOCX e PDF)
        if tmp_docx_path and os.path.exists(tmp_docx_path):
            os.remove(tmp_docx_path)
        if tmp_pdf_path and os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)

# --- Funções Auxiliares ---

def adicionar_sugestao(sugestao):
    texto_atual = st.session_state["instrucoes_adicionais"]
    if texto_atual:
        st.session_state["instrucoes_adicionais"] = texto_atual + ", " + sugestao
    else:
        st.session_state["instrucoes_adicionais"] = sugestao

def metricas_NLP(texto):
    if not texto or not texto.strip():
        return "Texto inválido para análise de legibilidade."

    palavras = texto.split()
    if not palavras or len(palavras) < 20:
        return "Texto muito curto para análise de legibilidade (mínimo 20 palavras)."

    # Cálculo de variedade lexical:
    variedade_lexical_calc = lambda t: (
        len(set(t.split())) / len(t.split())
        if t.strip() and len(t.split()) > 0 else 0
    )

    facilidade_leitura = round(flesch_reading_ease(texto), 2)
    serie_aprox = round(flesch_kincaid_grade(texto), 2)
    nivel_escolar = round(smog_index(texto), 2)
    variedade_lexical = round(variedade_lexical_calc(texto), 2)


    # Interpretação de Facilidade de Leitura (Flesch Reading-Ease):
    if facilidade_leitura >= 90:
        fl_desc = "Muito fácil 🟢"
    elif 70 <= facilidade_leitura < 90:
        fl_desc = "Fácil 🟢"
    elif 50 <= facilidade_leitura < 70:
        fl_desc = "Médio 🟡"
    else:
        fl_desc = "Difícil 🔴"

    # Interpretação de Série Aproximada (Flesch-Kincaid Grade Level)
    if serie_aprox < 6:
        sa_desc = "Fundamental I 🟢"
    elif serie_aprox < 9:
        sa_desc = "Fundamental II 🟢"
    elif serie_aprox <= 12:
        sa_desc = "Ensino Médio 🟡"
    else:
        sa_desc = "Ensino Superior 🔴"

    # Interpretação de Nível Escolar (SMOG Index)
    if nivel_escolar < 9:
        ne_desc = "Fundamental 🟢"
    elif nivel_escolar <= 12:
        ne_desc = "Ensino Médio 🟡"
    else:
        ne_desc = "Ensino Superior 🔴"

    # Interpretação Variedade Lexical
    if variedade_lexical > 0.7:
        vl_desc = "Alta 🟡"
    elif 0.5 <= variedade_lexical <= 0.7:
        vl_desc = "Média 🟢"
    else:
        vl_desc = "Baixa 🟢"


    return {
        "facilidade_leitura_val": facilidade_leitura,
        "facilidade_leitura_desc": fl_desc,
        "serie_aprox_val": serie_aprox,
        "serie_aprox_desc": sa_desc,
        "nivel_escolar_val": nivel_escolar,
        "nivel_escolar_desc": ne_desc,
        "variedade_lexical_val": variedade_lexical,
        "variedade_lexical_desc": vl_desc,
    }

# Modelo de IA generativa
modelo_txt = "gemini-2.5-flash"

# --- UI ---

st.title('🧩 IncluIA')
st.subheader('Uma ferramenta educacional para adaptar avaliações para estudantes com NEEs, utilizando IA generativa.')


# --- Barra Lateral com Explicação das Métricas de NLP ---
with st.sidebar:
    st.header("Entenda a Legibilidade do Texto")
    st.write("Veja como as métricas de legibilidade avaliam o texto:")

    st.subheader("Facilidade de Leitura (Flesch Reading-Ease)")
    st.write(
        "Indica o quão **fácil é ler** o texto. Quanto maior a nota, mais fácil a leitura."
    )
    st.markdown("""
        | Pontuação | Nível de Facilidade |
        | :-------- | :------------------ |
        | 90–100    | Muito Fácil (crianças pequenas) |
        | 70–89     | Fácil (Ensino Fundamental) |
        | 50–69     | Médio (Ensino Médio) |
        | < 50      | Difícil (acima do Ensino Médio) |
    """)

    st.subheader("Série Aproximada (Flesch-Kincaid Grade Level)")
    st.write(
        "Estima a **série escolar** necessária para compreender o texto. "
        "Um valor de 8, por exemplo, sugere que o texto é adequado para alguém na 8ª série."
    )
    st.markdown("""
        | Pontuação | Nível Escolar Sugerido |
        | :-------- | :--------------------- |
        | 0–5       | Fundamental I          |
        | 6–8       | Fundamental II         |
        | 9–12      | Ensino Médio           |
        | > 12      | Nível Universitário    |
    """)

    st.subheader("Nível Escolar (SMOG Index)")
    st.write(
        "Outra estimativa do **nível escolar** de entendimento. "
        "Foca em palavras com 3 ou mais sílabas. Quanto mais 'palavras difíceis', maior o nível escolar exigido."
    )
    st.markdown("""
        | Pontuação | Nível Escolar Sugerido |
        | :-------- | :--------------------- |
        | 0–8       | Fundamental I e II     |
        | 9–12      | Ensino Médio           |
        | > 12      | Nível Universitário    |
    """)

    st.subheader("Variedade Lexical")
    st.write(
        "Indica a **diversidade de palavras** usadas no texto. "
        "Um valor alto significa que muitas palavras diferentes foram usadas, enquanto um valor baixo sugere repetição."
    )
    st.markdown("""
        | Pontuação | Variedade |
        | :-------- | :-------- |
        | > 0.7     | Alta      |
        | 0.5–0.7   | Média     |
        | < 0.5     | Baixa     |
    """)
    st.markdown("---")
    st.info("Essas métricas são guias para ajudar a tornar o conteúdo mais acessível! A adaptação da **IncluIA** busca atingir esses níveis.")


# --- Entrada do Usuário ---

campo_input = st.text_area(label='Insira ou descreva as questões aqui:', height=200, key="campo_input")

if isinstance(st.session_state.campo_input, str) and len(st.session_state.campo_input.split()) >= 20:
    metric_results = metricas_NLP(st.session_state.campo_input)
    if isinstance(metric_results, dict):
        col_m1, col_m2, col_m3 = st.columns([1, 0.05, 1])
        with col_m1:
            st.markdown(f"**Facilidade de Leitura (Flesch):** {metric_results['facilidade_leitura_val']} ({metric_results['facilidade_leitura_desc']})")
            st.markdown(f"**Série Aprox. (Flesch-Kincaid):** {metric_results['serie_aprox_val']} ({metric_results['serie_aprox_desc']})")
        with col_m3:
            st.markdown(f"**Nível Escolar (SMOG):** {metric_results['nivel_escolar_val']} ({metric_results['nivel_escolar_desc']})")
            st.markdown(f"**Variedade Lexical:** {metric_results['variedade_lexical_val']} ({metric_results['variedade_lexical_desc']})")
    else:
        st.info(metric_results)
else:
    st.warning("Texto original muito curto para análise de legibilidade (mínimo 20 palavras).")


# Campo de upload de arquivo:
campo_upload = st.file_uploader(label='Ou faça upload da avaliação (PDF ou Word)', type=['pdf', 'docx'], key="campo_upload")

# Lista de NEEs (Necessidades Educativas Especiais)
adversidades = [
    'Não especificado',
    'Transtorno do Espectro Autista (TEA)',
    'Transtorno do Déficit de Atenção com Hiperatividade (TDAH)',
    'Deficiência Intelectual',
    'Deficiência Visual',
    'Deficiência Auditiva',
    'Dislexia',
    'Discalculia',
    'Altas Habilidades/Superdotação'
]

selectbox_adv = st.selectbox(label='Insira a adversidade do aluno:', placeholder='Escolha uma opção', options=adversidades, key="selectbox_adv")

# Instruções Adicionais:
sugestoes = [
    "Usar exemplos do cotidiano",
    "Aluno não alfabetizado",
    "Não simplificar muito",
    "Simplificar texto de apoio",
    "Incluir dicas"
]

st.text_input('Instruções adicionais:', key="instrucoes_adicionais")

cols = st.columns(len(sugestoes))

for col, sugestao in zip(cols, sugestoes):
    col.button(sugestao, on_click=adicionar_sugestao, args=(sugestao,))


st.markdown('---')

# --- Instrução de Sistema para a IA ---

system_instruction_text = """
Você é IncluIA, um especialista em Design Universal para Aprendizagem (DUA) e na adaptação de materiais didáticos e avaliativos para alunos com Necessidades Educativas Especiais (NEEs). Sua missão é tornar o conteúdo educacional acessível e justo, removendo barreiras de aprendizagem que não estejam relacionadas ao conhecimento ou habilidade central que se deseja avaliar.

**REGRAS DE IDIOMA (MUITO IMPORTANTE):**

1.  **Idioma Padrão:** O idioma da questão adaptada DEVE ser o mesmo idioma da questão original. Se a questão original está em português, a adaptação DEVE ser em português.
2.  **Exceção para Língua Estrangeira:** Se a disciplina for de língua estrangeira (inglês, espanhol, etc.), a questão adaptada DEVE permanecer no idioma estrangeiro. O objetivo é avaliar o conhecimento nesse idioma. Para facilitar a compreensão, você pode:
    *   Escrever o enunciado da questão em português e manter as alternativas/respostas no idioma estrangeiro.
    *   Usar português e a língua estrangeira juntos no enunciado para esclarecer comandos complexos.
    *   NUNCA traduza o conteúdo principal (textos, alternativas) que avalia a proficiência no idioma para o português.

**PROCESSO DE ADAPTAÇÃO:**

Ao receber uma questão e a especificação de uma NEE, siga rigorosamente estes passos:

1.  **Análise do Objetivo:** Primeiro, identifique qual é o objetivo de aprendizagem central da questão original. O que o aluno precisa saber ou fazer para respondê-la corretamente?
2.  **Identificação de Barreiras:** Analise como a formatação, a linguagem ou a estrutura da questão original podem criar barreiras para um aluno com a NEE especificada, considerando também as `instrucoes_adicionais`.
3.  **Aplicação da Adaptação:** Modifique a questão para remover as barreiras identificadas. Suas estratégias podem incluir, mas não se limitam a:
    *   Simplificar a linguagem e o vocabulário.
    *   Tornar os enunciados mais diretos e claros.
    *   Dividir tarefas complexas em etapas menores e numeradas.
    *   Mudar o formato da questão (ex: de múltipla escolha para completar lacunas).
    *   Sugerir o uso de recursos de apoio (ex: banco de palavras, imagens, calculadora).
4.  **Consideração das Instruções Adicionais:** As `instrucoes_adicionais` sobre o aluno são cruciais e devem sempre ser consideradas para personalizar a adaptação.

**REGRA DE ADAPTAÇÃO DE TEXTO-BASE:**

Por padrão, textos-base (enunciados longos, artigos, contos, etc.) que servem de apoio para as questões devem ser mantidos em sua forma original.
**EXCEÇÃO:** Você SÓ DEVE adaptar o texto-base se as `instrucoes_adicionais` contiverem uma diretriz explícita para isso, como "Adaptar enunciado/texto" ou "Simplificar texto de apoio".
Se a adaptação do texto for solicitada, você deve reescrevê-lo usando estratégias como: simplificação de vocabulário, divisão de frases complexas, uso de listas para organizar informações e, se necessário, adição de um pequeno glossário para termos-chave. O texto-base adaptado deve ser apresentado no início da sua resposta, antes das questões adaptadas.

**REGRA DE SUBSTITUIÇÃO DE QUESTÃO:**

Se a questão original for complexa a ponto de a adaptação descaracterizar completamente seu objetivo pedagógico, você DEVE criar uma NOVA questão. A nova questão precisa:
a. Avaliar o mesmo conceito da original ou um pré-requisito essencial para ele.
b. Ser totalmente acessível para a NEE e as `instrucoes_adicionais`.
c. Na sua justificativa, explique por que a substituição foi necessária e como a nova questão se conecta ao tema.

**PRINCÍPIOS ORIENTADORES:**
*   **Foco na Acessibilidade:** O objetivo é remover barreiras, não diminuir o rigor do conteúdo dentro das possibilidades do aluno.
*   **Justiça Avaliativa:** A adaptação deve garantir que a avaliação seja justa e meça o conhecimento do aluno sobre o tema, e não sua dificuldade com o formato da prova.

**FORMATO DA RESPOSTA FINAL (OBRIGATÓRIO):**

Sua resposta final deve seguir esta estrutura exata, sem exceções:

1.  Se aplicável, o texto-base adaptado primeiro.
2.  Todas as questões adaptadas (ou as novas questões), numeradas. Nunca indique qual a resposta correta na avaliação adaptada.
3.  Em uma nova linha, insira o marcador `# Justificativas:` (exatamente assim).
4.  Abaixo do marcador, liste suas justificativas detalhadas para cada adaptação ou substituição.
5.  Se você criou uma nova questão, informe o gabarito dela na justificativa correspondente.
6.  NÃO utilize formatações em markdown como negrito, itálico ou listas com marcadores (como '*' ou '-'). Use apenas texto puro e numeração simples.
"""

# --- Prompts Específicos para cada NEE ---
# Estes prompts serão combinados com o texto do arquivo/campo_input antes de enviar para a IA.

prompt_base_template = """
Adapte a seguinte questão/avaliação para um aluno com {nee_type}.
{nee_guidelines}

Instruções Adicionais Específicas para este aluno com {nee_type_short}: "{instrucoes_adicionais_val}"

Sua Adaptação:
"""

# Dicionário para mapear adversidades a guidelines e short_names
nee_details = {
    'Não especificado': {
        'guidelines': "Aplicando princípios de Design Universal para Aprendizagem. Foque em clareza, objetividade, e remoção de barreiras comuns.",
        'short_name': "Necessidades Educativas Especiais não especificadas"
    },
    'Transtorno do Espectro Autista (TEA)': {
        'guidelines': """Priorize:
- Linguagem literal, direta e objetiva. Evite ambiguidades, ironias ou linguagem figurada.
- Instruções curtas, claras e sequenciais (passo a passo, se aplicável).
- Redução de estímulos visuais excessivos ou distratores no texto.
- Enunciados concisos.
- Se houver elementos sociais implícitos, torne-os explícitos ou reformule.""",
        'short_name': "TEA"
    },
    'Transtorno do Déficit de Atenção com Hiperatividade (TDAH)': {
        'guidelines': """Priorize:
- Instruções curtas, claras e diretas.
- Destaque (ex: negrito, ou menção explícita) para palavras-chave ou comandos importantes.
- Divisão de tarefas longas em partes menores e mais gerenciáveis.
- Redução de distratores textuais.
- Formato que facilite o foco (ex: uma questão por vez, se for uma lista).""",
        'short_name': "TDAH"
    },
    'Deficiência Intelectual': {
        'guidelines': """Priorize:
- Linguagem extremamente simples, concreta e objetiva.
- Uso de vocabulário familiar e frases curtas.
- Instruções passo a passo, com exemplos concretos se possível.
- Redução do número de elementos ou informações a serem processadas simultaneamente.
- Foco nos conceitos e habilidades mais essenciais.
- Se for múltipla escolha, reduza o número de alternativas e torne-as bem distintas.""",
        'short_name': "DI"
    },
    'Deficiência Visual': {
        'guidelines': """Priorize (considerando leitura via software leitor de tela ou transcrição para Braille):
- Descrição textual detalhada de quaisquer imagens, gráficos ou tabelas essenciais para a compreensão.
- Clareza na estrutura do texto para navegação sequencial.
- Evitar informações que dependam exclusivamente de formatação visual (cores, layout complexo) sem alternativa textual.
- Enunciados claros e diretos.""",
        'short_name': "DV"
    },
    'Deficiência Auditiva': {
        'guidelines': """Priorize (que pode ter Português como L2):
- Linguagem clara, objetiva e direta, evitando estruturas frasais muito complexas, voz passiva excessiva ou inversões sintáticas desnecessárias.
- Vocabulário acessível e preciso. Evite gírias ou expressões idiomáticas complexas.
- Uso de recursos visuais textuais (ex: tópicos, listas) para organizar informações.
- Frases mais curtas e com ordem direta (Sujeito-Verbo-Objeto), se possível.""",
        'short_name': "DA"
    },
    'Dislexia': {
        'guidelines': """Priorize:
- Linguagem clara, objetiva e frases curtas.
- Evitar blocos de texto muito densos; use parágrafos mais curtos e espaçamento.
- Destaque para palavras-chave (ex: negrito, ou menção explícita).
- Instruções segmentadas.
- Evitar fontes ou formatações que dificultem a leitura (embora você não controle a fonte final, a estrutura do texto pode ajudar).
- Se possível, transformar questões dissertativas longas em itens menores ou formatos alternativos (completar, associar, múltipla escolha clara).""",
        'short_name': "Dislexia"
    },
    'Discalculia': {
        'guidelines': """Priorize (especialmente se envolver matemática):
- Clareza extrema nos enunciados de problemas matemáticos; decomponha-os em etapas lógicas.
- Redução de informações numéricas irrelevantes.
- Uso de linguagem simples e direta para descrever operações ou conceitos matemáticos.
- Espaço visualmente organizado para cálculos (se for o caso de descrever um layout).
- Sugestão de uso de recursos de apoio (tabuada, calculadora – se o objetivo não for avaliar o cálculo mental em si).
- Foco no raciocínio matemático em detrimento de pura memorização de fatos numéricos, quando aplicável.""",
        'short_name': "Discalculia"
    },
    'Altas Habilidades/Superdotação': {
        'guidelines': """Priorize (visando maior desafio, profundidade e engajamento):
- Aumento da complexidade conceitual ou do nível de abstração.
- Questões que exijam pensamento crítico, criatividade, análise e síntese.
- Transformação de questões fechadas em abertas, permitindo múltiplas soluções ou aprofundamento.
- Propostas de investigação, conexão com outros temas ou aplicação do conhecimento em novos contextos.
- Se a questão original for muito básica, sugira uma extensão ou um desafio complementar.""",
        'short_name': "AH/SD"
    }
}


# --- Botão de Geração ---

col1_btn, col2_btn, col3_btn = st.columns([1, 1, 1])
with col2_btn:
    btn_adaptar = st.button(label='GERAR ADAPTAÇÃO')

# --- Lógica de Geração da IA e Exibição ---

if btn_adaptar:
    user_content_parts = []
    has_text_input = bool(st.session_state.campo_input and st.session_state.campo_input.strip())

    # 1. Processar arquivo carregado
    if st.session_state.campo_upload is not None:
        file_bytes = st.session_state.campo_upload.read()
        converted_image_bytes_list = []

        with st.spinner(f"Processando arquivo {st.session_state.campo_upload.name}..."):
            if st.session_state.campo_upload.type == "application/pdf":
                converted_image_bytes_list = convert_pdf_bytes_to_image_bytes(file_bytes)
            elif st.session_state.campo_upload.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document": # DOCX
                converted_image_bytes_list = convert_docx_bytes_to_image_bytes(file_bytes)
            else:
                st.error("Tipo de arquivo não suportado. Por favor, envie um PDF ou DOCX.")

        if converted_image_bytes_list:
            for img_bytes in converted_image_bytes_list:
                user_content_parts.append({'mime_type': 'image/jpeg', 'data': img_bytes})
        elif st.session_state.campo_upload.type in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"] and not converted_image_bytes_list:
            st.warning("Não foi possível extrair conteúdo visual do arquivo.")

    # 2. Adicionar texto do campo_input se houver
    if has_text_input:
        user_content_parts.append(st.session_state.campo_input)

    # 3. Verificar se há conteúdo para enviar
    if not user_content_parts:
        st.warning('Insira um texto no campo ou faça upload de um arquivo para realizar a adaptação!')
    else:
        instrucoes_adicionais_valor = st.session_state.get("instrucoes_adicionais", "")
        selected_nee_info = nee_details.get(st.session_state.selectbox_adv, nee_details['Não especificado'])

        user_prompt_text_string = prompt_base_template.format(
            nee_type=st.session_state.selectbox_adv,
            nee_guidelines=selected_nee_info['guidelines'],
            nee_type_short=selected_nee_info['short_name'],
            instrucoes_adicionais_val=instrucoes_adicionais_valor if instrucoes_adicionais_valor else 'Nenhuma instrução adicional fornecida.'
        )

        final_contents_for_api = [system_instruction_text] + user_content_parts + [user_prompt_text_string]

        try:
            with st.spinner("Gerando adaptação com IA... Por favor, aguarde."):
                model = genai.GenerativeModel(modelo_txt)
                response = model.generate_content(final_contents_for_api)

            full_response_text = response.text.strip()

            if not full_response_text:
                st.warning("A IA não gerou uma resposta de texto válida ou a resposta estava vazia.")
                st.session_state.output_adaptado = "Não foi possível gerar uma resposta. Tente novamente."
                st.session_state.output_justificativas = ""
            elif "# Justificativas:" in full_response_text:
                parts_split = full_response_text.split("# Justificativas:", 1)
                st.session_state.output_adaptado = parts_split[0].strip()
                st.session_state.output_justificativas = parts_split[1].strip()
            else:
                st.session_state.output_adaptado = full_response_text
                st.session_state.output_justificativas = "Nenhuma justificativa explícita fornecida pela IA."

            # ---- Atualização dos placeholders ----
            output_adaptado_placeholder.text_area(
                label='Texto Adaptado (A IncluIA pode cometer erros. Revise as respostas.):',
                value=st.session_state.output_adaptado,
                disabled=True,
                height=350
            )
            output_justificativas_placeholder.text_area(
                label='Justificativas da Adaptação:',
                value=st.session_state.output_justificativas,
                disabled=True,
                height=250
            )

        except Exception as e:
            st.error(f"Ocorreu um erro ({type(e).__name__}) ao chamar a IA: {e}")
            if "503" in str(e) or "RESOURCE_EXHAUSTED" in str(e).upper():
                 st.warning("O modelo da IA parece estar sobrecarregado ou você excedeu sua cota. Tente novamente mais tarde.")
            st.session_state.output_adaptado = "Não foi possível processar a solicitação devido a um erro."
            st.session_state.output_justificativas = ""

# --- Exibição dos Resultados na Interface ---

# CORREÇÃO DE BUG:
output_adaptado_placeholder = st.empty()
# st.text_area(label='Texto Adaptado (A IncluIA pode cometer erros. Revise as respostas.):',
#              value=st.session_state.output_adaptado,
#              disabled=True,
#              height=350,
#              key="output_adaptado_area")

if isinstance(st.session_state.output_adaptado, str) and st.session_state.output_adaptado.strip() and len(st.session_state.output_adaptado.split()) >= 20:
    metric_results_adapted = metricas_NLP(st.session_state.output_adaptado)
    if isinstance(metric_results_adapted, dict):
        col_ma1, col_ma2, col_ma3 = st.columns([1, 0.05, 1])
        with col_ma1:
            st.markdown(f"**Facilidade de Leitura (Flesch):** {metric_results_adapted['facilidade_leitura_val']} ({metric_results_adapted['facilidade_leitura_desc']})")
            st.markdown(f"**Série Aprox. (Flesch-Kincaid):** {metric_results_adapted['serie_aprox_val']} ({metric_results_adapted['serie_aprox_desc']})")
        with col_ma3:
            st.markdown(f"**Nível Escolar (SMOG):** {metric_results_adapted['nivel_escolar_val']} ({metric_results_adapted['nivel_escolar_desc']})")
            st.markdown(f"**Variedade Lexical:** {metric_results_adapted['variedade_lexical_val']} ({metric_results_adapted['variedade_lexical_desc']})")
    else:
        st.info(metric_results_adapted)
else:
    if st.session_state.output_adaptado and len(st.session_state.output_adaptado.split()) < 20:
        st.warning("Texto adaptado muito curto ou vazio para análise de legibilidade (mínimo 20 palavras).")

# CORREÇÃO DE BUG:
output_justificativas_placeholder = st.empty()
# st.text_area(label='Justificativas da Adaptação:',
#              value=st.session_state.output_justificativas,
#              disabled=True,
#              height=250,
#              key="output_justificativas_area")

st.markdown('---')
st.caption("Lembre-se: A IncluIA é uma ferramenta de auxílio. Revise as respostas.")
