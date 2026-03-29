# IsabelaOS — Comercial Assembler Worker

Worker de RunPod Serverless para ensamble de comerciales de video con FFmpeg.

## Qué hace

Recibe los clips individuales de video (generados por Veo3) y los audios de narración (generados por ElevenLabs) y los ensambla en un **único video final profesional** con transiciones.

## Input esperado

```json
{
  "scenes": [
    {
      "scene_number": 1,
      "video_b64": "base64_del_video_mp4",
      "audio_b64": "base64_del_audio_mp3",
      "duration_seconds": 8
    },
    {
      "scene_number": 2,
      "video_b64": "base64_del_video_mp4",
      "audio_b64": "base64_del_audio_mp3",
      "duration_seconds": 8
    }
  ],
  "title": "Mi Comercial",
  "transition": "fade",
  "output_format": "mp4"
}
```

### Transiciones disponibles

| Valor | Descripción |
|-------|-------------|
| `cut` | Corte directo — más rápido, comerciales energéticos |
| `fade` | Fade to black — cinematográfico, emocional (default) |
| `dissolve` | Cross-dissolve suave — elegante, lifestyle |

## Output

```json
{
  "ok": true,
  "video_b64": "base64_video_final_mp4",
  "video_mime": "video/mp4",
  "duration_total": 32.0,
  "scenes_count": 4,
  "title": "Mi Comercial",
  "transition": "fade"
}
```

## Especificaciones del video final

- **Resolución:** 1080×1920 (9:16 vertical — Reels, TikTok, Stories)
- **FPS:** 24
- **Codec video:** H.264 (yuv420p, compatible con todas las plataformas)
- **Codec audio:** AAC 192kbps stereo 44100Hz
- **Calidad:** CRF 22 (alta calidad, archivo razonable)

## Configuración en RunPod

1. Conectar este repo al endpoint `isabelaos-avatar-trainer`
2. GPU: cualquiera (el worker es CPU-only, la GPU no se usa)
3. Timeout recomendado: 600s (10 minutos)
4. Workers mínimos: 0 (escala desde cero)

## Variables de entorno requeridas

Ninguna — el worker es autónomo.

## Stack

- Python 3.11
- FFmpeg (instalado en la imagen Docker)
- runpod SDK 1.7.3
