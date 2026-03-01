# IsabelaOS Avatar Trainer (SDXL LoRA)

Este repo contiene el worker de RunPod para entrenar LoRA (SDXL) con 5+ fotos.

## Inputs
action: "avatar_train"
avatar_id, user_id, trigger, photos[]

photos[] = paths dentro del bucket (ej: avatars/user/avt/photos/1.jpg)

## Output
Devuelve lora_bucket_path para que el generador lo use.
Opcionalmente borra las fotos de training al finalizar.
