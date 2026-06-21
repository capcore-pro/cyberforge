# ============================================
# VIDEO ASSEMBLY — CyberForge
# Assemblage clips + musique via FFmpeg
# ============================================

import asyncio
import logging
import httpx
from pathlib import Path

from utils.ffmpeg_bin import resolve_ffmpeg, resolve_ffprobe

logger = logging.getLogger(__name__)

VIDEOS_DIR = Path("static/videos")
MUSIC_DIR = Path("static/music")
TEMP_DIR = Path("temp/video")


class VideoAssembly:

    def __init__(self):
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────
    # TÉLÉCHARGER UN CLIP DEPUIS URL
    # ─────────────────────────────────────────
    async def download_clip(self, url: str, filename: str) -> Path:
        """Télécharge un clip Kling vers le dossier temp."""

        output_path = TEMP_DIR / filename

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(url)
            output_path.write_bytes(response.content)

        logger.info(f"Downloaded clip: {filename}")
        return output_path

    # ─────────────────────────────────────────
    # ASSEMBLER CLIPS EN VIDÉO FINALE
    # ─────────────────────────────────────────
    async def assemble_clips(
        self,
        project_id: str,
        clip_paths: list[Path],
        music_path: Path = None,
        music_volume: float = 0.3
    ) -> Path:
        """Assemble les clips en vidéo finale avec musique optionnelle."""

        # Créer fichier liste FFmpeg
        list_file = TEMP_DIR / f"{project_id}_list.txt"
        list_content = "\n".join([f"file '{p.absolute()}'" for p in clip_paths])
        list_file.write_text(list_content)

        output_path = VIDEOS_DIR / f"{project_id}_final.mp4"

        if music_path and music_path.exists():
            logger.info("Music file found for assembly: %s", music_path.resolve())
            await self._assemble_with_music(
                list_file, music_path, output_path, music_volume
            )
        else:
            if music_path:
                logger.warning(
                    "Music path provided but file missing: %s — assembly without music",
                    music_path,
                )
            await self._assemble_no_music(list_file, output_path)

        # Nettoyage fichiers temp
        list_file.unlink(missing_ok=True)

        logger.info(f"Assembly done: {output_path}")
        return output_path

    # ─────────────────────────────────────────
    # ASSEMBLAGE SANS MUSIQUE
    # ─────────────────────────────────────────
    async def _assemble_no_music(
        self,
        list_file: Path,
        output_path: Path
    ):
        cmd = [
            resolve_ffmpeg(), "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path)
        ]

        await self._run_ffmpeg(cmd)

    # ─────────────────────────────────────────
    # ASSEMBLAGE AVEC MUSIQUE
    # ─────────────────────────────────────────
    async def _assemble_with_music(
        self,
        list_file: Path,
        music_path: Path,
        output_path: Path,
        music_volume: float
    ):
        if not music_path.exists():
            logger.error("Cannot assemble with music — file not found: %s", music_path)
            raise FileNotFoundError(f"Music file not found: {music_path}")

        logger.info(
            "Assembling with music track %s (volume=%.2f)",
            music_path.resolve(),
            music_volume,
        )

        # Les clips Kling n'ont souvent pas de piste audio — on mappe la musique seule.
        cmd = [
            resolve_ffmpeg(), "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-i", str(music_path),
            "-filter_complex",
            f"[1:a]volume={music_volume}[music]",
            "-map", "0:v",
            "-map", "[music]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_path)
        ]

        await self._run_ffmpeg(cmd)

    # ─────────────────────────────────────────
    # TEXTE OVERLAY (brand + tagline)
    # ─────────────────────────────────────────
    @staticmethod
    def _escape_drawtext(value: str) -> str:
        """Échappe le texte pour le filtre drawtext FFmpeg."""
        return (
            value.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace(":", "\\:")
            .replace("%", "\\%")
        )

    async def add_text_overlay(
        self,
        video_path: Path,
        brand_name: str,
        tagline: str,
        output_path: Path
    ) -> Path:
        """Ajoute texte brand + tagline sur la vidéo finale."""

        font = "C\\:/Windows/Fonts/Arial.ttf"
        safe_brand = self._escape_drawtext(brand_name)
        safe_tagline = self._escape_drawtext(tagline)

        cmd = [
            resolve_ffmpeg(), "-y",
            "-i", str(video_path),
            "-vf",
            (
                f"drawtext=fontfile='{font}'"
                f":text='{safe_brand}'"
                f":fontcolor=white"
                f":fontsize=48"
                f":x=(w-text_w)/2"
                f":y=h-150"
                f":enable='between(t,25,30)'"
                f":alpha='if(lt(t,26),t-25,if(gt(t,29),30-t,1))',"

                f"drawtext=fontfile='{font}'"
                f":text='{safe_tagline}'"
                f":fontcolor=0xCCCCCC"
                f":fontsize=24"
                f":x=(w-text_w)/2"
                f":y=h-100"
                f":enable='between(t,26,30)'"
                f":alpha='if(lt(t,27),t-26,if(gt(t,29),30-t,1))'"
            ),
            "-codec:a", "copy",
            str(output_path)
        ]

        await self._run_ffmpeg(cmd)
        return output_path

    # ─────────────────────────────────────────
    # EXÉCUTER FFMPEG
    # ─────────────────────────────────────────
    async def _run_ffmpeg(self, cmd: list):
        logger.info(f"FFmpeg: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            raise Exception(f"FFmpeg failed: {stderr.decode()[-500:]}")

        logger.info("FFmpeg completed successfully")

    # ─────────────────────────────────────────
    # OBTENIR DURÉE VIDÉO
    # ─────────────────────────────────────────
    async def get_duration(self, video_path: Path) -> float:
        cmd = [
            resolve_ffprobe(), "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(video_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, _ = await process.communicate()

        import json
        data = json.loads(stdout.decode())
        return float(data["format"]["duration"])

    # ─────────────────────────────────────────
    # NETTOYER FICHIERS TEMP PROJET
    # ─────────────────────────────────────────
    async def cleanup_project(self, project_id: str):
        for f in TEMP_DIR.glob(f"*{project_id}*"):
            f.unlink(missing_ok=True)
        logger.info(f"Cleaned temp files for project {project_id}")


# Instance globale
video_assembly = VideoAssembly()
