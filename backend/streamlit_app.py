import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import requests
import re
import os

st.set_page_config(page_title="YT Transcrib API", layout="wide")

st.title("YT Transcrib API 🚀")
st.write("This is a Streamlit-based API for YouTube Transcription to bypass IP blocks.")

# Get query parameters
query_params = st.query_params
url = query_params.get("url", None)
lang = query_params.get("lang", "pt")

def extract_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None

import json

if url:
    video_id = extract_video_id(url)
    if not video_id:
        st.json({"error": "Invalid URL"})
    else:
        # Tentar usar cookies se existirem nos secrets do Streamlit
        cookies_content = st.secrets.get("YOUTUBE_COOKIES", None)
        cookie_file = "cookies.txt"
        if cookies_content:
            with open(cookie_file, "w") as f:
                f.write(cookies_content)
        
        # Headers para disfarce
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.youtube.com/',
        }

        try:
            # 1. Tentar yt-dlp com cookies (Método Blindado)
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
                
                if not subs:
                    raise Exception("No subtitles found")
                
                # Selecionar idioma
                target_lang = None
                priority = [lang, 'pt', 'pt-BR', 'en']
                
                # Tentar match exato e prioridades
                for p in priority:
                    if p in subs:
                        target_lang = p
                        break
                
                if not target_lang:
                    target_lang = list(subs.keys())[0]

                # Pegar URL do JSON3
                sub_tracks = subs[target_lang]
                json3_track = next((t for t in sub_tracks if t.get('ext') == 'json3'), None)
                
                if not json3_track:
                    raise Exception("JSON3 format not found")

                # Baixar legenda
                r = requests.get(json3_track['url'], headers=headers)
                data = r.json()

                # Processar
                transcript = []
                for event in data.get('events', []):
                    if 'segs' not in event: continue
                    text = "".join([s.get('utf8', '') for s in event['segs']]).strip()
                    if not text: continue
                    transcript.append({
                        "text": text,
                        "start": event.get('tStartMs', 0) / 1000.0,
                        "duration": event.get('dDurationMs', 0) / 1000.0
                    })

                full_text = " ".join([t['text'] for t in transcript])
                
                st.json({
                    "video_id": video_id,
                    "transcript": transcript,
                    "full_text": full_text
                })

        except Exception as e:
            st.json({"error": str(e), "detail": "Failed to transcribe"})

else:
    st.write("Pass ?url=YOUTUBE_URL&lang=pt to use the API")
