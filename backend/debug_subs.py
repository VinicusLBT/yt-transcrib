import yt_dlp
import json

url = "https://www.youtube.com/watch?v=4DC77TWi49E"
ydl_opts = {
    'skip_download': True,
    'writesubtitles': True,
    'writeautomaticsub': True,
    'quiet': True,
    'no_warnings': True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    subs = info.get('automatic_captions') or info.get('subtitles')
    print(json.dumps(list(subs.keys()) if subs else None))
    # Print the first 2 entries for 'pt' or whatever is found
    target = 'pt'
    if subs and target in subs:
        print(f"Subtitles for {target}:")
        print(json.dumps(subs[target][:2], indent=2))
