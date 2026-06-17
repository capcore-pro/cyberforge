"""
Génère des pistes MP3 de test (tons sinusoïdaux) via FFmpeg.

Usage (depuis la racine du dépôt ou backend/) :
    python backend/scripts/download_music.py
"""

import subprocess
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = BACKEND_ROOT / "static/music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

TRACKS = [
    {"filename": "cyberforge-dark-tech.mp3", "freq": "200", "duration": "60"},
    {"filename": "capcore-premium.mp3", "freq": "300", "duration": "60"},
    {"filename": "lumio-soft.mp3", "freq": "400", "duration": "60"},
    {"filename": "vocali-energy.mp3", "freq": "500", "duration": "60"},
]

for track in TRACKS:
    path = MUSIC_DIR / track["filename"]
    if path.exists():
        print(f"Already exists: {track['filename']}")
        continue
    print(f"Generating: {track['filename']}...")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={track['freq']}:duration={track['duration']}",
            "-q:a",
            "9",
            str(path),
        ],
        check=True,
    )
    print(f"Done: {track['filename']}")

print("All tracks ready.")
