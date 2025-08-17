import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import re

# --- FUNÇÕES AUXILIARES ---

def init_supabase_client() -> Client:
    """Inicializa e retorna o cliente Supabase usando variáveis de ambiente."""
    try:
        url = st.secrets["supabase_url"]
        key = st.secrets["supabase_key"]
    except KeyError:
        st.error("Credenciais Supabase não encontradas. Verifique seu arquivo .env ou as configurações de ambiente.")
        st.stop()
        
    if not url or not key:
        st.error("As credenciais SUPABASE_URL e SUPABASE_KEY estão vazias. Verifique seu arquivo .env ou as configurações de ambiente.")
        st.stop()
    return create_client(url, key)

def show_api_key_form(error_message=None):
    """Mostra o formulário para inserir/atualizar a chave da API."""
    st.subheader("🔑 Configure sua Chave da API Gemini")
    st.markdown("Para usar a IncluIA, é necessária uma chave válida da API do Google Gemini.")

    if error_message:
        st.error(error_message)

    with st.expander("Como obter sua chave da API?"):
        st.markdown("""
        1. Vá para o [Google AI Studio](https://aistudio.google.com/app/apikey).
        2. Clique em **'Criar chave de API'**.
        3. Copie a chave criada e cole abaixo.

        **Importante:** A chave correta é uma sequência de 39 caracteres que sempre começa com `AIza`.
        """)

    with st.form("api_key_form"):
        gemini_api_key = st.text_input("Cole sua Chave da API Gemini aqui", type="password")
        submitted = st.form_submit_button("Salvar e Validar Chave")

        if submitted and gemini_api_key:
            submitted_key = gemini_api_key.strip()
            if not submitted_key.startswith("AIza") or len(submitted_key) != 39:
                st.error("Formato de chave inválido. A chave deve começar com 'AIza' e ter 39 caracteres. Por favor, copie a chave correta no Google AI Studio.")
                return

            try:
                genai.configure(api_key=submitted_key)
                genai.list_models()  # Uma chamada leve para testar a autenticação

                supabase = st.session_state.supabase_client
                user_id = st.session_state.user.id
                supabase.table('profiles').update({
                    'gemini_api_key': submitted_key
                }).eq('id', user_id).execute()

                st.success("Chave válida salva com sucesso! Recarregando...")
                if 'profile' in st.session_state:
                    del st.session_state['profile']
                if 'api_key_validated' in st.session_state:
                    del st.session_state['api_key_validated']
                st.rerun()

            except Exception as e:
                if "API key not valid" in str(e):
                    st.error("A chave tem o formato correto, mas é inválida. Verifique se você a copiou corretamente ou gere uma nova chave.")
                else:
                    st.error(f"Ocorreu um erro ao tentar validar a chave: {e}")


def show_set_username_form():
    """Mostra um formulário para usuários existentes definirem seu nome de usuário."""
    st.subheader("👋 Bem-vindo de volta!")
    st.info("Percebemos que você ainda não tem um nome de usuário. Por favor, crie um para continuar.")
    
    with st.form("set_username_form"):
        username = st.text_input("Escolha seu nome de usuário (letras minúsculas, números, sem espaços)")
        submitted = st.form_submit_button("Salvar Nome de Usuário")

        if submitted and username:
            if not re.match("^[a-z0-9_]+$", username):
                st.error("Nome de usuário inválido. Use apenas letras minúsculas, números e underscore (_).")
                return

            supabase = st.session_state.supabase_client
            user_id = st.session_state.user.id
            try:
                existing_user = supabase.table('profiles').select('id', count='exact').eq('username', username).execute()
                if existing_user.count > 0:
                    st.error("Este nome de usuário já está em uso. Por favor, escolha outro.")
                    return

                supabase.table('profiles').update({'username': username}).eq('id', user_id).execute()
                st.success("Nome de usuário salvo! Recarregando...")
                if 'profile' in st.session_state:
                    del st.session_state['profile']
                st.rerun()
            except Exception as e:
                st.error(f"Ocorreu um erro ao salvar o nome de usuário: {e}")


# --- FUNÇÃO PRINCIPAL DE AUTENTICAÇÃO ---

def authenticate_user():
    """
    Gerencia a autenticação, criação de perfil e validação da chave da API.
    Retorna True se o usuário está totalmente autenticado e configurado.
    """
    if 'supabase_client' not in st.session_state:
        st.session_state.supabase_client = init_supabase_client()
    supabase = st.session_state.supabase_client

    if 'user' not in st.session_state:
        st.title("🧩 Bem-vindo à IncluIA")
        st.write("Faça login ou crie sua conta para continuar.")
        login_tab, signup_tab = st.tabs(["Login", "Criar Conta"])
        
        with login_tab:
            with st.form("login_form"):
                identifier = st.text_input("Email ou Nome de Usuário")
                password = st.text_input("Senha", type="password")
                if st.form_submit_button("Login"):
                    try:
                        login_email = identifier
                        
                        if '@' not in identifier:
                            response = supabase.rpc('get_email_by_username', {'p_username': identifier}).execute()
                            
                            if response.data:
                                login_email = response.data
                            else:
                                st.error("Nome de usuário não encontrado.")
                                return None
                        
                        resp = supabase.auth.sign_in_with_password({"email": login_email, "password": password})
                        if resp.user:
                            st.session_state.user = resp.user
                            st.rerun()
                        else:
                            st.error("Ocorreu um erro inesperado durante o login.")
                    except Exception as e:
                        st.error(f"Falha no login: Verifique suas credenciais. {e}")

        with signup_tab:
            with st.form("signup_form"):
                email = st.text_input("Email para cadastro")
                username = st.text_input("Escolha um nome de usuário (ex: joao_silva)")
                password = st.text_input("Crie uma senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    if not email or not password or not username:
                        st.error("Por favor, preencha todos os campos.")
                        return

                    if not re.match("^[a-z0-9_]+$", username):
                        st.error("Nome de usuário inválido. Use apenas letras minúsculas, números e underscore (_).")
                        return

                    try:
                        resp = supabase.auth.sign_up({"email": email, "password": password})
                        if resp.user:
                            user = resp.user
                            supabase.table('profiles').insert({
                                'id': user.id,
                                'email': user.email,
                                'username': username
                            }).execute()
                            st.session_state.user = user
                            st.success("Conta criada com sucesso! Faça o login ou verifique seu e-mail para confirmação, se necessário.")
                            st.rerun()
                        else:
                           st.error("Ocorreu um erro inesperado ao criar a conta.")
                    except Exception as e:
                        if "duplicate key value violates unique constraint" in str(e) and "profiles_username_key" in str(e):
                            st.error("Erro ao criar conta: Este nome de usuário já está em uso.")
                        elif "User already registered" in str(e):
                            st.error("Erro ao criar conta: Este e-mail já está cadastrado.")
                        else:
                            st.error(f"Erro ao criar conta: {e}")
        return None

    if 'profile' not in st.session_state:
        try:
            profile_res = supabase.table('profiles').select('username, gemini_api_key').eq('id', st.session_state.user.id).single().execute()
            st.session_state.profile = profile_res.data
        except Exception as e:
            if "JSON object requested, but no row found" in str(e):
                st.error("Seu perfil não foi encontrado. Por favor, faça logout e tente criar a conta novamente.")
                supabase.auth.sign_out()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            else:
                st.error(f"Não foi possível buscar o perfil no banco de dados: {e}")
            return None

    if not st.session_state.profile.get('username'):
        show_set_username_form()
        return None

    if st.session_state.get('api_key_validated') is True:
        with st.sidebar:
            st.write(f"Logado como: `{st.session_state.user.email}`")
            st.write(f"Usuário: `{st.session_state.profile.get('username')}`")
            if st.button("Logout"):
                supabase.auth.sign_out()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        return True

    key_from_db = st.session_state.profile.get('gemini_api_key')
    if not key_from_db:
        show_api_key_form()
        return None

    try:
        genai.configure(api_key=key_from_db)
        genai.list_models()
        st.session_state.api_key_validated = True
        st.rerun()
    except Exception as e:
        error_msg = f"Houve um problema ao validar a chave: {e}"
        if "API key not valid" in str(e):
            error_msg = "A chave da API salva em sua conta é inválida. Por favor, insira uma chave válida."
        show_api_key_form(error_message=error_msg)
        return None