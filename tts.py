#!/usr/bin/env python3
"""
Sistema TTS optimizado y corregido - Versión 4.2

CORRECCIONES PRINCIPALES:
- ✅ Arregla error de combinación ffmpeg (WAV → MP3)
- ✅ Mejor manejo de codec de audio
- ✅ Validación robusta de archivos
- ✅ Fallback mejorado entre modelos
- ✅ Limpieza de caracteres problemáticos (¡¿)
- ✅ Estructura de directorios optimizada
"""

import os
import re
import logging
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Union
from enum import Enum


class VoiceModel(Enum):
    """Modelos de voz seleccionados y probados"""
    ES_CSS10 = "tts_models/es/css10/vits"           # Modelo principal - Natural
    ES_MAI = "tts_models/es/mai/tacotron2-DDC"      # Modelo de respaldo - Cálido


@dataclass
class TTSConfig:
    """Configuración optimizada"""
    voice_model: VoiceModel = VoiceModel.ES_CSS10
    max_chars_per_chunk: int = 200  # Reducido para mayor estabilidad
    sentence_pause: float = 0.1     # Pausas muy cortas
    paragraph_pause: float = 0.2    # Pausas breves
    combine_fragments: bool = True
    keep_temp_files: bool = False
    verbose: bool = True
    
    # Configuración de procesamiento de audio
    remove_silence: bool = True
    silence_threshold: float = -35.0    # Menos estricto
    min_silence_duration: float = 0.5   # Reducido para mantener naturalidad
    silence_padding: float = 0.05       # Padding mínimo
    
    # Audio settings
    output_format: str = "mp3"          # wav o mp3
    audio_bitrate: str = "128k"         # Bitrate para MP3
    sample_rate: int = 22050           # Sample rate estándar
    
    # Carpeta raíz única
    root_dir: Path = Path("tts_outputs")

    @property
    def input_dir(self) -> Path:
        return self.root_dir / "input"

    @property
    def output_dir(self) -> Path:
        return self.root_dir / "audio"

    @property
    def temp_dir(self) -> Path:
        return self.root_dir / "temp"


class SimpleTTS:
    """Sistema TTS mejorado y corregido"""
    
    def __init__(self, config: TTSConfig = None):
        self.config = config or TTSConfig()
        self.logger = self._setup_logger()
        self._create_directories()
        self._validate_dependencies()
        self.current_model = self.config.voice_model
        self.logger.info("🚀 Sistema TTS optimizado v4.2 inicializado")
        self.logger.info(f"🎤 Modelo inicial: {self.current_model.value}")

    def _setup_logger(self):
        logger = logging.getLogger("SimpleTTS")
        logger.setLevel(logging.INFO if self.config.verbose else logging.WARNING)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _create_directories(self):
        for directory in [self.config.input_dir, self.config.output_dir, self.config.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"📁 Directorio creado: {directory}")

    def _validate_dependencies(self):
        """Valida que las dependencias estén instaladas"""
        try:
            # Verificar TTS
            result = subprocess.run(['tts', '--help'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception("TTS no está instalado o no funciona")
            
            # Verificar ffmpeg
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception("ffmpeg no está instalado")
                
            self.logger.info("✅ Dependencias validadas: TTS y ffmpeg disponibles")
            
        except Exception as e:
            self.logger.error(f"❌ Error de dependencias: {e}")
            raise

    def load_text(self, file_path: Union[str, Path]) -> str:
        """Carga texto y limpia caracteres problemáticos"""
        file_path = Path(file_path)
        
        # Buscar archivo
        search_paths = [file_path]
        if not file_path.is_absolute():
            search_paths.extend([
                Path.cwd() / file_path.name,
                self.config.input_dir / file_path.name
            ])
        
        for path in search_paths:
            if path.exists():
                file_path = path
                break
        else:
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        # Cargar con múltiples encodings
        for encoding in ['utf-8', 'latin1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read().strip()
                self.logger.info(f"📄 Archivo cargado: {file_path} ({len(content)} caracteres)")
                return self._clean_text(content)
            except UnicodeDecodeError:
                continue
                
        raise UnicodeDecodeError("No se pudo decodificar el archivo con ningún encoding")

    def _clean_text(self, text: str) -> str:
        """Limpieza avanzada del texto"""
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n{2,}', '\n\n', text)
        
        # ⚠️ IMPORTANTE: Remover caracteres problemáticos que causan errores en TTS
        text = text.replace('¡', '')  # Eliminar signos de exclamación invertidos
        text = text.replace('¿', '')  # Eliminar signos de interrogación invertidos
        
        # Limpiar caracteres especiales problemáticos pero mantener básicos
        text = re.sub(r'[^\w\s.,;:!?()"\'-áéíóúüñÁÉÍÓÚÜÑ]', ' ', text)
        
        # Arreglar espaciado después de puntuación
        text = re.sub(r'([.,;:!?])([A-ZÁÉÍÓÚÜÑ])', r'\1 \2', text)
        
        # Remover comillas problemáticas
        text = text.replace('"', '')  # Eliminar comillas dobles que causan problemas
        
        # Normalizar espacios finales
        text = ' '.join(text.split())
        
        self.logger.info("🧹 Texto limpiado y caracteres problemáticos eliminados")
        return text.strip()

    def split_text(self, text: str) -> List[str]:
        """Divide texto en fragmentos manejables"""
        fragments = []
        max_chars = self.config.max_chars_per_chunk
        
        # Dividir por párrafos primero
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        for paragraph in paragraphs:
            if len(paragraph) <= max_chars:
                fragments.append(paragraph)
            else:
                # Dividir párrafo largo por oraciones
                sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜÑ])', paragraph)
                current_fragment = ""
                
                for sentence in sentences:
                    test_fragment = current_fragment + " " + sentence if current_fragment else sentence
                    
                    if len(test_fragment) <= max_chars:
                        current_fragment = test_fragment
                    else:
                        # Agregar fragmento actual si no está vacío
                        if current_fragment:
                            fragments.append(current_fragment.strip())
                        
                        # Si la oración sola es muy larga, dividirla por comas
                        if len(sentence) > max_chars:
                            comma_parts = sentence.split(', ')
                            temp_part = ""
                            for part in comma_parts:
                                if len(temp_part + ", " + part) <= max_chars:
                                    temp_part = temp_part + ", " + part if temp_part else part
                                else:
                                    if temp_part:
                                        fragments.append(temp_part.strip())
                                    temp_part = part
                            if temp_part:
                                current_fragment = temp_part
                        else:
                            current_fragment = sentence
                
                # Agregar último fragmento
                if current_fragment:
                    fragments.append(current_fragment.strip())
        
        # Filtrar fragmentos muy cortos o vacíos
        fragments = [f for f in fragments if len(f.strip()) > 10]
        
        self.logger.info(f"📚 Texto dividido en {len(fragments)} fragmentos")
        return fragments

    def generate_audio_fragment(self, text: str, output_file: Path, attempt: int = 1) -> bool:
        """Genera audio para un fragmento con reintentos"""
        try:
            self.logger.info(f"🎵 Generando fragmento: {output_file.name} (intento {attempt})")
            
            # Escapar texto para evitar problemas con comillas
            clean_text = text.replace('"', '').replace("'", "").strip()
            
            # Usar el modelo actual
            cmd = [
                'tts',
                '--text', clean_text,
                '--model_name', self.current_model.value,
                '--out_path', str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and output_file.exists() and output_file.stat().st_size > 1000:
                self.logger.info("✅ Fragmento generado exitosamente")
                return True
            else:
                self.logger.warning(f"⚠️ Error generando fragmento (código: {result.returncode})")
                if result.stderr:
                    self.logger.warning(f"Error: {result.stderr[:200]}")
                
                # Cambiar modelo si hay muchos errores
                if attempt == 1 and self.current_model == VoiceModel.ES_CSS10:
                    self.logger.info("🔄 Cambiando a modelo MAI...")
                    self.current_model = VoiceModel.ES_MAI
                    return self.generate_audio_fragment(text, output_file, attempt + 1)
                
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Timeout generando fragmento: {output_file.name}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error generando audio: {e}")
            return False

    def combine_fragments_to_wav(self, fragment_files: List[Path], output_file: Path) -> bool:
        """Combina fragmentos WAV a un archivo WAV final"""
        try:
            self.logger.info(f"🔗 Combinando {len(fragment_files)} fragmentos a WAV...")
            
            file_list = self.config.temp_dir / "file_list.txt"
            with open(file_list, 'w', encoding='utf-8') as f:
                for fragment_file in fragment_files:
                    f.write(f"file '{fragment_file.absolute()}'\n")
            
            # Combinar usando concat demuxer - MANTENER WAV
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(file_list),
                '-c', 'copy',  # Copia directa para WAV → WAV
                str(output_file),
                '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and output_file.exists():
                self.logger.info("✅ Fragmentos combinados a WAV exitosamente")
                return True
            else:
                self.logger.error(f"❌ Error combinando fragmentos: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error en combinación: {e}")
            return False

    def process_audio_to_final(self, input_file: Path, output_file: Path) -> bool:
        """Procesa audio final con eliminación de silencios y conversión de formato"""
        try:
            if not self.config.remove_silence and self.config.output_format.lower() == "wav":
                # Sin procesamiento: copiar directamente
                shutil.copy2(input_file, output_file)
                self.logger.info("📁 Audio copiado sin procesamiento")
                return True
            
            self.logger.info("🎛️ Procesando audio final...")
            
            # Construir filtros de audio
            filters = []
            
            if self.config.remove_silence:
                # Filtro para eliminar silencios
                silence_filter = (
                    f"silenceremove="
                    f"start_periods=1:"
                    f"start_silence=0.1:"
                    f"start_threshold={self.config.silence_threshold}dB:"
                    f"detection=peak,"
                    f"silenceremove="
                    f"stop_periods=-1:"
                    f"stop_silence={self.config.min_silence_duration}:"
                    f"stop_threshold={self.config.silence_threshold}dB:"
                    f"detection=peak"
                )
                filters.append(silence_filter)
            
            # Comando ffmpeg
            cmd = ['ffmpeg', '-i', str(input_file)]
            
            # Agregar filtros si existen
            if filters:
                cmd.extend(['-af', ','.join(filters)])
            
            # Configurar output según formato
            if self.config.output_format.lower() == "mp3":
                cmd.extend([
                    '-c:a', 'libmp3lame',
                    '-b:a', self.config.audio_bitrate,
                    '-ar', str(self.config.sample_rate)
                ])
            else:  # WAV
                cmd.extend([
                    '-c:a', 'pcm_s16le',
                    '-ar', str(self.config.sample_rate)
                ])
            
            cmd.extend([str(output_file), '-y'])
            
            self.logger.info(f"🎛️ Aplicando filtros: {len(filters)} filtro(s)")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and output_file.exists():
                # Mostrar estadísticas
                original_size = input_file.stat().st_size / (1024 * 1024)
                processed_size = output_file.stat().st_size / (1024 * 1024)
                
                self.logger.info(f"✅ Audio procesado exitosamente")
                self.logger.info(f"📊 {original_size:.1f}MB → {processed_size:.1f}MB")
                return True
            else:
                self.logger.error(f"❌ Error procesando audio: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error en procesamiento: {e}")
            return False

    def process_file(self, input_file: Union[str, Path], output_name: Optional[str] = None):
        """Procesa archivo completo de texto a audio"""
        try:
            self.logger.info(f"🔄 Procesando archivo: {input_file}")
            
            # 1. Cargar y dividir texto
            text = self.load_text(input_file)
            if not text:
                self.logger.error("❌ No se pudo cargar el texto")
                return None
                
            fragments = self.split_text(text)
            if not fragments:
                self.logger.error("❌ No se pudieron crear fragmentos de texto")
                return None

            # 2. Generar nombre de salida
            if not output_name:
                base_name = Path(input_file).stem + "_audio"
                output_name = f"{base_name}.{self.config.output_format}"

            # 3. Generar fragmentos de audio
            fragment_files = []
            failed_count = 0
            total_fragments = len(fragments)

            for i, fragment in enumerate(fragments):
                self.logger.info(f"📝 Procesando fragmento {i+1}/{total_fragments}")
                frag_out = self.config.temp_dir / f"fragment_{i:03d}.wav"
                
                if self.generate_audio_fragment(fragment, frag_out):
                    fragment_files.append(frag_out)
                else:
                    failed_count += 1
                    self.logger.warning(f"⚠️ Falló fragmento {i+1}")

            if not fragment_files:
                self.logger.error("❌ No se pudo generar ningún fragmento de audio")
                return None

            success_rate = (len(fragment_files) / total_fragments) * 100
            self.logger.info(f"✅ Generados {len(fragment_files)}/{total_fragments} fragmentos ({success_rate:.1f}% éxito)")

            # 4. Combinar fragmentos
            temp_combined = self.config.temp_dir / "combined_temp.wav"
            
            if len(fragment_files) == 1:
                # Un solo fragmento: mover directamente
                shutil.move(str(fragment_files[0]), str(temp_combined))
                self.logger.info("📁 Fragmento único preparado")
            else:
                # Múltiples fragmentos: combinar
                if not self.combine_fragments_to_wav(fragment_files, temp_combined):
                    self.logger.error("❌ Error combinando fragmentos")
                    return None

            # 5. Procesamiento final
            final_output = self.config.output_dir / output_name
            if not self.process_audio_to_final(temp_combined, final_output):
                self.logger.error("❌ Error en procesamiento final")
                return None

            # 6. Limpieza de archivos temporales
            if not self.config.keep_temp_files:
                cleanup_files = fragment_files + [temp_combined]
                cleaned = 0
                for f in cleanup_files:
                    try:
                        if f.exists():
                            f.unlink()
                            cleaned += 1
                    except Exception as e:
                        self.logger.warning(f"⚠️ No se pudo limpiar {f}: {e}")
                
                # Limpiar file_list.txt
                file_list = self.config.temp_dir / "file_list.txt"
                if file_list.exists():
                    file_list.unlink()
                    cleaned += 1
                    
                self.logger.info(f"🧹 Limpiados {cleaned} archivos temporales")

            # 7. Verificar resultado final
            if final_output.exists() and final_output.stat().st_size > 1000:
                size_mb = final_output.stat().st_size / (1024 * 1024)
                duration_estimate = len(text) / 150  # ~150 caracteres por minuto hablado
                self.logger.info(f"🎉 Audio generado exitosamente!")
                self.logger.info(f"📁 Ubicación: {final_output}")
                self.logger.info(f"📊 Tamaño: {size_mb:.1f} MB")
                self.logger.info(f"⏱️ Duración estimada: {duration_estimate:.1f} minutos")
                self.logger.info(f"🎵 Formato: {self.config.output_format.upper()}")
                return final_output
            else:
                self.logger.error("❌ El archivo final no se generó correctamente")
                return None

        except Exception as e:
            self.logger.error(f"❌ Error procesando archivo: {e}")
            return None


def main():
    """Función principal con configuración personalizable"""
    print("🎙️ SISTEMA TTS OPTIMIZADO v4.2")
    print("=" * 50)
    
    # Configuración personalizable
    config = TTSConfig(
        # Configuración de audio
        output_format="mp3",           # "mp3" o "wav" 
        remove_silence=True,           # Eliminar silencios largos
        silence_threshold=-35.0,       # Umbral de silencio (-40 a -30 dB)
        min_silence_duration=0.5,      # Duración mínima de silencio a eliminar
        audio_bitrate="128k",          # Bitrate para MP3
        
        # Configuración de procesamiento
        max_chars_per_chunk=200,       # Caracteres por fragmento
        keep_temp_files=False,         # Mantener archivos temporales
        verbose=True                   # Logging detallado
    )
    
    tts = SimpleTTS(config)

    # Buscar archivo de entrada
    input_files = ["guion.txt", "texto.txt", "input.txt"]
    input_file = None
    
    for file in input_files:
        if Path(file).exists():
            input_file = file
            break
    
    if not input_file:
        print(f"❌ No se encontró archivo de entrada")
        print("📂 Archivos .txt disponibles:")
        for f in Path(".").glob("*.txt"):
            print(f"   - {f.name}")
        print("\n💡 Crea un archivo 'guion.txt' con el texto a convertir")
        return

    print(f"📄 Procesando: {input_file}")
    print(f"🎵 Formato de salida: {config.output_format.upper()}")
    print(f"🔇 Eliminación de silencios: {'✅ Activada' if config.remove_silence else '❌ Desactivada'}")
    if config.remove_silence:
        print(f"   📊 Umbral: {config.silence_threshold}dB | Duración mín: {config.min_silence_duration}s")
    
    result = tts.process_file(input_file)
    
    if result:
        print(f"\n🎉 ¡PROCESO COMPLETADO EXITOSAMENTE!")
        print(f"📁 Archivo generado: {result}")
        print(f"📊 Tamaño final: {result.stat().st_size / (1024*1024):.1f} MB")
        print(f"🎵 Puedes encontrar el audio en: tts_outputs/audio/")
    else:
        print(f"\n❌ ERROR EN LA GENERACIÓN")
        print("💡 Consejos para solucionar:")
        print("   1. Verifica que TTS esté instalado: pip install TTS")
        print("   2. Verifica que ffmpeg esté disponible")
        print("   3. Revisa que el archivo tenga contenido válido")
        print("   4. Si persisten problemas, cambia output_format='wav'")
        print("   5. Para debugging, activa keep_temp_files=True")


if __name__ == "__main__":
    main()