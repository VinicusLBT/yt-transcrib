import streamlit as st
import yt_dlp
import requests
import os
import time

# Configuração da Página
st.set_page_config(
    page_title="YT Transcrib",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed"
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
</style>
""", unsafe_allow_html=True)

# Título e Cabeçalho
st.title("YT Transcrib 🎙️")
st.write("Transforme vídeos do YouTube em texto em segundos.")

# Inputs
url = st.text_input("Cole a URL do vídeo aqui:", placeholder="https://www.youtube.com/watch?v=...")
lang_options = {"Português": "pt", "Inglês": "en", "Espanhol": "es", "Francês": "fr"}
selected_lang_name = st.selectbox("Idioma de Preferência:", list(lang_options.keys()))
lang = lang_options[selected_lang_name]

# Botão Transcrever
if st.button("Transcrever Vídeo", use_container_width=True):
    if not url:
        st.warning("⚠️ Por favor, insira uma URL válida.")
    else:
        with st.status("Processando...", expanded=True) as status:
            try:
                st.write("🔍 Conectando ao YouTube (Modo Seguro)...")
                
                # Configurar Cookies
                cookies_content = st.secrets.get("YOUTUBE_COOKIES", None)
                cookie_file = "cookies.txt"
                if cookies_content:
                    with open(cookie_file, "w") as f:
                        f.write(cookies_content)
                
                # Headers e Opções do yt-dlp
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.youtube.com/',
                }
                
                ydl_opts = {
                    'skip_download': True,
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'quiet': True,
                    'no_warnings': True,
                    'cookiefile': cookie_file if os.path.exists(cookie_file) else None,
                    'user_agent': headers['User-Agent'],
                }

                # Extração
                st.write("📥 Baixando legendas...")
                transcript_text = ""
                full_transcript = []

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    subs = info.get('automatic_captions') or info.get('subtitles')
                    
                    if not subs:
                        raise Exception("Nenhuma legenda encontrada para este vídeo.")
                    
                    # Lógica de Seleção de Idioma Melhorada
                    target_lang = None
                    # 1. Tenta exato
                    if lang in subs:
                        target_lang = lang
                    # 2. Tenta variações (pt-BR, pt-PT)
                    if not target_lang:
                        for code in subs.keys():
                            if code.startswith(lang):
                                target_lang = code
                                break
                    # 3. Fallback para prioridades
                    if not target_lang:
                        priority = ['pt', 'en']
                        for p in priority:
                            for code in subs.keys():
                                if code.startswith(p):
                                    target_lang = code
                                    break
                            if target_lang: break
                    # 4. Pega o primeiro que tiver
                    if not target_lang:
                        target_lang = list(subs.keys())[0]

                    st.write(f"📝 Processando idioma: {target_lang}...")
                    
                    sub_tracks = subs[target_lang]
                    json3_track = next((t for t in sub_tracks if t.get('ext') == 'json3'), None)
                    
                    if not json3_track:
                        # Tentar VTT se JSON3 falhar
                        raise Exception("Formato de legenda compatível não encontrado.")

                    r = requests.get(json3_track['url'], headers=headers)
                    data = r.json()

                    for event in data.get('events', []):
                        if 'segs' not in event: continue
                        text_seg = "".join([s.get('utf8', '') for s in event['segs']]).strip()
                        if not text_seg: continue
                        
                        start = event.get('tStartMs', 0) / 1000.0
                        timestamp = time.strftime('%H:%M:%S', time.gmtime(start))
                        
                        full_transcript.append(f"[{timestamp}] {text_seg}")
                        transcript_text += text_seg + " "

                status.update(label="Concluído!", state="complete", expanded=False)
                
                # Exibição dos Resultados
                st.success("Transcrição realizada com sucesso!")
                st.caption("Dica: Use o botão de copiar 📄 no canto superior direito do texto.")
                
                tab1, tab2 = st.tabs(["📄 Texto Corrido (Limpo)", "⏱️ Com Timestamps"])
                
                with tab1:
                    # Usando st.code para ganhar o botão de copiar nativo
                    st.code(transcript_text, language="text")
                    st.download_button("Baixar Texto (.txt)", data=transcript_text, file_name="transcricao_alerial.txt")
                
                with tab2:
                    timestamped_text = "\n".join(full_transcript)
                    st.code(timestamped_text, language="text")
                    st.download_button("Baixar com Tempo (.txt)", data=timestamped_text, file_name="transcricao_tempo_alerial.txt")

            except Exception as e:
                status.update(label="Erro", state="error", expanded=False)
                st.error(f"Ocorreu um erro: {str(e)}")
                st.info("Dica: Verifique se o vídeo tem legendas ou permissões.")

# Rodapé Profissional
st.markdown("""
<br><br><br>
<div style='text-align: center; color: #666; font-size: 12px; padding: 20px; border-top: 1px solid #2d2d30;'>
    <p>© 2026 <b>Alerial</b>. Todos os direitos reservados.</p>
    <p>
        <a href='#' style='color: #888; text-decoration: none;'>Termos de Uso (EULA)</a> | 
        <a href='#' style='color: #888; text-decoration: none;'>Política de Privacidade</a> | 
        <a href='#' style='color: #888; text-decoration: none;'>Suporte</a>
    </p>
    <p style='margin-top: 10px; font-style: italic;'>Desenvolvido para facilitar seus estudos e pesquisas.</p>
</div>
""", unsafe_allow_html=True)
