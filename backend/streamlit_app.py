import streamlit as st
import yt_dlp
import requests
import os
import time
import re
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

# Configuração da Página
st.set_page_config(
    page_title="YT Transcrib + AI",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Groq Client Setup
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=st.secrets.get("GROQ_API_KEY")
)

# Estilização Customizada (CSS)
st.markdown("""
<style>
    .stApp {
        background-color: #0e0e11;
        color: #efeff1;
    }
    .stButton>button {
        background-color: #e50914;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #b2070f;
        transform: scale(1.02);
    }
    .stTextInput>div>div>input {
        background-color: #18181b;
        color: white;
        border-radius: 8px;
        border: 1px solid #2d2d30;
    }
    .success-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #18181b;
        border: 1px solid #2d2d30;
        margin-top: 1rem;
    }
    h1 {
        background: -webkit-linear-gradient(45deg, #e50914, #ff6b6b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .video-preview {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #2d2d30;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Funções Utilitárias

def extract_video_id(url):
    """Extrai o ID do vídeo de várias formas de URL do YouTube"""
    if not url:
        return None
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtube\.com\/watch\?.+&v=)([^&\s]+)',
        r'youtu\.be\/([^?\s]+)',
        r'youtube\.com\/embed\/([^?\s]+)',
        r'youtube\.com\/shorts\/([^?\s]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def resumir_transcricao(texto_completo):
    """Gera um resumo estruturado usando Groq (Llama 3)"""
    # Limite seguro de caracteres para o contexto
    texto_para_resumir = texto_completo[:15000]
    
    prompt = f"""
    Atue como um assistente especialista em análise de conteúdo de vídeo.
    Sua tarefa é criar um resumo executivo, estruturado e altamente informativo do texto abaixo.
    
    A estrutura deve seguir este padrão:
    1. 📌 **Visão Geral**: Um parágrafo curto resumindo o tema principal.
    2. 🔑 **Pontos Chave**: Lista com os momentos e ideias mais importantes.
    3. 💡 **Conclusão/Insight**: Qual a principal lição ou mensagem final do vídeo.
    
    Regras:
    - Responda SEMPRE em Português do Brasil.
    - Use Markdown para formatação.
    - Seja direto, mas mantenha a profundidade das informações.
    
    Texto do vídeo:
    {texto_para_resumir}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Você é um assistente útil que resume vídeos com precisão."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erro ao gerar resumo: {str(e)}"

# Título e Cabeçalho
st.title("YT Transcrib 🎙️ + AI")
st.write("Transcreva vídeos e gere resumos inteligentes com Inteligência Artificial.")

# Input da URL
url = st.text_input("Cole a URL do vídeo aqui:", placeholder="https://www.youtube.com/watch?v=...")

# Preview do Vídeo
video_id = extract_video_id(url)
if video_id:
    st.markdown("📺 **Confirme o vídeo:**")
    st.video(url)

# Botão Principal
if st.button("🚀 Transcrever Vídeo", use_container_width=True):
    if not url or not video_id:
        st.warning("⚠️ Por favor, insira uma URL válida.")
    else:
        with st.status("Processando...", expanded=True) as status:
            try:
                st.write("🔍 Conectando ao YouTube...")
                
                # Configurar Cookies se existirem
                cookies_content = st.secrets.get("YOUTUBE_COOKIES", None)
                cookie_file = "cookies.txt"
                if cookies_content and not os.path.exists(cookie_file):
                    with open(cookie_file, "w") as f:
                        f.write(cookies_content)
                
                # Tenta baixar a legenda original (Método mais estável)
                data = None
                try:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookie_file if os.path.exists(cookie_file) else None)
                    # Tenta qualquer idioma disponível, priorizando PT/EN
                    try:
                        t_obj = transcript_list.find_generated_transcript(['pt', 'en', 'es', 'fr'])
                    except:
                        t_obj = next(iter(transcript_list))
                    
                    raw_data = t_obj.fetch()
                    data = {'events': []}
                    for entry in raw_data:
                        data['events'].append({
                            'tStartMs': entry['start'] * 1000,
                            'segs': [{'utf8': entry['text']}]
                        })
                except Exception as e_api:
                    st.write("⚠️ Método 1 falhou. Tentando backup...")
                    # Fallback com yt-dlp
                    ydl_opts = {'skip_download': True, 'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        subs = info.get('automatic_captions') or info.get('subtitles')
                        if subs:
                            first_key = next(iter(subs.keys()))
                            sub_url = next((t for t in subs[first_key] if t.get('ext') == 'json3'), subs[first_key][0])['url']
                            r = requests.get(sub_url, timeout=10)
                            if r.status_code == 200: data = r.json()

                if not data:
                    raise Exception("Não foi possível obter nenhuma legenda para este vídeo.")

                # Processamento do texto
                st.write("📝 Organizando transcrição...")
                full_transcript = []
                temp_text = []
                for event in data.get('events', []):
                    if 'segs' not in event: continue
                    text = "".join([s.get('utf8', '') for s in event['segs']]).strip()
                    if text:
                        start = event.get('tStartMs', 0) / 1000.0
                        timestamp = time.strftime('%H:%M:%S', time.gmtime(start))
                        full_transcript.append({'timestamp': timestamp, 'text': text})
                        temp_text.append(text)
                
                transcript_text = " ".join(temp_text)
                st.session_state['transcript_text'] = transcript_text
                st.session_state['full_transcript'] = full_transcript
                
                status.update(label="Transcrição Concluída!", state="complete", expanded=False)
                st.success("✅ Texto extraído com sucesso!")

            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
                st.info("Dica: Verifique se o vídeo tem legendas disponíveis.")

# Área de Resultados (se houver transcrição)
if 'transcript_text' in st.session_state:
    st.divider()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("✨ Gerar Resumo com IA", use_container_width=True, type="secondary"):
            with st.spinner("🤖 Groq está analisando o vídeo..."):
                resumo = resumir_transcricao(st.session_state['transcript_text'])
                st.session_state['resumo_ia'] = resumo

    # Exibição do Resumo
    if 'resumo_ia' in st.session_state:
        st.markdown("### 📝 Resumo Inteligente")
        st.info(st.session_state['resumo_ia'])
        st.download_button("📥 Baixar Resumo", st.session_state['resumo_ia'], "resumo_ia.txt")

    # Tabs para Transcrição e Chat
    st.write("---")
    tab_chat, tab_txt, tab_ts = st.tabs(["💬 Chat com Vídeo", "📄 Texto Limpo", "🕒 Timestamps"])

    with tab_chat:
        st.markdown("### Pergunte algo sobre o vídeo")
        st.caption("A IA usará a transcrição completa como contexto para responder.")
        
        # Inicializar histórico do chat se não existir
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Exibir mensagens anteriores
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Input do usuário
        if prompt := st.chat_input("Ex: Qual o ponto principal deste vídeo?"):
            # Adicionar mensagem do usuário ao histórico
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Gerar resposta
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                try:
                    # Contexto: Transcrição (limitada para caber no modelo)
                    contexto = st.session_state['transcript_text'][:15000]
                    
                    messages = [
                        {"role": "system", "content": f"Você é um assistente especialista que responde perguntas baseadas na transcrição de um vídeo. Use o contexto abaixo para responder de forma precisa e direta em Português do Brasil.\n\nCONTEÚDO DO VÍDEO:\n{contexto}"},
                    ]
                    
                    # Adicionar histórico da conversa (últimas 5 mensagens para manter contexto)
                    for m in st.session_state.messages[-5:]:
                        messages.append({"role": m["role"], "content": m["content"]})

                    response = client.chat.completions.create(
                        model="llama3-8b-8192",
                        messages=messages,
                        temperature=0.7,
                        stream=True
                    )

                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                except Exception as e:
                    st.error(f"Erro no chat: {str(e)}")

    with tab_txt:
        st.code(st.session_state['transcript_text'], language="text")
        st.download_button("Baixar Texto", st.session_state['transcript_text'], "transcricao.txt")
        
    with tab_ts:
        ts_text = "\n".join([f"[{e['timestamp']}] {e['text']}" for e in st.session_state['full_transcript']])
        st.code(ts_text, language="text")
        st.download_button("Baixar com Tempo", ts_text, "transcricao_timestamps.txt")

# Rodapé
st.markdown("""
<br><br>
<div style='text-align: center; color: #666; font-size: 12px; padding: 20px; border-top: 1px solid #2d2d30;'>
    <p>© 2026 <b>Alerial</b> - Inteligência em Transcrição</p>
</div>
""", unsafe_allow_html=True)
