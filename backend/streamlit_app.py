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

# Groq Client Setup - Protegido contra erro de inicialização
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")

def get_groq_client():
    if not GROQ_API_KEY:
        st.error("🔑 **Chave API da Groq não encontrada!** Por favor, configure `GROQ_API_KEY` nos Secrets do Streamlit.")
        st.info("💡 Como configurar: Vá em Settings -> Secrets no painel do Streamlit Cloud.")
        return None
    return OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY
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
    client = get_groq_client()
    if not client:
        return "Erro: Chave API não configurada corretamente."

    # Limite seguro de caracteres
    texto_para_resumir = texto_completo[:15000]
    
    prompt = f"""
    Atue como um assistente especialista em resumir vídeos do YouTube.
    Faça um resumo estruturado e profissional do texto abaixo.
    Use tópicos (bullet points) claros e destaque as conclusões principais.
    Responda SEMPRE em Português do Brasil.
    
    Texto do vídeo:
    {texto_para_resumir}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Modelo atualizado e mais potente
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
                
                # 1. Configurar Cookies e Headers
                cookies_content = st.secrets.get("YOUTUBE_COOKIES", None)
                cookie_file = "cookies.txt"
                if cookies_content and not os.path.exists(cookie_file):
                    with open(cookie_file, "w") as f:
                        f.write(cookies_content)
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Referer': 'https://www.youtube.com/',
                }

                # 2. TENTATIVA 1: yt-dlp (Método mais robusto)
                data = None
                try:
                    st.write("📡 Conectando ao YouTube (Primário)...")
                    ydl_opts = {
                        'skip_download': True,
                        'writesubtitles': True,
                        'writeautomaticsub': True,
                        'quiet': True,
                        'no_warnings': True,
                        'cookiefile': cookie_file if os.path.exists(cookie_file) else None,
                        'user_agent': headers['User-Agent'],
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        subs = info.get('automatic_captions') or info.get('subtitles')
                        
                        if subs:
                            # Tenta pegar qualquer idioma disponível (prioridade PT, depois EN)
                            target_sub_lang = 'pt' if 'pt' in subs else ('en' if 'en' in subs else next(iter(subs.keys())))
                            sub_tracks = subs[target_sub_lang]
                            json3_track = next((t for t in sub_tracks if t.get('ext') == 'json3'), sub_tracks[0])
                            
                            r = requests.get(json3_track['url'], headers=headers, timeout=10)
                            if r.status_code == 200:
                                data = r.json()
                                st.write(f"✅ Legendas obtidas (Base: {target_sub_lang})")
                except Exception as e_dlp:
                    st.write(f"⚠️ Método primário falhou. Tentando backup...")

                # 3. TENTATIVA 2: YouTubeTranscriptApi (Backup)
                if not data:
                    try:
                        st.write("📡 Conectando via canais alternativos...")
                        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookie_file if os.path.exists(cookie_file) else None)
                        
                        # Tenta PT, depois EN, depois qualquer uma
                        try:
                            t_obj = transcript_list.find_transcript(['pt', 'en'])
                        except:
                            t_obj = next(iter(transcript_list))
                        
                        raw_data = t_obj.fetch()
                        data = {'events': []}
                        for entry in raw_data:
                            data['events'].append({
                                'tStartMs': entry['start'] * 1000,
                                'segs': [{'utf8': entry['text']}]
                            })
                        st.write(f"✅ Legendas obtidas via backup ({t_obj.language_code})")
                    except Exception as e_api:
                         raise Exception("Não foi possível obter legendas. O YouTube pode estar bloqueando o acesso temporariamente (Erro 429).")

                if not data:
                    raise Exception("Nenhuma legenda encontrada para este vídeo.")

                # 4. Processamento do texto
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

    # Tabs para Transcrição
    st.write("---")
    st.markdown("### 📄 Transcrição Completa")
    tab1, tab2 = st.tabs(["Texto Limpo", "Com Timestamps"])
    
    with tab1:
        st.code(st.session_state['transcript_text'], language="text")
        st.download_button("Baixar Texto", st.session_state['transcript_text'], "transcricao.txt")
        
    with tab2:
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
