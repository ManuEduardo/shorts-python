import yt_dlp
import pandas as pd
from datetime import datetime
import os


class YouTubeShortsScraper:
    def __init__(self, channel_url, output_dir="data", verbose=True):
        self.channel_url = channel_url
        self.output_dir = output_dir
        self.verbose = verbose

        # Crear carpeta de salida si no existe
        os.makedirs(self.output_dir, exist_ok=True)

        # Configuración de yt-dlp
        self.ydl_opts = {
            "quiet": not self.verbose,
            "extract_flat": False,
            "skip_download": True,
            "dump_single_json": True,
        }

        # Archivo CSV con timestamp
        self.csv_filename = os.path.join(
            self.output_dir,
            f"youtube_shorts_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    def _log(self, message):
        """Imprime mensajes solo si verbose=True."""
        if self.verbose:
            print(message)

    def _fetch_shorts_data(self):
        """Obtiene la metadata de todos los shorts del canal."""
        self._log(f"🔄 Obteniendo información de {self.channel_url} ...")
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(self.channel_url, download=False)

    def _parse_video_entry(self, entry):
        """Convierte la metadata de un video en un diccionario legible."""
        return {
            "Título": entry.get("title", "N/A"),
            "Descripción": entry.get("description", "N/A"),
            "URL": entry.get("webpage_url", "N/A"),
            "ID Video": entry.get("id", "N/A"),
            "Fecha Publicación": (
                datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d")
                if entry.get("timestamp") else "N/A"
            ),
            "Duración (segundos)": entry.get("duration", 0),
            "Vistas": entry.get("view_count", 0),
            "Likes": entry.get("like_count", 0),
            "Comentarios": entry.get("comment_count", 0),
            "Miniatura": entry.get("thumbnail", "N/A"),
            "Canal": entry.get("uploader", "N/A"),
            "Suscriptores Canal": entry.get("channel_follower_count", "N/A"),
        }

    def get_shorts_dataframe(self):
        """Obtiene la información de los shorts en un DataFrame."""
        data = self._fetch_shorts_data()

        # Filtramos solo videos válidos
        videos = [
            self._parse_video_entry(entry)
            for entry in data.get("entries", [])
            if not ("_type" in entry and entry["_type"] != "url")
        ]

        df = pd.DataFrame(videos)
        self._log(f"📊 Total de shorts extraídos: {len(df)}")
        return df

    def export_to_csv(self, df=None):
        """Exporta los datos a un CSV."""
        if df is None:
            df = self.get_shorts_dataframe()
        df.to_csv(self.csv_filename, index=False, encoding="utf-8-sig")
        self._log(f"✅ Archivo generado: {self.csv_filename}")
        return self.csv_filename


if __name__ == "__main__":
    scraper = YouTubeShortsScraper(
        channel_url="https://www.youtube.com/@curiousuniverse64/shorts",
        output_dir="data",
        verbose=True
    )

    # Obtener DataFrame y exportar a CSV
    df = scraper.get_shorts_dataframe()
    scraper.export_to_csv(df)
