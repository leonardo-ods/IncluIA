import streamlit as st
import os
from google import genai
from google.genai import types
import io
import tempfile
import fitz  # PyMuPDF
from docx import Document
from docx2pdf import convert
from auth_utils import authenticate_user

# --- Configurações Iniciais da Página ---
st.set_page_config(
    page_title="IncluIA",
    page_icon="🧩",
    initial_sidebar_state="expanded"
)

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

# --- Autenticação e Configuração da API ---
if not authenticate_user():
    st.stop()

try:
    api_key_from_profile = st.session_state.profile.get('gemini_api_key')

    if not api_key_from_profile:
        st.error("Chave da API não encontrada no perfil após a autenticação. Tente fazer logout e login novamente.")
        st.stop()

    client = genai.Client(api_key=api_key_from_profile)

    modelo_texto_avancado = 'gemini-2.5-flash'
    modelo_gerador_imagem = 'gemini-2.0-flash-exp-image-generation'
    
except Exception as e:
    st.error(f"Erro ao inicializar o cliente Gemini. Detalhe: {e}")
    st.stop()
    

# Funções de conversão de arquivo (mantidas)
def convert_pdf_bytes_to_image_bytes_pymupdf(pdf_bytes):
    image_bytes_list = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes('jpeg')
            image_bytes_list.append(img_bytes)
        doc.close()
    except Exception as e:
        st.error(f'Erro ao converter PDF para imagem: {e}')
    return image_bytes_list

def convert_docx_bytes_to_image_bytes_with_pymupdf(docx_bytes):
    image_bytes_list = []
    temp_docx_file = None
    temp_pdf_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_docx:
            tmp_docx.write(docx_bytes)
            temp_docx_file = tmp_docx.name
        temp_pdf_file = temp_docx_file.replace('.docx', '.pdf')
        try:
            st.info('Tentando converter DOCX para PDF...')
            convert(temp_docx_file, temp_pdf_file)
        except Exception as e_convert:
            st.error(f'Erro ao converter DOCX para PDF: {e_convert}')
            return []
        if os.path.exists(temp_pdf_file):
            with open(temp_pdf_file, 'rb') as f_pdf:
                pdf_bytes_converted = f_pdf.read()
            image_bytes_list = convert_pdf_bytes_to_image_bytes_pymupdf(pdf_bytes_converted)
        else:
            st.warning('Arquivo PDF temporário não foi criado do DOCX.')
    except Exception as e:
        st.error(f'Erro na conversão de DOCX: {e}')
    finally:
        if temp_docx_file and os.path.exists(temp_docx_file): os.remove(temp_docx_file)
        if temp_pdf_file and os.path.exists(temp_pdf_file): os.remove(temp_pdf_file)
    return image_bytes_list

def adicionar_sugestao(sugestao):
    texto_atual = st.session_state['instrucoes_adicionais']
    st.session_state['instrucoes_adicionais'] = (texto_atual + ', ' + sugestao) if texto_atual else sugestao


# --- UI ---
st.title('🧩 IncluIA - Gerador de Imagens')
st.warning('**Atenção: A geração de imagens pela IncluIA é experimental e pode não fornecer os resultados desejados.**')

if 'campo_input_text' not in st.session_state:
    st.session_state.campo_input_text = ''
if 'adversidade_selecionada' not in st.session_state:
    st.session_state.adversidade_selecionada = 'Não especificado'
if 'instrucoes_adicionais' not in st.session_state: 
    st.session_state.instrucoes_adicionais = ''

st.text_area(
    label='Descreva a questão/conceito original:', 
    height=150, 
    key='campo_input_text'
)

campo_upload = st.file_uploader(
    label='Ou faça upload (PDF, Word, JPEG, PNG):', 
    type=['pdf', 'docx', 'jpeg', 'png']
)

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

st.selectbox(
    label='Adversidade do aluno:', 
    options=adversidades,
    key='adversidade_selecionada'
)

sugestoes = ['Exemplos do cotidiano',
             'Uso de símbolos',
             'Língua estrangeira',
             'Riqueza em detalhes',
             'Minimalista'
]

st.text_input('Instruções adicionais para imagem:', key='instrucoes_adicionais')

cols = st.columns(len(sugestoes))
for col, sugestao_btn in zip(cols, sugestoes):
    col.button(sugestao_btn, on_click=adicionar_sugestao, args=(sugestao_btn,))
st.markdown('---')

# --- PROMPTS E CONFIGS DA IA (SEM MUDANÇAS) ---
system_instruction_text_image_prompt_generator = """
Você é IncluIA, especialista em design universal para aprendizagem e na criação de prompts para geração de imagens educativas acessíveis para alunos com Necessidades Educativas Especiais (NEEs). Sua missão é traduzir um conceito educacional em um prompt de imagem eficaz e uma descrição textual clara, balanceando riqueza visual com acessibilidade.

**PRINCÍPIOS PARA UM PROMPT VISUALMENTE CLARO E EFICAZ:**

1.  **Ação Simplificada:** Em vez de evitar ações, descreva-as de forma direta e singular. Foque na ação principal. Em vez de "um time competindo ferozmente", prefira "duas crianças sorrindo e chutando uma bola de futebol". Ações claras são mais fáceis de gerar e entender.
2.  **Hierarquia Visual Clara:** A imagem deve ter um foco principal óbvio. O prompt deve guiar a IA a construir a cena com clareza, definindo o que é mais importante. Uma boa estrutura é: **[Sujeito e Ação Principal]** em **[Cenário Relevante]** com **[Elementos de Contexto Simples]**.
3.  **Cenário Relevante, mas Descomplicado:** O fundo deve dar contexto sem competir com a cena principal. Em vez de um fundo branco genérico, use cenários simples como "um campo de grama verde", "um céu azul claro", "uma parede de sala de aula com um quadro", garantindo que tenham poucos detalhes.

**PROCESSO DE CRIAÇÃO:**

Ao receber um conceito, NEE e instruções, siga estes passos:

1.  **Análise do Objetivo:** Identifique o conceito ou cena central que a imagem deve ilustrar.
2.  **Formulação do PROMPT em INGLÊS:** Crie um prompt que construa a imagem em camadas de importância, para guiar a IA de forma eficaz:
    a. **Estilo Visual:** Comece sempre com o estilo. O padrão é `2D cartoon, friendly art style, bold outlines`.
    b. **Cena Principal (Sujeito e Ação):** Descreva o foco principal. Ex: `Two happy children, a boy and a girl, playing soccer`.
    c. **Cenário e Contexto:** Descreva onde a ação acontece e adicione um ou dois elementos de fundo para dar vida à cena. Ex: `on a simple green grass field with a small soccer goal in the background`.
    d. **Atmosfera e Qualidade:** Adicione termos que definam a sensação geral e a qualidade técnica. Ex: `bright and vibrant colors`, `clear blue sky`, `no complex shadows`, `simple details`.
    e. **Escrita na Imagem:** Se precisar de texto, ele deve ser em PORTUGUÊS (a menos que a instrução seja "Língua estrangeira"). A instrução no prompt em inglês deve ser clara. Ex: `A sign with the Portuguese text 'Diversão' written on it.`

3.  **Criação da DESCRIÇÃO TEXTUAL:** Em português, descreva a cena que você idealizou, incluindo a ação, os personagens e o ambiente.
4.  **Justificativa das Escolhas:** Em português, explique como a sua escolha de cena, estilo e cores torna a imagem um bom apoio visual para a NEE especificada, focando em clareza, representatividade e na ausência de distrações.

**ATENÇÃO:** A imagem gerada servirá de APOIO para a questão. NÃO PODE conter textos explicativos complexos ou a resposta. Sua função é ilustrar o conceito de forma engajadora e clara.

**NÃO utilize formatações no texto (negrito, itálico, etc.), nem inclua caracteres especiais como asteriscos ("*"). Quero apenas o texto puro, SEM MARKDOWN.**

**Exemplo de um BOM prompt que você deve gerar (para o caso do futebol):**
`2D cartoon, friendly art style. Two happy, diverse children kicking a soccer ball on a simple green grass field. A small soccer goal is visible in the background under a clear blue sky. Bright and vibrant colors, bold outlines, no complex shadows.`

**Output ESTRITO:**

# Prompt da Imagem:
[Seu prompt detalhado em INGLÊS aqui]
# Descrição da Imagem:
[Sua descrição em PORTUGUÊS aqui]
# Justificativas:
[Suas justificativas em PORTUGUÊS aqui]
"""
prompt_base_template_image = """
Gere prompt, descrição e justificativas para o conteúdo abaixo, adaptado para {nee_type}.
{nee_guidelines}
Instruções adicionais para {nee_type_short}: '{instrucoes_adicionais_val}'
Conteúdo Original:
"""
nee_details_image = {
    'Não especificado': {'guidelines': 'Clareza visual.', 'short_name': 'NEEs'},
    'TEA': {'guidelines': 'Imagens literais, estilo limpo, cores calmas.', 'short_name': 'TEA'},
    'TDAH': {'guidelines': 'Elementos que capturem atenção, organizados.', 'short_name': 'TDAH'},
    'Deficiência Intelectual': {'guidelines': 'Imagens simples, concretas, cartoon.', 'short_name': 'DI'},
    'Deficiência Visual': {'guidelines': 'Descrição EXTREMAMENTE DETALHADA. Imagem com elementos distintos.', 'short_name': 'DV'},
    'Deficiência Auditiva': {'guidelines': 'Imagens claras, contexto visual definido.', 'short_name': 'DA'},
    'Dislexia': {'guidelines': 'Layout limpo, bom contraste.', 'short_name': 'Dislexia'},
    'Discalculia': {'guidelines': 'Representações visuais claras de números.', 'short_name': 'Discalculia'},
    'Altas Habilidades/Superdotação': {'guidelines': 'Imagens que incitem curiosidade, abstratas.', 'short_name': 'AH/SD'}
}

col1_btn, col2_btn, col3_btn = st.columns([1, 2, 1])
with col2_btn:
    btn_gerar_imagem = st.button(label='GERAR IMAGEM E DESCRIÇÃO', use_container_width=True)

if 'generated_image' not in st.session_state: st.session_state.generated_image = None
if 'image_description' not in st.session_state: st.session_state.image_description = ''
if 'image_justification' not in st.session_state: st.session_state.image_justification = ''

# --- LÓGICA DE GERAÇÃO ---
if btn_gerar_imagem:
    st.session_state.generated_image = None
    st.session_state.image_description = 'Gerando...'
    st.session_state.image_justification = 'Gerando...'

    input_parts_for_text_model = []
    original_text_from_input_field = st.session_state.campo_input_text.strip()

    if campo_upload is not None:
        file_bytes = campo_upload.read()
        file_type = campo_upload.type
        with st.spinner(f'Processando {campo_upload.name}...'):
            if file_type == 'application/pdf':
                img_list = convert_pdf_bytes_to_image_bytes_pymupdf(file_bytes)
                for img_bytes in img_list: input_parts_for_text_model.append(types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg'))
            elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                img_list = convert_docx_bytes_to_image_bytes_with_pymupdf(file_bytes)
                if img_list:
                    for img_bytes in img_list: input_parts_for_text_model.append(types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg'))
                elif not original_text_from_input_field:
                    try:
                        doc = Document(io.BytesIO(file_bytes))
                        extracted_text = '\n'.join([p.text for p in doc.paragraphs])
                        if extracted_text.strip():
                            original_text_from_input_field = extracted_text
                            st.info('Texto do DOCX usado para prompt.')
                    except Exception as e: st.warning(f'Erro ao extrair texto do DOCX: {e}')
            elif file_type in ['image/jpeg', 'image/png']:
                input_parts_for_text_model.append(types.Part.from_bytes(data=file_bytes, mime_type=file_type))
            else: st.error('Tipo de arquivo não suportado.')

    if original_text_from_input_field:
        input_parts_for_text_model.append(types.Part.from_text(text=f'Texto original: {original_text_from_input_field}'))

    if not input_parts_for_text_model:
        st.warning('Insira uma descrição textual ou faça o upload de um arquivo para continuar.')
    else:
        instrucoes_adicionais_valor = st.session_state.instrucoes_adicionais
        selectbox_adv = st.session_state.adversidade_selecionada
        selected_nee_info = nee_details_image.get(selectbox_adv, nee_details_image['Não especificado'])

        with st.spinner('IA elaborando prompt...'):
            try:
                user_prompt_str = prompt_base_template_image.format(
                    nee_type=selectbox_adv, nee_guidelines=selected_nee_info['guidelines'],
                    nee_type_short=selected_nee_info['short_name'],
                    instrucoes_adicionais_val=instrucoes_adicionais_valor or 'Nenhuma.'
                )
                final_contents_text = [
                    types.Part.from_text(text=system_instruction_text_image_prompt_generator),
                    types.Part.from_text(text=user_prompt_str)
                ]
                final_contents_text.extend(input_parts_for_text_model)
                
                response_text_ia = client.models.generate_content(
                    model=modelo_texto_avancado,
                    contents=final_contents_text,
                    config=None
                )
                
                text_output = ''
                if response_text_ia.candidates and response_text_ia.candidates[0].content and response_text_ia.candidates[0].content.parts:
                    text_output = response_text_ia.candidates[0].content.parts[0].text.strip()
                elif hasattr(response_text_ia, 'text'): 
                    text_output = response_text_ia.text.strip()

                if not text_output:
                    st.error('IA (geradora de prompt) não retornou texto.')
                    st.session_state.image_description, st.session_state.image_justification = 'Falha.', 'Falha.'
                else:
                    image_prompt_from_ia = 'Não gerado.'
                    try:
                        parts = text_output.split('# Descrição da Imagem:', 1)
                        prompt_part_text = parts[0].replace('# Prompt da Imagem:', '').strip()
                        parts2 = parts[1].split('# Justificativas:', 1)
                        desc_part_text = parts2[0].strip()
                        just_part_text = parts2[1].strip()

                        if prompt_part_text and desc_part_text and just_part_text:
                            image_prompt_from_ia = prompt_part_text
                            st.session_state.image_description = desc_part_text
                            st.session_state.image_justification = just_part_text
                        else:
                            raise ValueError('Parsing falhou, uma das seções está vazia.')
                            
                    except Exception as e_parse:
                        st.warning(f'Parse da resposta da IA (prompt) falhou: {e_parse}. Tentando usar resposta bruta.')
                        st.text_area('Resposta Bruta IA Texto:', value=text_output, height=100)
                        if '# Prompt da Imagem:' in text_output:
                            image_prompt_from_ia = text_output.split('# Prompt da Imagem:',1)[1].split('#')[0].strip()
                        else:
                            image_prompt_from_ia = text_output
                        st.session_state.image_description = 'Verifique resposta bruta para descrição.'
                        st.session_state.image_justification = 'Verifique resposta bruta para justificativas.'

                    if image_prompt_from_ia != 'Não gerado.' and image_prompt_from_ia.strip():
                        st.success('Prompt para imagem gerado!')
                        #st.info(f'**Prompt para imagem:**\n{image_prompt_from_ia}')

                        with st.spinner('IA gerando imagem...'):
                            try:
                                image_gen_config = types.GenerateContentConfig(
                                    response_modalities=['TEXT', 'IMAGE']
                                )
                                image_gen_contents = image_prompt_from_ia

                                response_image_ia = client.models.generate_content(
                                    model=modelo_gerador_imagem,
                                    contents=image_gen_contents,
                                    config=image_gen_config
                                )

                                generated_image_bytes = None
                                
                                if response_image_ia.candidates:
                                    for part in response_image_ia.candidates[0].content.parts:
                                        if part.inline_data is not None and hasattr(part.inline_data, 'data') and hasattr(part.inline_data, 'mime_type') and part.inline_data.mime_type.startswith('image/'):
                                            generated_image_bytes = part.inline_data.data
                                            break
                                        elif hasattr(part, 'data') and part.data and hasattr(part, 'mime_type') and part.mime_type.startswith('image/'):
                                            generated_image_bytes = part.data
                                            break

                                if generated_image_bytes:
                                    st.session_state.generated_image = generated_image_bytes
                                    st.success('Imagem gerada!')
                                else:
                                    st.error('Falha ao obter bytes da imagem. Nenhuma parte de imagem foi encontrada na resposta da API.')
                                    st.session_state.generated_image = None

                            except Exception as e_img:
                                err_type_name_img = type(e_img).__name__
                                st.error(f'Erro ({err_type_name_img}) ao gerar imagem: {e_img}')
                                st.session_state.generated_image = None
                    else:
                        st.error('Não foi possível criar um prompt de imagem válido.')
                        st.session_state.image_description, st.session_state.image_justification = 'Falha: prompt.', 'Falha: prompt.'
            except Exception as e_txt:
                err_type_name_txt = type(e_txt).__name__
                st.error(f'Erro ({err_type_name_txt}) ao chamar IA (prompt): {e_txt}')
                st.session_state.image_description, st.session_state.image_justification = f'Erro: {err_type_name_txt}', f'Erro: {err_type_name_txt}'
                if hasattr(e_txt, 'message'): st.error(f'Detalhe: {e_txt.message}')
                elif '503' in str(e_txt) or 'UNAVAILABLE' in str(e_txt).upper() or 'RESOURCE_EXHAUSTED' in str(e_txt).upper(): st.warning('Modelo IA sobrecarregado.')

# --- Exibição ---
st.markdown('---')
st.subheader('Resultado da Geração:')
if st.session_state.generated_image:
    st.image(st.session_state.generated_image, caption='Imagem Gerada pela IncluIA', use_column_width=True)
else:
    st.info('A imagem gerada aparecerá aqui.')
st.text_area(label='Descrição da Imagem (gerada pela IA):', value=st.session_state.image_description, disabled=True, height=150)
st.text_area(label='Justificativas da Adaptação Visual (geradas pela IA):', value=st.session_state.image_justification, disabled=True, height=200)
st.markdown('---')
st.caption('Lembre-se: A IncluIA é uma ferramenta de auxílio. Revise as respostas.')
