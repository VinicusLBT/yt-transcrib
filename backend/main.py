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

    try:
        api = YouTubeTranscriptApi()
        # The 'fetch' method in this version takes video_id and languages
        # Note: fetch returns the content directly if prioritized correctly
        languages_to_try = [request.language] if request.language else ['pt', 'en']
        
        transcript_data_objects = api.fetch(video_id, languages=languages_to_try)
        
        # Convert objects to dicts for JSON serialization and usage
        transcript = [
            {
                "text": entry.text,
                "start": entry.start,
                "duration": entry.duration
            }
            for entry in transcript_data_objects
        ]
        
        # Formatter
        full_text = " ".join([entry['text'] for entry in transcript])
        
        return {
            "video_id": video_id,
            "transcript": transcript,
            "full_text": full_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
