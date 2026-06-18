"""
Télécharge les pistes musicales (archive.org) avec repli FFmpeg si échec.

Usage (depuis la racine du dépôt ou backend/) :
    python backend/scripts/download_music.py
"""

import subprocess
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = BACKEND_ROOT / "static/music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

TRACKS = [
    {
        "filename": "cyberforge-dark-tech.mp3",
        "url": "https://archive.org/download/electronic-dark-ambient/dark-tech-loop.mp3",
        "fallback": True,
        "freq": "200",
    },
    {
        "filename": "capcore-premium.mp3",
        "url": "https://archive.org/download/corporate-background/corporate-loop.mp3",
        "fallback": True,
        "freq": "300",
    },
    {
        "filename": "lumio-soft.mp3",
        "url": "https://archive.org/download/soft-ambient/soft-ambient-loop.mp3",
        "fallback": True,
        "freq": "400",
    },
    {
        "filename": "vocali-energy.mp3",
        "url": "https://archive.org/download/energetic-electronic/energy-loop.mp3",
        "fallback": True,
        "freq": "500",
    },
]


def generate_fallback(filename: str, freq: str, duration: int = 60) -> None:
    """Génère un ton de secours si le téléchargement échoue."""
    path = MUSIC_DIR / filename
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            (
                f"aevalsrc=sin(2*PI*{freq}*t)*0.3|sin(2*PI*{freq}*1.5*t)*0.2:"
                f"s=44100:c=stereo"
            ),
            "-t",
            str(duration),
            "-q:a",
            "4",
            str(path),
        ],
        check=True,
    )


def download_track(url: str, path: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CyberForge-MusicDownloader/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    if len(data) < 1024:
        raise ValueError("Fichier trop petit — probablement une page d'erreur")
    path.write_bytes(data)


def main() -> None:
    for track in TRACKS:
        path = MUSIC_DIR / track["filename"]
        if path.exists():
            print(f"Already exists: {track['filename']}")
            continue

        print(f"Downloading: {track['filename']}...")
        try:
            download_track(track["url"], path)
            print(f"Done: {track['filename']}")
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as exc:
            print(f"Download failed for {track['filename']}: {exc}")
            if track.get("fallback"):
                print(f"Fallback FFmpeg: {track['filename']}...")
                generate_fallback(track["filename"], track["freq"])
                print(f"Fallback done: {track['filename']}")
            else:
                raise

    print("All tracks ready.")


if __name__ == "__main__":
    main()
