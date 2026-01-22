from youtube_transcript_api import YouTubeTranscriptApi

print("Instantiating API...")
try:
    api = YouTubeTranscriptApi()
    print("API methods:", dir(api))
    
    print("Trying list for 'jNQXAC9IVRw'...")
    ts = api.list("jNQXAC9IVRw")
    print("List result:", ts)
    
    # print("Trying fetch...")
    # trans = api.fetch("jNQXAC9IVRw")
    # print("Fetch result (len):", len(trans))
    
except Exception as e:
    print("Error:", e)
