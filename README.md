# 🎬 Sistema de Generación de Assets para Videos YouTube

## 📁 Nueva Estructura de Carpetas

```
shorts-python/
├── 📁 projects/                    # Carpeta raíz de proyectos
│   └── 📁 [nombre_proyecto]/      # Cada proyecto tiene su carpeta
│       ├── 📁 assets/             # Assets generados
│       │   ├── 📁 audio/          # Archivos de audio (MP3/WAV)
│       │   ├── 📁 images/         # Imágenes descargadas
│       │   └── 📁 subtitles/      # Archivos SRT
│       └── 📁 temp/               # Archivos temporales
├── 📄 video.json                  # Configuración del video
├── 📄 guion.txt                   # Script del video
├── 📄 main.py                     # Archivo principal mejorado
├── 📄 audio_pro.py                # Generador de audio TTS
├── 📄 images_pro.py               # Descargador de imágenes (mejorado)
├── 📄 subtitle_pro.py             # Transcriptor de audio (mejorado)
└── 📄 .env                        # Variables de entorno
```

## 🚀 Mejoras Implementadas

### ✅ **Ejecución en Paralelo**
- Proceso 1: Descarga de imágenes (independiente)
- Proceso 2.1: Generación de audio TTS
- Proceso 2.2: Generación de subtítulos (depende del audio)

### ✅ **Mejor Organización**
- Estructura de carpetas consistente
- Configuración centralizada
- Manejo de errores robusto
- Logging detallado

### ✅ **Funcionalidades Nuevas**
- Validación de configuración
- Limpieza automática de archivos temporales
- Estadísticas detalladas
- Fallback a ejecución secuencial
- Soporte para múltiples formatos de imagen

---

## 📋 Configuración

### 1. Variables de Entorno (.env)
```bash
# APIs para descarga de imágenes
UNSPLASH_KEY=tu_clave_unsplash
PEXELS_KEY=tu_clave_pexels  
PIXABAY_KEY=tu_clave_pixabay
SERPAPI_KEY=tu_clave_serpapi
```

### 2. Configuración de Video (video.json)
```json
{
  "title": "El día que Einstein rechazó ser presidente de Israel",
  "description": "Historia fascinante sobre Einstein y la política",
  "keywords": ["ciencia", "historia", "einstein"],
  "google_keywords": [
    "albert einstein",
    "israel presidencia",
    "relatividad", 
    "fisica teorica",
    "nobel fisica"
  ],
  "duration_target": 60,
  "vertical_format": true
}
```

### 3. Script del Video (guion.txt)
```
El 17 de noviembre de 1952, algo extraordinario sucedió...

[Tu script completo aquí]
```

---

## 🛠️ Instalación y Uso

### 1. **Instalar Dependencias**
```bash
pip install -r requirements.txt

# Instalar ffmpeg (necesario para audio)
# Windows: choco install ffmpeg
# macOS: brew install ffmpeg  
# Linux: sudo apt install ffmpeg
```

### 2. **Configurar APIs** 
- Crea cuenta en [Unsplash](https://unsplash.com/developers)
- Crea cuenta en [Pexels](https://www.pexels.com/api/)
- Crea cuenta en [Pixabay](https://pixabay.com/api/docs/)
- Crea cuenta en [SerpAPI](https://serpapi.com/) (para Google Images)

### 3. **Ejecutar Sistema**
```bash
python main.py
```

---

## 📊 Salida del Sistema

### **Proceso Exitoso:**
```
🎬 SISTEMA DE GENERACIÓN DE ASSETS PARA VIDEOS v2.0
============================================================
📋 Configuración cargada: El día que Einstein rechazó ser presidente de Israel
🚀 Iniciando generación de assets en paralelo...

🖼️ Iniciando descarga de imágenes...
📸 Unsplash: 3 imágenes encontradas para 'einstein'
✅ Guardada → einstein_unsplash_01.jpg

🎙️ Iniciando generación de audio...
🎵 Generando fragmento: fragment_001.wav
✅ Audio generado: Einstein_audio.mp3 (2.3 MB)

📝 Iniciando generación de subtítulos...
✅ Subtítulos generados

⏱️ Generación completada en 45.2 segundos

==================================================
📊 RESUMEN DE GENERACIÓN DE ASSETS
==================================================
📁 Proyecto: El día que Einstein rechazó ser presidente de Israel
📂 Directorio: projects/El_día_que_Einstein_rechazó_ser_presidente_de_Israel

🖼️ Imágenes: ✅ Completado
🎙️ Audio: ✅ Completado  
📝 Subtítulos: ✅ Completado

🎵 Audio generado: Einstein_audio.mp3 (2.3 MB)
🖼️ Imágenes descargadas: 24
🎯 Procesos exitosos: 3/3
🎉 ¡Todos los assets generados correctamente!
```

---

## ⚙️ Configuraciones Avanzadas

### **Personalizar TTS:**
```python
config_tts = TTSConfig(
    voice_model=VoiceModel.ES_CSS10,    # o ES_MAI
    remove_silence=True,                # Eliminar silencios
    silence_threshold=-40.0,            # Umbral de silencio (dB)
    min_silence_duration=0.8,           # Duración mínima de silencio
    keep_temp_files=False,              # No guardar temporales
    verbose=True                        # Logging detallado
)
```

### **Personalizar Descarga de Imágenes:**
```python
downloader = ImageDownloader(
    images_per_keyword=5,               # Imágenes por keyword
    images_per_keyword_google=8,        # Imágenes de Google
    use_unsplash=True,                  # Usar Unsplash
    use_pexels=True,                    # Usar Pexels  
    use_pixabay=True,                   # Usar Pixabay
    use_google=True,                    # Usar Google Images
    max_workers=4,                      # Descargas paralelas
    verbose=True                        # Logging detallado
)
```

### **Personalizar Transcripción:**
```python
transcriber = AudioTranscriber(
    model_name="medium",                # tiny, base, small, medium, large
    language="es",                      # Idioma
    device="cuda",                      # "cpu", "cuda", None
    verbose=True                        # Logging detallado
)
```

---

## 🔧 Solución de Problemas

### **Error: "tts command not found"**
```bash
pip install TTS
```

### **Error: "ffmpeg not found"**
- Windows: `choco install ffmpeg`
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### **Error: "CUDA out of memory"**
```python
# Usar CPU para Whisper
transcriber = AudioTranscriber(device="cpu")
```

### **Error: "API key invalid"**
- Verificar claves en `.env`
- Verificar límites de API
- Verificar que las claves tienen permisos

### **Archivos de salida vacíos**
- Verificar permisos de escritura
- Verificar espacio en disco
- Revisar logs para errores específicos