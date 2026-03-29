#!/usr/bin/env python3
# handler.py
# ─────────────────────────────────────────────────────────────
# RunPod Serverless Worker — Ensamble de Comerciales IsabelaOS
#
# Recibe por cada job:
#   - scenes: lista de { video_b64, audio_b64, duration_seconds }
#   - title: nombre del comercial
#   - transition: tipo de transición (fade, cut, zoom)
#   - output_format: "mp4" (default)
#
# Proceso:
#   1. Decodifica cada clip (video base64) y audio (base64)
#   2. Mezcla audio sobre cada clip con FFmpeg
#   3. Concatena todos los clips con transiciones
#   4. Devuelve el video final en base64
#
# Transiciones disponibles:
#   - cut: corte limpio directo (más profesional para comerciales rápidos)
#   - fade: fade to black entre escenas (más cinematográfico)
#   - dissolve: cross-dissolve suave entre escenas
# ─────────────────────────────────────────────────────────────
 
import runpod
import base64
import os
import json
import subprocess
import tempfile
import shutil
import traceback
from pathlib import Path
 
 
# ── Utilidades ────────────────────────────────────────────────
 
def b64_to_file(b64_string: str, filepath: str) -> bool:
    """Decodifica base64 y lo escribe en disco."""
    try:
        data = base64.b64decode(b64_string)
        with open(filepath, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"[handler] Error decodificando base64 → {filepath}: {e}")
        return False
 
 
def file_to_b64(filepath: str) -> str:
    """Lee un archivo y lo devuelve como base64."""
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
 
 
def run_ffmpeg(cmd: list, label: str = "") -> tuple[bool, str]:
    """Ejecuta un comando FFmpeg y devuelve (ok, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos máximo por operación
        )
        if result.returncode != 0:
            print(f"[ffmpeg:{label}] ERROR:\n{result.stderr[-1000:]}")
            return False, result.stderr
        print(f"[ffmpeg:{label}] OK")
        return True, result.stderr
    except subprocess.TimeoutExpired:
        return False, "FFmpeg timeout (>5 min)"
    except Exception as e:
        return False, str(e)
 
 
# ── Paso 1: Mezclar audio sobre video de cada escena ─────────
 
def mix_audio_on_clip(video_path: str, audio_path: str, output_path: str, duration: float) -> bool:
    """
    Toma un clip de video (sin audio o con audio mudo) y le agrega
    la narración en off. Si el audio es más corto que el video, silencio
    al final. Si es más largo, se recorta al duration del video.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",           # video del clip
        "-map", "1:a:0",           # audio de la narración
        "-c:v", "copy",            # no re-encodear video
        "-c:a", "aac",             # encodear audio a AAC
        "-b:a", "192k",
        "-shortest",               # terminar cuando el más corto acabe
        "-t", str(duration),       # limitar a la duración de la escena
        output_path
    ]
    ok, _ = run_ffmpeg(cmd, f"mix_audio:{Path(output_path).stem}")
    return ok
 
 
def add_silent_audio(video_path: str, output_path: str, duration: float) -> bool:
    """Agrega pista de audio silencioso a un clip sin audio."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-t", str(duration),
        output_path
    ]
    ok, _ = run_ffmpeg(cmd, f"silent_audio:{Path(output_path).stem}")
    return ok
 
 
# ── Paso 2: Normalizar todos los clips al mismo formato ───────
 
def normalize_clip(input_path: str, output_path: str) -> bool:
    """
    Normaliza un clip a:
    - Resolución: 1080x1920 (9:16 vertical)
    - FPS: 24
    - Codec: H.264 (yuv420p para compatibilidad máxima)
    - Audio: AAC 44100Hz stereo
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
        "-r", "24",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",              # calidad alta
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", "192k",
        output_path
    ]
    ok, _ = run_ffmpeg(cmd, f"normalize:{Path(output_path).stem}")
    return ok
 
 
# ── Paso 3: Concatenar clips con transiciones ─────────────────
 
def concat_with_cut(clip_paths: list, output_path: str) -> bool:
    """Concatenación directa (cut limpio) — más rápido y profesional."""
    # Crear archivo de lista para concat
    list_file = output_path.replace(".mp4", "_list.txt")
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")
 
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ]
    ok, _ = run_ffmpeg(cmd, "concat_cut")
    if os.path.exists(list_file):
        os.remove(list_file)
    return ok
 
 
def concat_with_fade(clip_paths: list, output_path: str, fade_duration: float = 0.5) -> bool:
    """
    Concatenación con fade to black entre escenas.
    Más cinematográfico para comerciales emocionales.
    """
    if len(clip_paths) == 1:
        shutil.copy(clip_paths[0], output_path)
        return True
 
    # Construir filtergraph de xfade para cada par de clips
    # Primero obtener duración de cada clip
    durations = []
    for p in clip_paths:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", p],
            capture_output=True, text=True
        )
        try:
            durations.append(float(probe.stdout.strip()))
        except:
            durations.append(8.0)  # fallback
 
    # Construir inputs
    inputs = []
    for p in clip_paths:
        inputs += ["-i", p]
 
    # Construir filtergraph con xfade
    # Video: encadenar xfade entre clips consecutivos
    video_filters = []
    audio_filters = []
    offset = 0.0
 
    for i in range(len(clip_paths) - 1):
        offset += durations[i] - fade_duration
        if i == 0:
            v_in_a = f"[0:v]"
            v_in_b = f"[1:v]"
            a_in_a = f"[0:a]"
            a_in_b = f"[1:a]"
        else:
            v_in_a = f"[vx{i-1}]"
            v_in_b = f"[{i+1}:v]"
            a_in_a = f"[ax{i-1}]"
            a_in_b = f"[{i+1}:a]"
 
        v_out = f"[vx{i}]" if i < len(clip_paths) - 2 else "[vout]"
        a_out = f"[ax{i}]" if i < len(clip_paths) - 2 else "[aout]"
 
        video_filters.append(
            f"{v_in_a}{v_in_b}xfade=transition=fade:duration={fade_duration}:offset={offset:.3f}{v_out}"
        )
        audio_filters.append(
            f"{a_in_a}{a_in_b}acrossfade=d={fade_duration}{a_out}"
        )
 
    filtergraph = ";".join(video_filters + audio_filters)
 
    cmd = inputs + [
        "-y",
        "-filter_complex", filtergraph,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-ar", "44100",
        "-ac", "2",
        output_path
    ]
    cmd = ["ffmpeg"] + cmd
    ok, _ = run_ffmpeg(cmd, "concat_fade")
    return ok
 
 
def concat_with_dissolve(clip_paths: list, output_path: str) -> bool:
    """Cross-dissolve entre escenas — más suave que fade."""
    return concat_with_fade(clip_paths, output_path, fade_duration=0.4)
 
 
# ── Handler principal ─────────────────────────────────────────
 
def handler(job):
    """
    Job input esperado:
    {
        "scenes": [
            {
                "scene_number": 1,
                "video_b64": "base64...",   // video mp4 en base64
                "audio_b64": "base64...",   // audio mp3/aac en base64 (opcional)
                "duration_seconds": 8
            },
            ...
        ],
        "title": "Mi Comercial",
        "transition": "fade",   // "cut" | "fade" | "dissolve"
        "output_format": "mp4"  // solo mp4 por ahora
    }
 
    Respuesta:
    {
        "ok": true,
        "video_b64": "base64...",   // video final ensamblado
        "duration_total": 32.0,
        "scenes_count": 4,
        "title": "Mi Comercial"
    }
    """
    job_id    = job.get("id", "unknown")
    job_input = job.get("input", {})
 
    print(f"[handler] Job {job_id} iniciado")
 
    scenes     = job_input.get("scenes", [])
    title      = job_input.get("title", "comercial")
    transition = job_input.get("transition", "fade").lower()
 
    if not scenes:
        return {"ok": False, "error": "MISSING_SCENES", "detail": "Se requiere al menos una escena."}
 
    # Crear directorio temporal para este job
    workdir = tempfile.mkdtemp(prefix=f"comercial_{job_id}_")
    print(f"[handler] Workdir: {workdir}")
 
    try:
        prepared_clips = []  # clips listos para concatenar
 
        # ── Procesar cada escena ──────────────────────────────
        for i, scene in enumerate(scenes):
            scene_num   = scene.get("scene_number", i + 1)
            video_b64   = scene.get("video_b64")
            audio_b64   = scene.get("audio_b64")
            duration    = float(scene.get("duration_seconds", 8))
 
            print(f"[handler] Procesando escena {scene_num}/{len(scenes)}")
 
            if not video_b64:
                print(f"[handler] Escena {scene_num} sin video — saltando")
                continue
 
            # 1. Escribir video raw en disco
            raw_video = os.path.join(workdir, f"scene_{scene_num:02d}_raw.mp4")
            if not b64_to_file(video_b64, raw_video):
                print(f"[handler] Error decodificando video escena {scene_num}")
                continue
 
            # 2. Mezclar audio si existe
            video_with_audio = os.path.join(workdir, f"scene_{scene_num:02d}_audio.mp4")
            if audio_b64:
                raw_audio = os.path.join(workdir, f"scene_{scene_num:02d}_audio.mp3")
                if b64_to_file(audio_b64, raw_audio):
                    ok = mix_audio_on_clip(raw_video, raw_audio, video_with_audio, duration)
                    if not ok:
                        # fallback: usar video sin audio
                        print(f"[handler] Falló mezcla audio escena {scene_num}, usando video sin audio")
                        ok = add_silent_audio(raw_video, video_with_audio, duration)
                else:
                    ok = add_silent_audio(raw_video, video_with_audio, duration)
            else:
                # Sin audio: agregar silencio para que todos tengan pista de audio
                ok = add_silent_audio(raw_video, video_with_audio, duration)
 
            if not ok or not os.path.exists(video_with_audio):
                print(f"[handler] Error en escena {scene_num} — saltando")
                continue
 
            # 3. Normalizar al formato estándar (1080x1920, 24fps, H.264)
            normalized = os.path.join(workdir, f"scene_{scene_num:02d}_norm.mp4")
            ok = normalize_clip(video_with_audio, normalized)
            if not ok or not os.path.exists(normalized):
                print(f"[handler] Error normalizando escena {scene_num} — saltando")
                continue
 
            prepared_clips.append(normalized)
            print(f"[handler] ✅ Escena {scene_num} lista")
 
        if not prepared_clips:
            return {"ok": False, "error": "NO_CLIPS_PREPARED", "detail": "Ninguna escena pudo procesarse."}
 
        print(f"[handler] {len(prepared_clips)}/{len(scenes)} clips listos — aplicando transición: {transition}")
 
        # ── Ensamblar video final ─────────────────────────────
        final_path = os.path.join(workdir, "comercial_final.mp4")
 
        if transition == "cut" or len(prepared_clips) == 1:
            ok = concat_with_cut(prepared_clips, final_path)
        elif transition == "dissolve":
            ok = concat_with_dissolve(prepared_clips, final_path)
        else:
            # Default: fade
            ok = concat_with_fade(prepared_clips, final_path)
 
        if not ok or not os.path.exists(final_path):
            # Fallback a cut si falla la transición elegida
            print("[handler] Transición falló — intentando cut como fallback")
            ok = concat_with_cut(prepared_clips, final_path)
 
        if not ok or not os.path.exists(final_path):
            return {"ok": False, "error": "ASSEMBLY_FAILED", "detail": "No se pudo ensamblar el video final."}
 
        # ── Obtener duración total del video final ────────────
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", final_path],
            capture_output=True, text=True
        )
        try:
            total_duration = float(probe.stdout.strip())
        except:
            total_duration = len(prepared_clips) * 8.0
 
        # ── Convertir resultado a base64 ──────────────────────
        print(f"[handler] Convirtiendo video final a base64...")
        video_b64_out = file_to_b64(final_path)
 
        print(f"[handler] ✅ Job {job_id} completado — {len(prepared_clips)} escenas, {total_duration:.1f}s")
 
        return {
            "ok":             True,
            "video_b64":      video_b64_out,
            "video_mime":     "video/mp4",
            "duration_total": total_duration,
            "scenes_count":   len(prepared_clips),
            "title":          title,
            "transition":     transition,
        }
 
    except Exception as e:
        print(f"[handler] EXCEPTION: {traceback.format_exc()}")
        return {"ok": False, "error": "SERVER_ERROR", "detail": str(e)}
 
    finally:
        # Limpiar archivos temporales
        try:
            shutil.rmtree(workdir, ignore_errors=True)
            print(f"[handler] Workdir limpiado: {workdir}")
        except:
            pass
 
 
# ── Punto de entrada RunPod ───────────────────────────────────
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
