from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

app = FastAPI()

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str
    language: Optional[str] = None

def extract_video_id(url: str) -> str:
    # Supports standard https://www.youtube.com/watch?v=VIDEO_ID and https://youtu.be/VIDEO_ID
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return ""

@app.get("/")
def read_root():
    return {"message": "YouTube Transcript API is running"}

@app.post("/check-video")
def check_video(request: VideoRequest):
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        languages = []
        for t in transcript_list:
            languages.append({
                "code": t.language_code,
                "name": t.language,
                "is_generated": t.is_generated
            })
            
        return {
            "video_id": video_id,
            "available_languages": languages
        }
    except TranscriptsDisabled:
        raise HTTPException(status_code=400, detail="Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail="No transcript found for this video.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcript")
def get_transcript(request: VideoRequest):
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # 1. Tentar método oficial (mais rápido)
    try:
        api = YouTubeTranscriptApi()
        languages_to_try = [request.language] if request.language else ['pt', 'en']
        transcript_data_objects = api.fetch(video_id, languages=languages_to_try)
        
        transcript = [
            {"text": e.text, "start": e.start, "duration": e.duration}
            for e in transcript_data_objects
        ]
        
        full_text = " ".join([t['text'] for t in transcript])
        return {"video_id": video_id, "transcript": transcript, "full_text": full_text}

    except Exception as e_primary:
        print(f"Primary API failed: {e_primary}. Trying fallback...")
        
        # 2. Fallback com yt-dlp (mais robusto contra bloqueios)
        try:
            import yt_dlp
            import requests

            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(request.url, download=False)
                
                # Procurar legendas
                subs = info.get('automatic_captions') or info.get('subtitles')
                if not subs:
                    raise HTTPException(status_code=404, detail="No transcript found (fallback)")

                # Escolher idioma (pt ou en)
                target_lang = request.language if request.language and request.language in subs else None
                if not target_lang:
                     # Tenta encontrar 'pt', 'pt-orig', 'pt-br', ou 'en'
                    for lang_code in subs.keys():
                        if lang_code.startswith('pt'):
                            target_lang = lang_code
                            break
                    if not target_lang and 'en' in subs:
                        target_lang = 'en'
                    if not target_lang:
                        target_lang = list(subs.keys())[0] # Pega o primeiro que tiver

                # Pegar URL do formato JSON3
                sub_tracks = subs[target_lang]
                json3_track = next((t for t in sub_tracks if t.get('ext') == 'json3'), None)
                
                if not json3_track:
                    # Se não tiver json3, tenta formatar vtt (mais complexo, abortar por enquanto)
                     raise HTTPException(status_code=404, detail="Transcript format not supported in fallback")

                # Baixar o JSON da legenda
                r = requests.get(json3_track['url'])
                r.raise_for_status()
                data = r.json()
                
                # Converter formato JSON3 do Google para o nosso
                transcript = []
                events = data.get('events', [])
                for event in events:
                    segs = event.get('segs', [])
                    if not segs: continue
                    text = "".join([s.get('utf8', '') for s in segs]).strip()
                    if not text: continue
                    
                    start_ms = event.get('tStartMs', 0)
                    duration_ms = event.get('dDurationMs', 0)
                    
                    transcript.append({
                        "text": text,
                        "start": start_ms / 1000.0,
                        "duration": duration_ms / 1000.0
                    })

                full_text = " ".join([t['text'] for t in transcript])
                return {"video_id": video_id, "transcript": transcript, "full_text": full_text}

        except Exception as e_fallback:
             # Se ambos falharem, retorna o erro original ou combinado
             print(f"Fallback failed: {e_fallback}")
             raise HTTPException(status_code=500, detail=f"Failed to retrieve transcript. Primary: {str(e_primary)}. Fallback: {str(e_fallback)}")
