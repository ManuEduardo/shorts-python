#!/usr/bin/env python3
"""
Sistema de generación de assets para videos de YouTube - Versión 2.1

Correcciones:
- Arregla el error de movimiento de archivos de audio
- Mejora el manejo de rutas y directorios
- Asegura que los directorios de destino existan
"""

import json
import os
import asyncio
import concurrent.futures
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# Imports locales (asumiendo que están en el mismo directorio)
from tts import SimpleTTS, TTSConfig
from image_downloader import ImageDownloader
from audio_trascriber import AudioTranscriber


@dataclass
class ProjectConfig:
    """Configuración centralizada del proyecto"""
    # Paths base
    root_dir: Path = Path("projects")
    project_name: str = "default_project"
    
    # Archivos de entrada
    config_file: str = "video.json"
    script_file: str = "guion.txt"
    
    # APIs
    unsplash_key: Optional[str] = None
    pexels_key: Optional[str] = None
    pixabay_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    
    # Configuración de procesos
    max_workers: int = 3
    verbose: bool = True
    
    @property
    def project_dir(self) -> Path:
        """Directorio del proyecto actual"""
        return self.root_dir / self.project_name.replace(" ", "_")
    
    @property
    def assets_dir(self) -> Path:
        """Directorio de assets del proyecto"""
        return self.project_dir / "assets"
    
    @property
    def audio_dir(self) -> Path:
        """Directorio de audio"""
        return self.assets_dir / "audio"
    
    @property
    def images_dir(self) -> Path:
        """Directorio de imágenes"""
        return self.assets_dir / "images"
    
    @property
    def subtitles_dir(self) -> Path:
        """Directorio de subtítulos"""
        return self.assets_dir / "subtitles"
    
    @property
    def temp_dir(self) -> Path:
        """Directorio temporal"""
        return self.project_dir / "temp"
    
    def create_directories(self):
        """Crea toda la estructura de directorios"""
        directories = [
            self.project_dir,
            self.assets_dir,
            self.audio_dir,
            self.images_dir,
            self.subtitles_dir,
            self.temp_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


class VideoAssetsGenerator:
    """Generador principal de assets para videos"""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.video_data: Dict[str, Any] = {}
        
        # Crear estructura de directorios
        self.config.create_directories()
        
        # Cargar configuración del video
        self._load_video_config()
        
    def _setup_logger(self) -> logging.Logger:
        """Configura el logger"""
        logger = logging.getLogger("VideoAssetsGenerator")
        logger.setLevel(logging.INFO if self.config.verbose else logging.WARNING)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _load_video_config(self):
        """Carga la configuración del video desde JSON"""
        try:
            config_path = Path(self.config.config_file)
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.video_data = json.load(f)
                    
                # Actualizar nombre del proyecto si está en el JSON
                if "title" in self.video_data:
                    self.config.project_name = self.video_data["title"]
                    
                self.logger.info(f"📋 Configuración cargada: {self.video_data.get('title', 'Sin título')}")
            else:
                self.logger.warning(f"⚠️ Archivo de configuración {config_path} no encontrado")
                
        except Exception as e:
            self.logger.error(f"❌ Error cargando configuración: {e}")
    
    def _generate_images(self) -> bool:
        """Genera/descarga imágenes para el proyecto"""
        try:
            self.logger.info("🖼️ Iniciando descarga de imágenes...")
            
            # Obtener keywords del video_data o usar defaults
            keywords = self.video_data.get("keywords", ["video", "contenido"])
            google_keywords = self.video_data.get("google_keywords", keywords)
            
            downloader = ImageDownloader(
                project_name=str(self.config.images_dir),
                keywords=keywords,
                google_keywords=google_keywords,
                images_per_keyword=3,
                images_per_keyword_google=5,
                unsplash_key=self.config.unsplash_key,
                pexels_key=self.config.pexels_key,
                pixabay_key=self.config.pixabay_key,
                serpapi_key=self.config.serpapi_key
            )
            
            downloader.download_images()
            self.logger.info("✅ Descarga de imágenes completada")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error generando imágenes: {e}")
            return False
    
    def _generate_audio(self) -> Optional[Path]:
        """Genera audio a partir del guión"""
        try:
            self.logger.info("🎙️ Iniciando generación de audio...")
            
            # Verificar que existe el archivo de guión
            script_path = Path(self.config.script_file)
            if not script_path.exists():
                self.logger.error(f"❌ Archivo de guión no encontrado: {script_path}")
                return None
            
            # CORRECCIÓN: Crear directorio temporal específico para el TTS
            tts_temp_dir = self.config.project_dir / "tts_temp"
            tts_temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Configuración TTS personalizada
            tts_config = TTSConfig(
                remove_silence=True,
                silence_threshold=-40.0, # Umbral de silencio 
                min_silence_duration=0.4,
                keep_temp_files=False,
                verbose=self.config.verbose,
                root_dir=tts_temp_dir  # Usar directorio temporal específico
            )
            
            tts = SimpleTTS(tts_config)
            
            # Generar audio con nombre basado en el proyecto
            audio_filename = f"{self.config.project_name.replace(' ', '_')}_audio.mp3"
            result = tts.process_file(script_path, audio_filename)
            
            if result:
                # CORRECCIÓN: Asegurar que el directorio de destino existe
                self.config.audio_dir.mkdir(parents=True, exist_ok=True)
                
                # Mover el archivo generado a nuestro directorio de audio
                final_audio_path = self.config.audio_dir / audio_filename
                
                # CORRECCIÓN: Verificar que el archivo fuente existe antes de mover
                if result.exists():
                    try:
                        # Usar shutil.move en lugar de rename para manejar cruces de sistemas de archivos
                        shutil.move(str(result), str(final_audio_path))
                        self.logger.info(f"✅ Audio movido a: {final_audio_path}")
                    except Exception as move_error:
                        self.logger.warning(f"⚠️ Error moviendo archivo, intentando copia: {move_error}")
                        # Fallback: copiar y eliminar
                        shutil.copy2(str(result), str(final_audio_path))
                        if result.exists():
                            result.unlink()  # Eliminar archivo original
                        self.logger.info(f"✅ Audio copiado a: {final_audio_path}")
                else:
                    self.logger.error(f"❌ El archivo de audio generado no existe: {result}")
                    return None
                
                self.logger.info(f"✅ Audio generado: {final_audio_path}")
                return final_audio_path
            else:
                self.logger.error("❌ Error generando audio")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error en generación de audio: {e}")
            return None
    
    def _generate_subtitles(self, audio_path: Path) -> bool:
        """Genera subtítulos a partir del audio"""
        try:
            self.logger.info("📝 Iniciando generación de subtítulos...")
            
            # Verificar que el archivo de audio existe
            if not audio_path.exists():
                self.logger.error(f"❌ Archivo de audio no encontrado: {audio_path}")
                return False
            
            # Asegurar que el directorio de subtítulos existe
            self.config.subtitles_dir.mkdir(parents=True, exist_ok=True)
            
            transcriber = AudioTranscriber(
                audio_dir=str(audio_path.parent),
                output_dir=str(self.config.subtitles_dir),
                model_name="small",
                language="es",
                verbose=self.config.verbose
            )
            
            # Transcribir solo el archivo específico
            srt_content = transcriber.transcribe_audio(audio_path)
            
            if srt_content:
                srt_filename = audio_path.stem + ".srt"
                transcriber._save_srt(srt_content, srt_filename)
                self.logger.info("✅ Subtítulos generados")
                return True
            else:
                self.logger.error("❌ No se pudo generar contenido de subtítulos")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Error generando subtítulos: {e}")
            return False
    
    async def generate_assets_parallel(self):
        """Genera todos los assets en paralelo"""
        self.logger.info("🚀 Iniciando generación de assets en paralelo...")
        start_time = datetime.now()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Proceso 1: Imágenes (independiente)
            future_images = executor.submit(self._generate_images)
            
            # Proceso 2.1: Audio (debe completarse antes de subtítulos)
            future_audio = executor.submit(self._generate_audio)
            
            # Esperar a que termine el audio para generar subtítulos
            try:
                audio_path = future_audio.result(timeout=600)  # 10 minutos timeout
                
                if audio_path and audio_path.exists():
                    # Proceso 2.2: Subtítulos (depende del audio)
                    future_subtitles = executor.submit(self._generate_subtitles, audio_path)
                    
                    # Esperar todos los procesos
                    images_success = future_images.result(timeout=300)
                    subtitles_success = future_subtitles.result(timeout=300)
                    
                    # Resultados
                    results = {
                        "images": images_success,
                        "audio": True,
                        "subtitles": subtitles_success,
                        "audio_path": audio_path
                    }
                    
                else:
                    # Si falló el audio, solo esperar imágenes
                    images_success = future_images.result(timeout=300)
                    results = {
                        "images": images_success,
                        "audio": False,
                        "subtitles": False,
                        "audio_path": None
                    }
                    
            except concurrent.futures.TimeoutError:
                self.logger.error("⏰ Timeout en la generación de assets")
                results = {
                    "images": False,
                    "audio": False,
                    "subtitles": False,
                    "audio_path": None
                }
        
        duration = datetime.now() - start_time
        self.logger.info(f"⏱️ Generación completada en {duration.total_seconds():.1f} segundos")
        
        return results
    
    def generate_assets_sequential(self):
        """Genera todos los assets secuencialmente (fallback)"""
        self.logger.info("🔄 Generando assets secuencialmente...")
        
        # Proceso 1: Imágenes
        images_success = self._generate_images()
        
        # Proceso 2.1: Audio
        audio_path = self._generate_audio()
        
        # Proceso 2.2: Subtítulos (si el audio se generó correctamente)
        subtitles_success = False
        if audio_path and audio_path.exists():
            subtitles_success = self._generate_subtitles(audio_path)
        
        return {
            "images": images_success,
            "audio": audio_path is not None and audio_path.exists(),
            "subtitles": subtitles_success,
            "audio_path": audio_path
        }
    
    def print_summary(self, results: Dict[str, Any]):
        """Imprime resumen de resultados"""
        print("\n" + "="*50)
        print("📊 RESUMEN DE GENERACIÓN DE ASSETS")
        print("="*50)
        
        print(f"📁 Proyecto: {self.config.project_name}")
        print(f"📂 Directorio: {self.config.project_dir}")
        print()
        
        # Status de cada proceso
        statuses = {
            "🖼️ Imágenes": "✅ Completado" if results["images"] else "❌ Error",
            "🎙️ Audio": "✅ Completado" if results["audio"] else "❌ Error",
            "📝 Subtítulos": "✅ Completado" if results["subtitles"] else "❌ Error"
        }
        
        for process, status in statuses.items():
            print(f"{process}: {status}")
        
        # Información adicional
        if results["audio_path"] and results["audio_path"].exists():
            audio_size = results["audio_path"].stat().st_size / (1024*1024)
            print(f"🎵 Audio generado: {results['audio_path'].name} ({audio_size:.1f} MB)")
        
        # Contar imágenes descargadas
        if self.config.images_dir.exists():
            image_count = len(list(self.config.images_dir.rglob("*.jpg"))) + \
                         len(list(self.config.images_dir.rglob("*.png")))
            print(f"🖼️ Imágenes descargadas: {image_count}")
        
        success_count = sum([results["images"], results["audio"], results["subtitles"]])
        print(f"\n🎯 Procesos exitosos: {success_count}/3")
        
        if success_count == 3:
            print("🎉 ¡Todos los assets generados correctamente!")
        elif success_count > 0:
            print("⚠️ Generación parcial completada")
        else:
            print("❌ No se pudo generar ningún asset")


async def main():
    """Función principal"""
    print("🎬 SISTEMA DE GENERACIÓN DE ASSETS PARA VIDEOS v2.1")
    print("=" * 60)
    
    # Cargar variables de entorno
    from dotenv import load_dotenv
    load_dotenv()
    
    # Configuración del proyecto
    config = ProjectConfig(
        config_file="video.json",
        script_file="guion.txt",
        unsplash_key=os.getenv('UNSPLASH_KEY'),
        pexels_key=os.getenv('PEXELS_KEY'),
        pixabay_key=os.getenv('PIXABAY_KEY'),
        serpapi_key=os.getenv('SERPAPI_KEY'),
        verbose=True
    )
    
    # Crear generador
    generator = VideoAssetsGenerator(config)
    
    try:
        # Intentar generación en paralelo
        results = await generator.generate_assets_parallel()
        
    except Exception as e:
        print(f"⚠️ Error en ejecución paralela: {e}")
        print("🔄 Cambiando a ejecución secuencial...")
        results = generator.generate_assets_sequential()
    
    # Mostrar resumen
    generator.print_summary(results)


def main_sync():
    """Versión síncrona de main para compatibilidad"""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()