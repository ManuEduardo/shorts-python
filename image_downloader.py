import os
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import concurrent.futures
from serpapi import GoogleSearch


class ImageDownloader:
    """
    Descargador de imágenes mejorado con mejor estructura y manejo de errores
    """
    
    def __init__(
        self,
        project_name: str = "default_project",
        keywords: Optional[List[str]] = None,
        google_keywords: Optional[List[str]] = None,
        images_per_keyword: int = 3,
        images_per_keyword_google: int = 5,
        use_unsplash: bool = True,
        use_pexels: bool = True,
        use_pixabay: bool = True,
        use_google: bool = True,
        unsplash_key: Optional[str] = None,
        pexels_key: Optional[str] = None,
        pixabay_key: Optional[str] = None,
        serpapi_key: Optional[str] = None,
        max_workers: int = 4,
        verbose: bool = True,
    ):
        # Configuración base
        self.project_name = project_name
        self.keywords = keywords or []
        self.google_keywords = google_keywords or []
        self.images_per_keyword = images_per_keyword
        self.images_per_keyword_google = images_per_keyword_google
        self.max_workers = max_workers

        # Flags de fuentes
        self.use_unsplash = use_unsplash and unsplash_key is not None
        self.use_pexels = use_pexels and pexels_key is not None
        self.use_pixabay = use_pixabay and pixabay_key is not None
        self.use_google = use_google and serpapi_key is not None

        # Claves API
        self.unsplash_key = unsplash_key
        self.pexels_key = pexels_key
        self.pixabay_key = pixabay_key
        self.serpapi_key = serpapi_key
        
        # Logger
        self.logger = self._setup_logger(verbose)
        
        # Crear carpeta principal
        self.base_dir = Path(self.project_name)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Validar que al menos una fuente esté disponible
        self._validate_sources()

    def _setup_logger(self, verbose: bool) -> logging.Logger:
        """Configura el logger"""
        logger = logging.getLogger("ImageDownloader")
        logger.setLevel(logging.INFO if verbose else logging.WARNING)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _validate_sources(self):
        """Valida que al menos una fuente de imágenes esté disponible"""
        available_sources = []
        
        if self.use_unsplash:
            available_sources.append("Unsplash")
        if self.use_pexels:
            available_sources.append("Pexels")
        if self.use_pixabay:
            available_sources.append("Pixabay")
        if self.use_google:
            available_sources.append("Google")
        
        if not available_sources:
            self.logger.warning("⚠️ No hay fuentes de imágenes disponibles (faltan API keys)")
        else:
            self.logger.info(f"✅ Fuentes disponibles: {', '.join(available_sources)}")

    # ==== MÉTODOS DE BÚSQUEDA ====
    def _unsplash_search(self, keyword: str, per_page: int) -> List[str]:
        """Busca imágenes en Unsplash"""
        try:
            headers = {"Authorization": f"Client-ID {self.unsplash_key}"}
            params = {"query": keyword, "per_page": per_page, "orientation": "landscape"}
            
            response = requests.get(
                "https://api.unsplash.com/search/photos", 
                headers=headers, 
                params=params, 
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json().get("results", [])
            urls = [item["urls"]["regular"] for item in data if "urls" in item]
            
            self.logger.info(f"📸 Unsplash: {len(urls)} imágenes encontradas para '{keyword}'")
            return urls
            
        except Exception as e:
            self.logger.error(f"❌ Error en Unsplash para '{keyword}': {e}")
            return []

    def _pexels_search(self, keyword: str, per_page: int) -> List[str]:
        """Busca imágenes en Pexels"""
        try:
            headers = {"Authorization": self.pexels_key}
            params = {"query": keyword, "per_page": per_page, "orientation": "landscape"}
            
            response = requests.get(
                "https://api.pexels.com/v1/search", 
                headers=headers, 
                params=params, 
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json().get("photos", [])
            urls = [item["src"]["large"] for item in data if "src" in item]
            
            self.logger.info(f"📸 Pexels: {len(urls)} imágenes encontradas para '{keyword}'")
            return urls
            
        except Exception as e:
            self.logger.error(f"❌ Error en Pexels para '{keyword}': {e}")
            return []

    def _pixabay_search(self, keyword: str, per_page: int) -> List[str]:
        """Busca imágenes en Pixabay"""
        try:
            params = {
                "key": self.pixabay_key, 
                "q": keyword, 
                "image_type": "photo", 
                "per_page": per_page,
                "orientation": "horizontal",
                "min_width": 1280
            }
            
            response = requests.get(
                "https://pixabay.com/api/", 
                params=params, 
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json().get("hits", [])
            urls = [item["largeImageURL"] for item in data if "largeImageURL" in item]
            
            self.logger.info(f"📸 Pixabay: {len(urls)} imágenes encontradas para '{keyword}'")
            return urls
            
        except Exception as e:
            self.logger.error(f"❌ Error en Pixabay para '{keyword}': {e}")
            return []

    def _google_search(self, keyword: str, per_page: int) -> List[str]:
        """Busca imágenes en Google"""
        try:
            params = {
                "engine": "google",
                "q": keyword,
                "tbm": "isch",
                "num": per_page,
                "api_key": self.serpapi_key,
                "imgsz": "l",  # Imágenes grandes
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            images = results.get("images_results", [])
            urls = [img.get("original", img.get("link", "")) for img in images[:per_page] if img.get("original") or img.get("link")]
            
            self.logger.info(f"📸 Google: {len(urls)} imágenes encontradas para '{keyword}'")
            return urls
            
        except Exception as e:
            self.logger.error(f"❌ Error en Google para '{keyword}': {e}")
            return []

    def _download_single_image(self, url: str, filepath: Path) -> bool:
        """Descarga una sola imagen"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            response.raise_for_status()
            
            # Verificar que es una imagen
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/jpeg', 'image/png', 'image/jpg']):
                self.logger.warning(f"⚠️ URL no contiene imagen válida: {url}")
                return False
            
            # Guardar imagen
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verificar que el archivo se guardó correctamente
            if filepath.exists() and filepath.stat().st_size > 0:
                self.logger.info(f"✅ Guardada → {filepath.name}")
                return True
            else:
                self.logger.warning(f"⚠️ Archivo vacío o no guardado: {filepath}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error descargando {filepath.name}: {e}")
            return False

    def _download_images_for_keyword(self, keyword: str) -> Dict[str, int]:
        """Descarga imágenes para una palabra clave específica"""
        self.logger.info(f"\n🔍 Procesando keyword: '{keyword}'")
        
        # Crear carpeta para la keyword
        keyword_folder = self.base_dir / keyword.replace(" ", "_").replace("/", "_")
        keyword_folder.mkdir(parents=True, exist_ok=True)
        
        results = {
            "unsplash": 0,
            "pexels": 0,
            "pixabay": 0,
            "google": 0
        }
        
        # Definir fuentes a usar
        sources_config = []
        
        if self.use_unsplash:
            sources_config.append(("unsplash", self._unsplash_search, self.images_per_keyword))
        if self.use_pexels:
            sources_config.append(("pexels", self._pexels_search, self.images_per_keyword))
        if self.use_pixabay:
            sources_config.append(("pixabay", self._pixabay_search, self.images_per_keyword))
        if self.use_google and keyword in self.google_keywords:
            sources_config.append(("google", self._google_search, self.images_per_keyword_google))
        
        # Procesar cada fuente
        for source_name, search_fn, per_page in sources_config:
            self.logger.info(f"🔎 Buscando en {source_name}...")
            urls = search_fn(keyword, per_page)
            
            if urls:
                # Descargar imágenes en paralelo
                download_tasks = []
                for i, url in enumerate(urls, start=1):
                    filename = f"{keyword.replace(' ', '_')}_{source_name}_{i:02d}.jpg"
                    filepath = keyword_folder / filename
                    download_tasks.append((url, filepath))
                
                # Ejecutar descargas en paralelo
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(download_tasks), 4)) as executor:
                    futures = [executor.submit(self._download_single_image, url, filepath) 
                             for url, filepath in download_tasks]
                    
                    successful = 0
                    for future in concurrent.futures.as_completed(futures):
                        if future.result():
                            successful += 1
                    
                    results[source_name] = successful
                    self.logger.info(f"✅ {source_name}: {successful}/{len(urls)} imágenes descargadas")
            else:
                self.logger.warning(f"⚠️ No se encontraron URLs en {source_name}")
        
        total_downloaded = sum(results.values())
        self.logger.info(f"📊 Total para '{keyword}': {total_downloaded} imágenes descargadas")
        
        return results

    def download_images(self) -> Dict[str, Any]:
        """Descarga todas las imágenes y retorna estadísticas"""
        self.logger.info("🚀 Iniciando descarga de imágenes...")
        
        # Combinar todas las keywords
        all_keywords = list(set(self.keywords + self.google_keywords))
        
        if not all_keywords:
            self.logger.warning("⚠️ No se especificaron keywords para descargar")
            return {"success": False, "total_images": 0, "keywords_processed": 0}
        
        self.logger.info(f"📝 Keywords a procesar: {all_keywords}")
        
        total_stats = {}
        total_images = 0
        
        # Procesar cada keyword
        for keyword in all_keywords:
            try:
                keyword_stats = self._download_images_for_keyword(keyword)
                total_stats[keyword] = keyword_stats
                total_images += sum(keyword_stats.values())
                
            except Exception as e:
                self.logger.error(f"❌ Error procesando keyword '{keyword}': {e}")
                total_stats[keyword] = {"error": str(e)}
        
        # Resumen final
        self.logger.info(f"\n🎉 Descarga completada!")
        self.logger.info(f"📊 Total de imágenes descargadas: {total_images}")
        self.logger.info(f"📝 Keywords procesadas: {len([k for k in total_stats if 'error' not in total_stats[k]])}/{len(all_keywords)}")
        
        return {
            "success": True,
            "total_images": total_images,
            "keywords_processed": len(all_keywords),
            "detailed_stats": total_stats,
            "base_directory": str(self.base_dir)
        }

    def get_downloaded_images(self) -> List[Path]:
        """Retorna lista de todas las imágenes descargadas"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        downloaded_images = []
        
        for ext in image_extensions:
            downloaded_images.extend(self.base_dir.rglob(f"*{ext}"))
        
        return sorted(downloaded_images)
    
    def cleanup_empty_folders(self):
        """Elimina carpetas vacías"""
        try:
            for folder in self.base_dir.iterdir():
                if folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()
                    self.logger.info(f"🗑️ Carpeta vacía eliminada: {folder.name}")
        except Exception as e:
            self.logger.warning(f"⚠️ Error limpiando carpetas vacías: {e}")


if __name__ == "__main__":
    # Ejemplo de uso
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    downloader = ImageDownloader(
        project_name="test_project",
        keywords=["naturaleza", "tecnología"],
        google_keywords=["artificial intelligence", "machine learning"],
        unsplash_key=os.getenv('UNSPLASH_KEY'),
        pexels_key=os.getenv('PEXELS_KEY'),
        pixabay_key=os.getenv('PIXABAY_KEY'),
        serpapi_key=os.getenv('SERPAPI_KEY'),
        verbose=True
    )
    
    results = downloader.download_images()
    print("\n📊 Resultados:", results)