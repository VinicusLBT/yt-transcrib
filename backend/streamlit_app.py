import streamlit as st
import yt_dlp
import requests
import os
import time
import re
from youtube_transcript_api import YouTubeTranscriptApi

# Configuração da Página
st.set_page_config(
    page_title="YT Transcrib",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Meta Tags para tentar forçar o nome no Mobile (Best Effort)
st.markdown("""
    <head>
        <meta name="application-name" content="YT Transcrib">
        <meta name="apple-mobile-web-app-title" content="YT Transcrib">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="mobile-web-app-capable" content="yes">
        <!-- Ícone para Mobile (SVG Data URI) -->
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎙️</text></svg>">
        <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎙️</text></svg>">
    </head>
""", unsafe_allow_html=True)

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

# Função para extrair Video ID do YouTube
def extract_video_id(url):
    """Extrai o ID do vídeo de várias formas de URL do YouTube"""
    if not url:
        return None
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtube\.com\/watch\?.+&v=)([^&\s]+)',
        r'youtu\.be\/([^?\s]+)',
        r'youtube\.com\/embed\/([^?\s]+)',
        r'youtube\.com\/shorts\/([^?\s]+)',
        r'youtube\.com\/v\/([^?\s]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Função para traduzir texto usando Google Translate (via API gratuita)
def translate_text(text, target_lang):
    """Traduz texto usando Google Translate (scraping - gratuito e rápido)"""
    if not text or target_lang == "original":
        return text
    try:
        # Google Translate aceita textos bem maiores - traduz tudo de uma vez
        # Usando a API web do Google Translate (não a paga)
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'auto',  # auto-detect source
            'tl': target_lang,
            'dt': 't',
            'q': text[:5000]  # Limite seguro
        }
        response = requests.get(url, params=params, timeout=10)
        if response.ok:
            result = response.json()
            # Extrair texto traduzido do resultado
            translated_parts = []
            if result and result[0]:
                for part in result[0]:
                    if part[0]:
                        translated_parts.append(part[0])
            translated = ''.join(translated_parts)
            return translated if translated else text
        return text
    except Exception as e:
        # Fallback silencioso para o texto original
        return text

# Título e Cabeçalho
st.title("YT Transcrib 🎙️")
st.write("Transforme vídeos do YouTube em texto em segundos.")

# Input da URL
url = st.text_input("Cole a URL do vídeo aqui:", placeholder="https://www.youtube.com/watch?v=...")

# Preview do Vídeo
video_id = extract_video_id(url)
if video_id:
    st.markdown("📺 **Confirme o vídeo:**")
    st.markdown(f"""
    <div class="video-preview">
        <iframe 
            width="100%" 
            height="315" 
            src="https://www.youtube.com/embed/{video_id}" 
            frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen>
        </iframe>
    </div>
    """, unsafe_allow_html=True)

# Seletor de Idioma da Legenda (pega direto do YouTube - instantâneo!)
lang_options = {
    "🇧🇷 Português": "pt", 
    "🇺🇸 Inglês": "en", 
    "🇪🇸 Espanhol": "es", 
    "🇫🇷 Francês": "fr",
    "🇩🇪 Alemão": "de",
    "🇯🇵 Japonês": "ja",
    "🇰🇷 Coreano": "ko",
    "🇨🇳 Chinês": "zh"
}
selected_lang_name = st.selectbox("Idioma da transcrição:", list(lang_options.keys()))
target_lang = lang_options[selected_lang_name]
st.caption("💡 O YouTube gera legendas automáticas em vários idiomas - super rápido!")

# Botão Transcrever
if st.button("Transcrever Vídeo", use_container_width=True):
    if not url:
        st.warning("⚠️ Por favor, insira uma URL válida.")
    elif not video_id:
        st.warning("⚠️ URL do YouTube inválida. Verifique o link.")
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

                # Variáveis de controle
                success = False
                transcript_text = ""
                full_transcript = []

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    subs = info.get('automatic_captions') or info.get('subtitles')
                    
                    if not subs:
                        raise Exception("Nenhuma legenda encontrada para este vídeo.")
                    
                    # Buscar legenda no idioma escolhido pelo usuário
                    target_sub_lang = None
                    
                    # 1. Tenta exato (ex: "pt" ou "en")
                    if target_lang in subs:
                        target_sub_lang = target_lang
                    
                    # 2. Tenta variações (pt-BR, en-US, etc)
                    if not target_sub_lang:
                        for code in subs.keys():
                            if code.startswith(target_lang):
                                target_sub_lang = code
                                break
                    
                    # 3. Fallback: pega qualquer idioma disponível
                    if not target_sub_lang:
                        fallback_priority = ['pt', 'en', 'es', 'fr']
                        for p in fallback_priority:
                            for code in subs.keys():
                                if code.startswith(p):
                                    target_sub_lang = code
                                    break
                            if target_sub_lang:
                                break
                    
                    if not target_sub_lang:
                        target_sub_lang = list(subs.keys())[0]

                    st.write(f"📝 Obtendo legendas (Base: {target_sub_lang})...")
                    
                    sub_tracks = subs[target_sub_lang]
                    json3_track = next((t for t in sub_tracks if t.get('ext') == 'json3'), None)
                    
                    if not json3_track:
                        # Tenta pegar qualquer formato se json3 falhar
                        json3_track = sub_tracks[0]

                    subtitle_url = json3_track['url']
                    
                    # Se o idioma escolhido for diferente do idioma base, usa tradução nativa do YouTube
                    if target_lang != target_sub_lang.split('-')[0]:
                        subtitle_url += f"&tlang={target_lang}"
                        st.write(f"🌐 Ativando tradução nativa para: {target_lang}...")

                    try:
                         # Variável para controlar se precisamos traduzir manualmente
                        manual_translation_needed = False
                        
                        try:
                            # TENTATIVA 1: Legenda Nativa (pode incluir &tlang=)
                            r = requests.get(subtitle_url, headers=headers, timeout=10)
                            
                            # Se falhou E estavamos tentando traduzir -> Forçar erro
                            if r.status_code != 200 and "&tlang=" in subtitle_url:
                                raise Exception("NATIVE_TRANSLATION_FAILED")
                                
                            # Se falhou mas era original -> Erro grave
                            if r.status_code != 200:
                                 raise Exception("FETCH_FAILED")

                            data = r.json()
                            
                        except Exception as e:
                            # TENTATIVA 2: Fallback para Original + Tradução Manual
                            if "&tlang=" in subtitle_url:
                                try:
                                    st.write("⚠️ Tradução nativa bloqueada. Tentando buscar original e traduzir via Google...")
                                    subtitle_url = json3_track['url'] # URL limpa sem tlang
                                    r = requests.get(subtitle_url, headers=headers, timeout=10)
                                    if r.status_code == 200:
                                        data = r.json()
                                        manual_translation_needed = True 
                                    else:
                                        raise Exception("ORIGINAL_FETCH_FAILED")
                                except:
                                    raise Exception("ALL_REQUESTS_FAILED")
                            else:
                                raise e

                        # Processamento dos dados
                        for event in data.get('events', []):
                            if 'segs' not in event: continue
                            text_seg = "".join([s.get('utf8', '') for s in event['segs']]).strip()
                            if not text_seg: continue
                            start = event.get('tStartMs', 0) / 1000.0
                            timestamp = time.strftime('%H:%M:%S', time.gmtime(start))
                            
                            if manual_translation_needed and target_lang != "original":
                                text_seg = translate_text(text_seg, target_lang)
                                
                            full_transcript.append({'timestamp': timestamp, 'text': text_seg})
                            transcript_text += text_seg + " "
                            
                        success = True

                    except Exception as e_main:

                        # FALLBACK COM YouTubeTranscriptApi
                        try:
                            st.write("📡 Conectando via canais alternativos...")
                            # Tenta pegar a legenda no idioma alvo ou original e traduzir
                            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                            
                            try:
                                # Tenta pegar direto no idioma alvo
                                t_obj = transcript_list.find_transcript([target_lang])
                            except:
                                # Se não tiver, pega o original e traduz via API da biblioteca
                                t_obj = transcript_list.find_generated_transcript(['pt', 'en'])
                                if target_lang != t_obj.language_code:
                                    t_obj = t_obj.translate(target_lang)
                            
                            data = t_obj.fetch()
                            for entry in data:
                                text_seg = entry['text']
                                start = entry['start']
                                timestamp = time.strftime('%H:%M:%S', time.gmtime(start))
                                full_transcript.append({'timestamp': timestamp, 'text': text_seg})
                                transcript_text += text_seg + " "
                            success = True
                        except Exception as inner_e:
                            raise Exception(f"YouTube bloqueou todas as tentativas (Status 429). Tente novamente em alguns minutos ou use outro vídeo.")


                status.update(label="Concluido!", state="complete", expanded=False)
            
            except Exception as e:
                success = False
                error_msg = str(e)
                status.update(label="Erro no processamento", state="error", expanded=False)
                
        # Exibição dos Resultados ou Erros (FORA DO STATUS PARA SEMPRE APARECER)
        if not success and 'error_msg' in locals():
            st.error(f"❌ Ocorreu um erro: {error_msg}")
            st.info("💡 Dica: Verifique se o vídeo tem legendas ou se o link está correto. Algumas lives podem demorar para gerar legendas.")
            
        if success:
            st.success("Transcrição realizada com sucesso!")
            st.caption("Dica: Use o botão de copiar 📄 no canto superior direito do texto.")
            
            import textwrap
            
            tab1, tab2 = st.tabs(["📄 Texto Corrido (Limpo)", "⏱️ Com Timestamps"])
            
            with tab1:
                wrapped_text = textwrap.fill(transcript_text, width=80) 
                st.code(wrapped_text, language="text")
                st.download_button("Baixar Texto (.txt)", data=transcript_text, file_name="transcricao_alerial.txt", use_container_width=True)
            
            with tab2:
                timestamped_text = "\n".join([f"[{e['timestamp']}] {e['text']}" for e in full_transcript])
                st.code(timestamped_text, language="text")
                st.download_button("Baixar com Tempo (.txt)", data=timestamped_text, file_name="transcricao_tempo_alerial.txt", use_container_width=True)

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
