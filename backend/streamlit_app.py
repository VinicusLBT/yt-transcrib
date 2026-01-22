import streamlit as st
import yt_dlp
import requests
import os
import time
import re
import textwrap
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="YT Transcrib 🎙️",
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

# --- FUNÇÕES UTILITÁRIAS ---

def extract_video_id(url):
    """Extrai o ID do vídeo de várias formas de URL do YouTube"""
    if not url: return None
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtube\.com\/watch\?.+&v=)([^&\s]+)',
        r'youtu\.be\/([^?\s]+)',
        r'youtube\.com\/embed\/([^?\s]+)',
        r'youtube\.com\/shorts\/([^?\s]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return None

def fetch_original_transcript(video_id):
    """
    Baixa APENAS a legenda original.
    Evita pedir tradução ao YouTube para não dar erro 429.
    """
    try:
        # Tenta carregar cookies se existirem
        cookies_content = st.secrets.get("YOUTUBE_COOKIES", None)
        cookie_file = "cookies.txt"
        if cookies_content and not os.path.exists(cookie_file):
            with open(cookie_file, "w") as f: f.write(cookies_content)
            
        c_path = cookie_file if os.path.exists(cookie_file) else None
        
        # Tenta usar o método moderno se disponível
        if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=c_path)
            # Tenta manual (Humana), senão gerada automaticamente
            try:
                transcript = transcript_list.find_manually_created_transcript(['pt', 'en', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh'])
            except:
                transcript = transcript_list.find_generated_transcript(['pt', 'en', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh'])
            return transcript.fetch(), transcript.language_code
        else:
            # Fallback para método antigo/simples
            data = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en', 'es', 'fr'], cookies=c_path)
            return data, "auto"
            
    except Exception as e_main:
        # FALLBACK FINAL: Tenta usar yt-dlp se a biblioteca principal falhar
        try:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'quiet': True,
                'cookiefile': c_path,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                subs = info.get('automatic_captions') or info.get('subtitles')
                if not subs: return None, "No subs found"
                
                # Pega a primeira legenda disponível
                first_lang = next(iter(subs))
                sub_url = subs[first_lang][-1]['url'] # pega json3 ou o ultimo formato
                
                r = requests.get(sub_url)
                if r.status_code == 200:
                    data = r.json()
                    # Normaliza para o formato esperado
                    final_data = []
                    for event in data.get('events', []):
                         if 'segs' in event:
                             text = "".join([s.get('utf8', '') for s in event['segs']]).strip()
                             if text:
                                 final_data.append({'text': text, 'start': event.get('tStartMs', 0)/1000.0})
                    return final_data, first_lang
        except Exception as e_dlp:
            return None, f"Erro Fatal: {str(e_main)} | DLP: {str(e_dlp)}"

def translate_internally(texto_completo, target_lang):
    """
    Traduz o texto no servidor (Client-Side Strategy) usando chunking.
    Evita erros de limite do Google e fornece progresso visual.
    """
    if not texto_completo or target_lang == "original":
        return texto_completo
        
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        
        # Se for curto, traduz direto e rápido
        if len(texto_completo) < 4500:
            return translator.translate(texto_completo)
            
        # SE FOR LONGO: Divide em blocos de 4000 caracteres
        blocos = textwrap.wrap(texto_completo, 4000, break_long_words=False, replace_whitespace=False)
        texto_traduzido = []
        
        progresso_txt = st.empty()
        progresso_bar = st.progress(0)
        
        for i, bloco in enumerate(blocos):
            pct = int(((i + 1) / len(blocos)) * 100)
            progresso_txt.markdown(f"✍️ **Tradução em progresso: {pct}%**")
            progresso_bar.progress((i + 1) / len(blocos))
            
            try:
                # Traduz cada bloco individualmente
                traducao = translator.translate(bloco)
                texto_traduzido.append(traducao)
            except Exception as e:
                # Se falhar um pedaço, mantém o original para não perder informação
                texto_traduzido.append(bloco)
                
        progresso_bar.empty()
        progresso_txt.empty()
        return " ".join(texto_traduzido)
    except Exception as e:
        # Rede de segurança final
        return texto_completo

# --- INTERFACE (FRONTEND) ---

st.title("YT Transcrib 🎙️")
st.write("Transforme vídeos do YouTube em texto em segundos.")

url = st.text_input("Cole a URL do vídeo aqui:", placeholder="https://www.youtube.com/watch?v=...")

# Preview do Vídeo (Direto pelo Streamlit)
video_id = extract_video_id(url)
if video_id:
    st.markdown("📺 **Confirme o vídeo:**")
    st.video(url)

# Opções de Idioma (Para tradução própria)
lang_options = {
    "🇧🇷 Português": "pt", 
    "🇺🇸 Inglês": "en", 
    "🇪🇸 Espanhol": "es", 
    "🇫🇷 Francês": "fr",
    "🇩🇪 Alemão": "de",
    "📄 Manter Original": "original"
}
selected_lang_name = st.selectbox("Traduzir transcrição para:", list(lang_options.keys()))
target_lang = lang_options[selected_lang_name]

# Botão Principal
if st.button("🚀 Transcrever e Traduzir", use_container_width=True, type="primary"):
    if not url or not video_id:
        st.warning("⚠️ Por favor, insira uma URL válida do YouTube.")
    else:
        with st.status("Processando vídeo...", expanded=True) as status:
            try:
                # 1. OBTER LEGENDA ORIGINAL (ESTRATÉGIA ANTI-429)
                st.write("📡 1/2 Baixando legenda original do YouTube...")
                dados_legenda, lang_base = fetch_original_transcript(video_id)
                
                if not dados_legenda:
                    raise Exception(f"Não foi possível obter legendas para este vídeo: {lang_base}")
                
                # Montar texto base e lista com timestamps
                original_full_text = " ".join([item['text'] for item in dados_legenda])
                timestamped_list = []
                for item in dados_legenda:
                    start = item.get('start', 0)
                    ts = time.strftime('%H:%M:%S', time.gmtime(start))
                    timestamped_list.append({'timestamp': ts, 'text': item['text']})
                
                # 2. TRADUÇÃO INTERNA (SE NECESSÁRIA)
                # Verifica se precisa traduzir (se a língua base não for a de destino e não for 'original')
                if target_lang != "original" and not lang_base.startswith(target_lang):
                    st.write(f"🌐 2/2 Traduzindo de '{lang_base}' para '{target_lang}'...")
                    
                    # 2.1 Traduzir o texto corrido
                    transcript_text = translate_internally(original_full_text, target_lang)
                    
                    # 2.2 Traduzir timestamps em lotes (Batch)
                    st.write("⏱️ Ajustando timestamps...")
                    batch_size = 40
                    for i in range(0, len(timestamped_list), batch_size):
                        batch = timestamped_list[i:i+batch_size]
                        combined = " ||| ".join([item['text'] for item in batch])
                        translated_combined = translate_internally(combined, target_lang)
                        translated_list = translated_combined.split("|||")
                        for j, item in enumerate(batch):
                            if j < len(translated_list):
                                item['text'] = translated_list[j].strip()
                else:
                    transcript_text = original_full_text
                    st.write("✅ Usando idioma original disponível.")

                # EXIBIÇÃO DOS RESULTADOS
                status.update(label="Processamento Concluído!", state="complete", expanded=False)
                st.success("Transcriçao realizada com sucesso!")
                
                tab1, tab2 = st.tabs(["📄 Texto Corrido", "⏱️ Com Timestamps"])
                
                with tab1:
                    st.code(transcript_text, language="text")
                    st.download_button("📥 Baixar Texto (.txt)", transcript_text, f"transcricao_{video_id}.txt")
                
                with tab2:
                    timestamped_text = "\n".join([f"[{e['timestamp']}] {e['text']}" for e in timestamped_list])
                    st.code(timestamped_text, language="text")
                    st.download_button("📥 Baixar com Tempo (.txt)", timestamped_text, f"transcricao_tempo_{video_id}.txt")
                    
            except Exception as e:
                status.update(label="Erro detectado", state="error", expanded=True)
                st.error(f"❌ Falha no processo: {str(e)}")
                if "429" in str(e):
                    st.info("💡 Dica: O YouTube está bloqueando muitas requisições. Tente novamente mais tarde ou use um vídeo com legendas manuais.")

# Rodapé
st.markdown("""
<br><hr>
<div style='text-align: center; color: #666; font-size: 12px;'>
    <p>© 2026 <b>Alerial</b> - Inteligência em Transcrição</p>
    <p>Desenvolvido para facilitar seus estudos e pesquisas.</p>
</div>
""", unsafe_allow_html=True)
