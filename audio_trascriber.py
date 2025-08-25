import os
import whisper
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple


class AudioTranscriber:
    """
    Transcriptor de audio mejorado con mejor manejo de errores y configuración
    Incluye opciones para generar subtítulos en frases más pequeñas
    """
    
    def __init__(
        self,
        audio_dir: str = "audios",
        output_dir: str = "subtitles", 
        model_name: str = "small",
        language: str = "es",
        verbose: bool = True,
        device: Optional[str] = None,  # "cpu", "cuda", o None para auto-detectar
        # Nuevas opciones para fragmentación
        max_words_per_subtitle: int = 8,
        max_chars_per_subtitle: int = 50,
        min_duration_per_subtitle: float = 0.5,
        max_duration_per_subtitle: float = 4.0,
        fragment_subtitles: bool = True
    ):
        self.audio_dir = Path(audio_dir)
        self.output_dir = Path(output_dir)
        self.model_name = model_name
        self.language = language
        self.device = device
        
        # Configuración de fragmentación
        self.max_words_per_subtitle = max_words_per_subtitle
        self.max_chars_per_subtitle = max_chars_per_subtitle
        self.min_duration_per_subtitle = min_duration_per_subtitle
        self.max_duration_per_subtitle = max_duration_per_subtitle
        self.fragment_subtitles = fragment_subtitles
        
        # Logger
        self.logger = self._setup_logger(verbose)
        
        # Crear carpeta de salida si no existe
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar modelo Whisper
        self._load_model()
        
        # Extensiones de audio soportadas
        self.supported_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}

    def _setup_logger(self, verbose: bool) -> logging.Logger:
        """Configura el logger"""
        logger = logging.getLogger("AudioTranscriber")
        logger.setLevel(logging.INFO if verbose else logging.WARNING)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger

    def _load_model(self):
        """Carga el modelo Whisper con manejo de errores"""
        try:
            self.logger.info(f"🔄 Cargando modelo Whisper '{self.model_name}'...")
            
            # Especificar device si se proporcionó
            if self.device:
                self.model = whisper.load_model(self.model_name, device=self.device)
                self.logger.info(f"✅ Modelo cargado en {self.device}")
            else:
                self.model = whisper.load_model(self.model_name)
                self.logger.info(f"✅ Modelo '{self.model_name}' cargado correctamente")
                
        except Exception as e:
            self.logger.error(f"❌ Error cargando modelo Whisper: {e}")
            raise

    def _format_timestamp(self, seconds: float) -> str:
        """Convierte segundos en formato SRT: HH:MM:SS,MS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def _split_text_smart(self, text: str, max_words: int, max_chars: int) -> List[str]:
        """
        Divide el texto en fragmentos más pequeños de manera inteligente
        Respeta puntuación y estructura de oraciones
        """
        if not text.strip():
            return []
        
        text = text.strip()
        
        # Si el texto ya es lo suficientemente corto, devolverlo como está
        words = text.split()
        if len(words) <= max_words and len(text) <= max_chars:
            return [text]
        
        fragments = []
        
        # Dividir por oraciones primero (puntos, signos de interrogación, exclamación)
        sentences = re.split(r'[.!?]+', text)
        
        current_fragment = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Si agregar esta oración excede los límites, guardar fragmento actual
            test_fragment = f"{current_fragment} {sentence}".strip()
            test_words = len(test_fragment.split())
            
            if (test_words > max_words or len(test_fragment) > max_chars) and current_fragment:
                fragments.append(current_fragment)
                current_fragment = sentence
            else:
                current_fragment = test_fragment
        
        # Agregar último fragmento
        if current_fragment:
            fragments.append(current_fragment)
        
        # Si aún hay fragmentos muy largos, dividir por palabras
        final_fragments = []
        for fragment in fragments:
            if len(fragment.split()) <= max_words and len(fragment) <= max_chars:
                final_fragments.append(fragment)
            else:
                # Dividir por palabras manteniendo coherencia
                words = fragment.split()
                current = []
                
                for word in words:
                    test_fragment = " ".join(current + [word])
                    
                    if len(current) >= max_words or len(test_fragment) > max_chars:
                        if current:
                            final_fragments.append(" ".join(current))
                            current = [word]
                        else:
                            # Palabra individual muy larga
                            final_fragments.append(word)
                    else:
                        current.append(word)
                
                if current:
                    final_fragments.append(" ".join(current))
        
        return [f.strip() for f in final_fragments if f.strip()]

    def _create_subtitle_fragments(self, segment: Dict) -> List[Dict]:
        """
        Crea fragmentos de subtítulos más pequeños a partir de un segmento de Whisper
        """
        text = segment["text"].strip()
        start_time = segment["start"]
        end_time = segment["end"]
        total_duration = end_time - start_time
        
        if not self.fragment_subtitles:
            return [segment]
        
        # Dividir texto en fragmentos
        text_fragments = self._split_text_smart(
            text, 
            self.max_words_per_subtitle, 
            self.max_chars_per_subtitle
        )
        
        if len(text_fragments) <= 1:
            return [segment]
        
        # Distribuir tiempo entre fragmentos
        fragments = []
        fragment_count = len(text_fragments)
        
        for i, fragment_text in enumerate(text_fragments):
            # Calcular duración proporcional basada en longitud del texto
            text_ratio = len(fragment_text) / len(text)
            fragment_duration = max(
                total_duration * text_ratio,
                self.min_duration_per_subtitle
            )
            
            # Limitar duración máxima
            fragment_duration = min(fragment_duration, self.max_duration_per_subtitle)
            
            # Calcular tiempos de inicio y fin
            if i == 0:
                fragment_start = start_time
            else:
                fragment_start = fragments[i-1]["end"]
            
            fragment_end = fragment_start + fragment_duration
            
            # Ajustar último fragmento para que termine exactamente con el segmento original
            if i == fragment_count - 1:
                fragment_end = end_time
            
            # Asegurar que no se superponga con el siguiente fragmento
            if fragment_end > end_time:
                fragment_end = end_time
            
            fragments.append({
                "start": fragment_start,
                "end": fragment_end,
                "text": fragment_text
            })
        
        return fragments

    def _segments_to_srt(self, segments: List[Dict]) -> str:
        """Convierte los segmentos de Whisper en formato SRT con fragmentación opcional"""
        srt_content = ""
        subtitle_number = 1
        
        for segment in segments:
            # Crear fragmentos si está habilitado
            fragments = self._create_subtitle_fragments(segment)
            
            for fragment in fragments:
                start = self._format_timestamp(fragment["start"])
                end = self._format_timestamp(fragment["end"])
                text = fragment["text"].strip()
                
                # Filtrar segmentos muy cortos o vacíos
                if text and len(text) > 2:
                    srt_content += f"{subtitle_number}\n{start} --> {end}\n{text}\n\n"
                    subtitle_number += 1
        
        return srt_content

    def _save_srt(self, srt_content: str, file_name: str) -> Path:
        """Guarda el contenido SRT en la carpeta de salida"""
        srt_path = self.output_dir / file_name
        
        try:
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            self.logger.info(f"📄 Subtítulos guardados en: {srt_path}")
            return srt_path
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando subtítulos {srt_path}: {e}")
            raise

    def _is_audio_file(self, file_path: Path) -> bool:
        """Verifica si el archivo es un formato de audio compatible"""
        return file_path.suffix.lower() in self.supported_extensions

    def _get_audio_files(self) -> List[Path]:
        """Obtiene lista de archivos de audio en el directorio"""
        if not self.audio_dir.exists():
            self.logger.warning(f"⚠️ Directorio de audio no existe: {self.audio_dir}")
            return []
        
        audio_files = []
        for file_path in self.audio_dir.rglob("*"):
            if file_path.is_file() and self._is_audio_file(file_path):
                audio_files.append(file_path)
        
        return sorted(audio_files)

    def set_fragmentation_config(
        self,
        max_words_per_subtitle: Optional[int] = None,
        max_chars_per_subtitle: Optional[int] = None,
        min_duration_per_subtitle: Optional[float] = None,
        max_duration_per_subtitle: Optional[float] = None,
        fragment_subtitles: Optional[bool] = None
    ):
        """
        Actualiza la configuración de fragmentación de subtítulos
        
        Args:
            max_words_per_subtitle: Máximo número de palabras por subtítulo
            max_chars_per_subtitle: Máximo número de caracteres por subtítulo
            min_duration_per_subtitle: Duración mínima en segundos por subtítulo
            max_duration_per_subtitle: Duración máxima en segundos por subtítulo
            fragment_subtitles: Habilitar/deshabilitar fragmentación
        """
        if max_words_per_subtitle is not None:
            self.max_words_per_subtitle = max_words_per_subtitle
            
        if max_chars_per_subtitle is not None:
            self.max_chars_per_subtitle = max_chars_per_subtitle
            
        if min_duration_per_subtitle is not None:
            self.min_duration_per_subtitle = min_duration_per_subtitle
            
        if max_duration_per_subtitle is not None:
            self.max_duration_per_subtitle = max_duration_per_subtitle
            
        if fragment_subtitles is not None:
            self.fragment_subtitles = fragment_subtitles
        
        self.logger.info(f"🔧 Configuración de fragmentación actualizada:")
        self.logger.info(f"   - Fragmentación: {'Habilitada' if self.fragment_subtitles else 'Deshabilitada'}")
        self.logger.info(f"   - Máx. palabras: {self.max_words_per_subtitle}")
        self.logger.info(f"   - Máx. caracteres: {self.max_chars_per_subtitle}")
        self.logger.info(f"   - Duración mín/máx: {self.min_duration_per_subtitle}s - {self.max_duration_per_subtitle}s")

    def transcribe_audio(self, audio_path: Path, custom_options: Optional[Dict] = None) -> str:
        """
        Transcribe un solo archivo de audio y devuelve el contenido SRT
        
        Args:
            audio_path: Path al archivo de audio
            custom_options: Opciones adicionales para Whisper
        """
        try:
            self.logger.info(f"🎙️ Transcribiendo: {audio_path.name}")
            
            # Verificar que el archivo existe
            if not audio_path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {audio_path}")
            
            # Verificar tamaño del archivo
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            self.logger.info(f"📊 Tamaño del archivo: {file_size_mb:.1f} MB")
            
            if file_size_mb > 100:  # Advertencia para archivos grandes
                self.logger.warning(f"⚠️ Archivo grande ({file_size_mb:.1f} MB), puede tardar mucho tiempo")
            
            # Opciones por defecto para Whisper
            transcribe_options = {
                "language": self.language,
                "verbose": False,
                "word_timestamps": True,  # Mejora la precisión de timestamps
            }
            
            # Aplicar opciones personalizadas si se proporcionan
            if custom_options:
                transcribe_options.update(custom_options)
            
            # Realizar transcripción
            start_time = datetime.now()
            result = self.model.transcribe(str(audio_path), **transcribe_options)
            duration = datetime.now() - start_time
            
            self.logger.info(f"⏱️ Transcripción completada en {duration.total_seconds():.1f} segundos")
            
            # Mostrar información sobre fragmentación
            if self.fragment_subtitles:
                original_segments = len(result["segments"])
                self.logger.info(f"🔧 Fragmentando subtítulos (máx: {self.max_words_per_subtitle} palabras, {self.max_chars_per_subtitle} chars)")
            
            # Convertir a formato SRT
            srt_content = self._segments_to_srt(result["segments"])
            
            if not srt_content.strip():
                self.logger.warning(f"⚠️ No se detectó texto en el audio: {audio_path.name}")
                return ""
            
            # Contar subtítulos generados
            subtitle_count = len([line for line in srt_content.split('\n') if line.strip().isdigit()])
            self.logger.info(f"📝 Subtítulos generados: {subtitle_count}")
            
            return srt_content
            
        except Exception as e:
            self.logger.error(f"❌ Error transcribiendo {audio_path.name}: {e}")
            raise

    def transcribe_single_file(self, audio_path: Path, output_name: Optional[str] = None) -> Optional[Path]:
        """
        Transcribe un archivo específico y guarda el resultado
        
        Args:
            audio_path: Path al archivo de audio
            output_name: Nombre personalizado para el archivo SRT
        """
        try:
            srt_content = self.transcribe_audio(audio_path)
            
            if srt_content:
                # Determinar nombre del archivo de salida
                if not output_name:
                    suffix = "_fragmentado" if self.fragment_subtitles else ""
                    output_name = audio_path.stem + suffix + ".srt"
                
                return self._save_srt(srt_content, output_name)
            else:
                self.logger.warning(f"⚠️ No se generaron subtítulos para {audio_path.name}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error procesando {audio_path.name}: {e}")
            return None

    def transcribe_all(self) -> Dict[str, Any]:
        """
        Transcribe todos los audios del directorio y genera archivos SRT
        
        Returns:
            Diccionario con estadísticas del proceso
        """
        audio_files = self._get_audio_files()
        
        if not audio_files:
            self.logger.warning("⚠️ No se encontraron archivos de audio para transcribir")
            return {
                "success": False,
                "total_files": 0,
                "processed": 0,
                "failed": 0,
                "output_files": []
            }

        self.logger.info(f"🔎 Encontrados {len(audio_files)} archivos para transcribir")
        
        # Mostrar configuración actual
        if self.fragment_subtitles:
            self.logger.info(f"🔧 Fragmentación habilitada: {self.max_words_per_subtitle} palabras máx, {self.max_chars_per_subtitle} chars máx")
        else:
            self.logger.info("🔧 Fragmentación deshabilitada - usando segmentos originales de Whisper")
        
        # Estadísticas
        stats = {
            "success": True,
            "total_files": len(audio_files),
            "processed": 0,
            "failed": 0,
            "output_files": [],
            "errors": [],
            "fragmentation_enabled": self.fragment_subtitles,
            "fragmentation_config": {
                "max_words": self.max_words_per_subtitle,
                "max_chars": self.max_chars_per_subtitle,
                "min_duration": self.min_duration_per_subtitle,
                "max_duration": self.max_duration_per_subtitle
            }
        }
        
        start_time = datetime.now()
        
        for audio_file in audio_files:
            try:
                self.logger.info(f"\n📝 Procesando {stats['processed'] + 1}/{len(audio_files)}: {audio_file.name}")
                
                output_path = self.transcribe_single_file(audio_file)
                
                if output_path:
                    stats["processed"] += 1
                    stats["output_files"].append(str(output_path))
                    self.logger.info(f"✅ Completado: {audio_file.name}")
                else:
                    stats["failed"] += 1
                    stats["errors"].append(f"No se pudo procesar: {audio_file.name}")
                    
            except Exception as e:
                stats["failed"] += 1
                error_msg = f"Error en {audio_file.name}: {str(e)}"
                stats["errors"].append(error_msg)
                self.logger.error(f"❌ {error_msg}")

        # Resumen final
        total_time = datetime.now() - start_time
        self.logger.info(f"\n✅ Transcripción finalizada!")
        self.logger.info(f"⏱️ Tiempo total: {total_time.total_seconds():.1f} segundos")
        self.logger.info(f"📊 Procesados: {stats['processed']}/{stats['total_files']}")
        
        if stats["failed"] > 0:
            self.logger.warning(f"⚠️ Errores: {stats['failed']}")
        
        return stats

    def get_model_info(self) -> Dict[str, Any]:
        """Retorna información sobre el modelo actual y configuración"""
        return {
            "model_name": self.model_name,
            "language": self.language,
            "device": getattr(self.model, 'device', 'unknown'),
            "supported_languages": whisper.tokenizer.LANGUAGES,
            "supported_extensions": list(self.supported_extensions),
            "fragmentation_config": {
                "enabled": self.fragment_subtitles,
                "max_words_per_subtitle": self.max_words_per_subtitle,
                "max_chars_per_subtitle": self.max_chars_per_subtitle,
                "min_duration_per_subtitle": self.min_duration_per_subtitle,
                "max_duration_per_subtitle": self.max_duration_per_subtitle
            }
        }

    def validate_setup(self) -> Dict[str, Any]:
        """Valida la configuración y retorna un reporte"""
        report = {
            "audio_dir_exists": self.audio_dir.exists(),
            "audio_dir_readable": False,
            "output_dir_exists": self.output_dir.exists(),
            "output_dir_writable": False,
            "model_loaded": hasattr(self, 'model'),
            "audio_files_found": 0,
            "fragmentation_config_valid": True
        }
        
        try:
            # Verificar directorio de audio
            if report["audio_dir_exists"]:
                report["audio_dir_readable"] = os.access(self.audio_dir, os.R_OK)
                report["audio_files_found"] = len(self._get_audio_files())
            
            # Verificar directorio de salida
            if report["output_dir_exists"]:
                report["output_dir_writable"] = os.access(self.output_dir, os.W_OK)
            
            # Validar configuración de fragmentación
            if self.max_words_per_subtitle <= 0 or self.max_chars_per_subtitle <= 0:
                report["fragmentation_config_valid"] = False
                report["fragmentation_error"] = "max_words_per_subtitle y max_chars_per_subtitle deben ser > 0"
            
            if self.min_duration_per_subtitle <= 0 or self.max_duration_per_subtitle <= self.min_duration_per_subtitle:
                report["fragmentation_config_valid"] = False
                report["fragmentation_error"] = "Duraciones inválidas"
            
        except Exception as e:
            self.logger.error(f"❌ Error validando configuración: {e}")
            report["validation_error"] = str(e)
        
        return report

if __name__ == "__main__":
    # Ejemplo de uso y prueba
    
    print("🔧 Creando transcriptor con fragmentación...")
    transcriber = AudioTranscriber(
        audio_dir="tts_outputs/audio",
        output_dir="subtitles",
        model_name="small",
        language="es",
        verbose=True,
        max_words_per_subtitle=6,
        max_chars_per_subtitle=20
    )
    
    # Validar configuración
    validation = transcriber.validate_setup()
    print("🔍 Validación:", validation)
    
    # Mostrar configuración actual
    model_info = transcriber.get_model_info()
    print("📋 Configuración actual:")
    print(f"   Fragmentación: {'✅ Habilitada' if model_info['fragmentation_config']['enabled'] else '❌ Deshabilitada'}")
    print(f"   Máx. palabras: {model_info['fragmentation_config']['max_words_per_subtitle']}")
    print(f"   Máx. caracteres: {model_info['fragmentation_config']['max_chars_per_subtitle']}")
    
    # Ejemplo de cambio de configuración dinámico
    print("\n🔄 Cambiando configuración para frases aún más cortas...")
    transcriber.set_fragmentation_config(
        max_words_per_subtitle=4,
        max_chars_per_subtitle=30
    )
    
    # Transcribir todos los archivos
    results = transcriber.transcribe_all()
    print("\n📊 Resultados:", results)