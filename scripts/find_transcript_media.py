import json
import os

transcript_path = os.path.expanduser(r"C:\Users\samsung\.gemini\antigravity\brain\479daf75-25e8-4af0-af9b-4526d452b933\.system_generated\logs\transcript.jsonl")

if os.path.exists(transcript_path):
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if data.get('type') == 'USER_INPUT':
                media = data.get('media', [])
                print(f"Total media items in USER_INPUT: {len(media)}")
                for i, m in enumerate(media[:10]):
                    print(f"Media {i+1}: uri={m.get('uri')}")
else:
    print("Transcript not found at", transcript_path)
