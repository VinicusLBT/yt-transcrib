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

    # Headers que simulam um navegador real para evitar bloqueios de IP
    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.youtube.com/',
    }

    # 1. Tentar método oficial (com headers injetados se possível pela lib)
    try:
        # A lib youtube-transcript-api infelizmente não permite passar headers customizados facilmente
        # sem mexer no core, mas vamos tentar o básico primeiro.
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
        print(f"Primary API failed: {e_primary}. Trying advanced fallback...")
        
        # 2. Fallback com yt-dlp e headers de navegador
        try:
            import yt_dlp
            import requests

            # Configurações do yt-dlp para parecer um navegador
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'quiet': True,
                'no_warnings': True,
                'user_agent': browser_headers['User-Agent'],
                'referer': browser_headers['Referer'],
                'nocheckcertificate': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Tenta extrair info com headers de navegador
                info = ydl.extract_info(request.url, download=False)
                
                subs = info.get('automatic_captions') or info.get('subtitles')
                if not subs:
                    raise HTTPException(status_code=404, detail="Legendas não encontradas no YouTube (Fallback)")

                # Lógica de seleção de idioma aprimorada
                target_lang = request.language if request.language and request.language in subs else None
                if not target_lang:
                    # Prioridade: pt > en > qualquer um
                    priority = ['pt', 'pt-BR', 'pt-PT', 'en']
                    for p in priority:
                        if p in subs:
                            target_lang = p
                            break
                    if not target_lang:
                        target_lang = list(subs.keys())[0]

                # Pegar URL do formato JSON3
                sub_tracks = subs[target_lang]
                json3_track = next((t for t in sub_tracks if t.get('ext') == 'json3'), None)
                
                if not json3_track:
                     raise HTTPException(status_code=404, detail="Formato JSON3 não disponível")

                # Baixar o JSON da legenda usando os mesmos headers de navegador
                session = requests.Session()
                r = session.get(json3_track['url'], headers=browser_headers, timeout=10)
                r.raise_for_status()
                data = r.json()
                
                transcript = []
                # Formato JSON3 do YouTube (Google)
                for event in data.get('events', []):
                    if 'segs' not in event: continue
                    text = "".join([s.get('utf8', '') for s in event['segs']]).strip()
                    if not text: continue
                    
                    transcript.append({
                        "text": text,
                        "start": event.get('tStartMs', 0) / 1000.0,
                        "duration": event.get('dDurationMs', 0) / 1000.0
                    })

                if not transcript:
                    raise HTTPException(status_code=404, detail="Legenda vazia ou sem eventos")

                full_text = " ".join([t['text'] for t in transcript])
                return {"video_id": video_id, "transcript": transcript, "full_text": full_text}

        except Exception as e_fallback:
             print(f"Fallback failed: {e_fallback}")
             # Mensagem amigável para o usuário sobre o bloqueio de IP
             detail_msg = "O YouTube bloqueou o acesso vindo deste servidor cloud (Render/AWS)."
             if "429" in str(e_fallback):
                 detail_msg += " Erro 429: Muitas requisições detectadas pelo YouTube."
             
             raise HTTPException(status_code=500, detail=f"{detail_msg} Detalhes: {str(e_fallback)}")

