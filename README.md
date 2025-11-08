# IncluIA 🧩

O **IncluIA** é uma ferramenta educacional de código aberto, projetada para auxiliar na adaptação de materiais didáticos e avaliativos para estudantes com Necessidades Educacionais Especiais (NEEs). Utilizando o poder da Inteligência Artificial generativa do Google Gemini, a aplicação visa promover a inclusão e a equidade no ambiente de aprendizagem.

Este projeto nasceu como uma Atividade Extensionista da faculdade e foi prototipado e testado em uma escola na cidade de Valente-BA, com o objetivo de fornecer uma solução prática e acessível para educadores. Agora, está disponível para toda a comunidade.

---

## ✨ Funcionalidades

O IncluIA oferece duas ferramentas principais para apoiar educadores:

1.  **Adaptação de Conteúdo:**
    *   **Análise de Legibilidade:** Métricas como Flesch Reading-Ease, Flesch-Kincaid Grade Level e SMOG Index são utilizadas para avaliar a complexidade do texto original.
    *   **Adaptação Inteligente:** Com base no texto ou documento (PDF/DOCX) fornecido, na NEE selecionada e em instruções adicionais, a IA adapta o conteúdo, simplificando a linguagem, reestruturando questões e removendo barreiras de aprendizagem.
    *   **Justificativas Pedagógicas:** A ferramenta fornece explicações detalhadas sobre as adaptações realizadas, auxiliando o educador a compreender as escolhas feitas pela IA.

2.  **Gerador de Imagens Acessíveis:**
    *   **Ilustração de Conceitos:** A partir de uma descrição textual ou de um documento, a IA gera imagens para ilustrar conceitos de forma visualmente acessível.
    *   **Prompts Otimizados:** A ferramenta cria prompts de geração de imagem otimizados para clareza e acessibilidade, considerando a NEE do aluno.
    *   **Descrição e Justificativa:** Cada imagem gerada é acompanhada de uma descrição detalhada (útil para leitores de tela) e uma justificativa da sua adequação pedagógica.

---

## 💻 Tecnologias Utilizadas

O projeto foi construído com as seguintes tecnologias:

*   **Frontend:** [Streamlit](https://streamlit.io/)
*   **Inteligência Artificial:** [Google Gemini](https://ai.google.dev/)
*   **Autenticação e Banco de Dados:** [Supabase](https://supabase.com/)
*   **Manipulação de Documentos:** PyMuPDF (Fitz), python-docx, docx2pdf
*   **Análise de Texto:** textstat
*   **Linguagem:** Python

---

## 🌐 Acesse o Projeto

O IncluIA está disponível publicamente e pode ser acessado diretamente pelo link abaixo:

👉 [incluia.streamlit.app](https://incluia.streamlit.app/)

Não é necessário instalar nada: basta criar uma conta simples e gratuita com e-mail, nome de usuário e senha.

Após o cadastro, será solicitado que você informe sua chave de API do Gemini (modelo de IA do Google).
Na própria página de criação de conta há instruções e um link direto para gerar a chave, mas aqui vai um resumo rápido:

1. Acesse o site [aistudio.google.com/app/apikey](https://aistudio.google.com/app/api-keys)
2. Faça login com sua conta Google.
3. Clique em “Criar chave de API”.
4. Copie a chave gerada e cole no campo correspondente dentro do IncluIA.

Pronto! 🎉
Com isso, você já pode começar a adaptar questões e avaliar o potencial da inteligência artificial generativa para promover inclusão educacional.

---

## 🖼️ Demonstração

### Demonstração da adaptação textual:
<img width="1914" height="914" alt="image" src="https://github.com/user-attachments/assets/15a66908-b076-4f58-ad88-2f1fe5388ab2" />
<img width="1918" height="915" alt="image" src="https://github.com/user-attachments/assets/2c466cef-3fb1-4477-ba25-8b75eeef8d46" />

### Demonstração da geração de imagens:
<img width="1911" height="908" alt="image" src="https://github.com/user-attachments/assets/12252b41-ff5b-48d0-a894-9e596b198316" />
<img width="1910" height="920" alt="image" src="https://github.com/user-attachments/assets/6b05f28f-0a28-4dd9-a81c-41fae12bb7c3" />

---

## 📝 Licença

Este projeto está sob a licença [MIT](LICENSE). Veja o arquivo `LICENSE` para mais detalhes.
