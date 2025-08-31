import json
from openai import OpenAI
import google.generativeai as genai
import re
import time


class GuionGeneratorConfigurable:
    def __init__(self, openai_key: str, gemini_key: str):
        self.client = OpenAI(api_key=openai_key)
        genai.configure(api_key=gemini_key)
        self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")

    def generar_prompt_una_consulta(self, data: dict, num_guiones: int) -> str:
        """Genera prompt para obtener múltiples guiones en una consulta."""
        return f"""
Crea EXACTAMENTE {num_guiones} guiones completamente diferentes para un short de "{data['title']}" (categoría: {data['categoria']}).
La descripción del guion es: {data['description']}
Cada guión debe tener un enfoque único y ser totalmente diferente de los otros.
La duración aproximada del guión debe ser de {data['duration_target']} segundos.
Las imágenes deben de ser de cosas que se mencionan en el guión cada aproximadamente 5 a 10 palabras, las cosas más importantes a las que se esté haciendo referencia.
Las imágenes principales deben ser de elementos clave del guión, como personajes, objetos específicos, lugares o escenarios importantes (ejem: roberto bolaños, paris 1944, tratado de versalles, hipocampo, ps4 slim azul).
Las imágenes complementarias pueden incluir conceptos más simples (ejem: agua, vida, jugos, persona, mariposa, rana, etc.)

FORMATO ESTRICTO PARA CADA GUIÓN:

## GUIÓN [NÚMERO]: [Título único]

**Alternativas de Título:**
1. [Título A - máximo 4 palabras]
2. [Título B - máximo 4 palabras]

**Desarrollo ({data['duration_target']} segundos):**

[Hook impactante único] (Preferentemente una frase que en las primeras 2-3 palabras capte la atención)
[Contenido principal diferente]
[Más detalles únicos]
[CTA diferente que invite a comentar]

**Imágenes Principales (de google):**
["específica1", "específica2", "específica3", "específica4", "específica5"]

**Imágenes Complementarias (de galerías):**
["concepto1", "concepto2", "concepto3", "concepto4", "concepto5"]

**Tags (10):**
tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10

---

SEPARADOR ENTRE GUIONES: ===NUEVO_GUION===

INSTRUCCIONES CRÍTICAS:
- Cada guión debe abordar el tema desde un ángulo COMPLETAMENTE diferente
- Lanza datos como fechas, contexto, etc.
- Los {num_guiones} guiones deben ser únicos y no repetir conceptos
- Video misterioso, profundo y atrapante
- Títulos que enganchen desde las primeras 2-3 palabras
- Se deben lanzar datos cada 3 a 5 segundos
- No agregar en el guion marcas de tiempo (duración de cada parte), solo separa la frase de enganche, desarrollos y cierre
- Quiero que el guión te invite de alguna forma a comentar / debatir, además de la invitación directa al final de el guión
Indicaciones extra: {data['inidicaciones_extra']}
        """

    def generar_prompt_individual(self, data: dict, numero_guion: int, total_guiones: int) -> str:
        """Genera prompt para UN guion específico."""
        enfoques = {
            1: "enfócate en el aspecto más misterioso y sorprendente",
            2: "aborda el tema desde una perspectiva científica/técnica",
            3: "explora el lado histórico o de consecuencias",
            4: "analiza desde el impacto humano/social",
            5: "revela secretos o datos desconocidos"
        }
        
        enfoque = enfoques.get(numero_guion, f"usa un enfoque único #{numero_guion}")
        
        return f"""
Crea UN SOLO guión completo (Guión #{numero_guion} de {total_guiones}) para el video "{data['title']}" (categoría: {data['categoria']}).

ENFOQUE ESPECÍFICO: {enfoque}
La descripción del guion es: {data['description']}
La duración aproximada del guión debe ser de {data['duration_target']} segundos.
Las imágenes deben de ser de cosas que se mencionan en el guión cada aproximadamente 5 a 10 palabras, las cosas más importantes a las que se esté haciendo referencia.
Las imágenes principales deben ser de elementos clave del guión, como personajes, objetos específicos, lugares o escenarios importantes (ejem: roberto bolaños, paris 1944, tratado de versalles, hipocampo, ps4 slim azul).
Las imágenes complementarias pueden incluir conceptos más simples (ejem: agua, vida, jugos, persona, mariposa, rana, etc.)

FORMATO REQUERIDO:
## GUIÓN #{numero_guion}: [Título Creativo]

**Alternativas de Título:**
1. [Título 1 - máximo 4 palabras]
2. [Título 2 - máximo 4 palabras]

**Desarrollo Completo ({data['duration_target']} segundos):**

[Frase impactante que haga que no puedan dejar de ver] (Preferentemente una frase que en las primeras 2-3 palabras capte la atención)

[Explicación clara, entretenida y profunda del tema]

[Más detalles específicos y fascinantes]

[CTA atractivo que invite a seguir viendo más y comentar]

**Lista 1 - Imágenes Principales:**
["imagen específica 1", "lugar/persona 2", "objeto/concepto 3", "imagen específica 4", "elemento visual 5"]

**Lista 2 - Imágenes Complementarias:**
["concepto visual 1", "ambiente 2", "contexto 3", "elemento 4", "atmósfera 5"]

**Tags (10):**
[tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10]

INSTRUCCIONES:
- Video misterioso, profundo y atrapante
- Lanza datos como fechas, contexto, etc.
- Títulos que enganchen desde las primeras 2-3 palabras
- Se deben lanzar datos cada 3 a 5 segundos
- No agregar en el guion marcas de tiempo (duración de cada parte), solo separa la frase de enganche, desarrollos y cierre
- NO repitas conceptos si sabes que hay otros guiones
- Debe ser completamente diferente a otros enfoques
- Quiero que el guión te invite de alguna forma a comentar / debatir, además de la invitación directa al final de el guión
Indicaciones extra: {data['inidicaciones_extra']}
        """

    def generar_chatgpt(self, prompt: str) -> str:
        """Genera contenido usando ChatGPT."""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un experto guionista de videos cortos y virales. Crea EXACTAMENTE el formato solicitado sin desviaciones."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1500
        )
        return response.choices[0].message.content.strip()

    def generar_gemini(self, prompt: str) -> str:
        """Genera contenido usando Gemini."""
        return self.gemini_model.generate_content(prompt).text.strip()

    def parsear_guiones_una_consulta(self, contenido: str, num_esperados: int) -> list:
        """Extrae guiones individuales de una respuesta combinada."""
        guiones = []
        
        # Intentar separar por el separador específico
        if "===NUEVO_GUION===" in contenido:
            partes = contenido.split("===NUEVO_GUION===")
            for i, parte in enumerate(partes):
                if parte.strip():
                    guiones.append(f"## GUIÓN {len(guiones)+1}:\n{parte.strip()}")
        
        # Fallback: separar por patrones de guión
        if len(guiones) < num_esperados:
            guiones = []
            patrones = [
                r"## GUIÓN \d+:",
                r"# GUIÓN \d+:",
                r"\*\*GUIÓN \d+:",
                r"GUIÓN \d+:"
            ]
            
            for patron in patrones:
                matches = re.split(patron, contenido, flags=re.IGNORECASE)
                if len(matches) > 1:
                    for i, match in enumerate(matches[1:], 1):
                        if match.strip():
                            guiones.append(f"## GUIÓN {i}:\n{match.strip()}")
                    break
        
        # Último recurso: dividir por separadores comunes
        if len(guiones) < num_esperados:
            separadores = ["---", "====", "###", "***"]
            for sep in separadores:
                partes = contenido.split(sep)
                if len(partes) >= num_esperados:
                    guiones = []
                    for i, parte in enumerate(partes[:num_esperados], 1):
                        if parte.strip():
                            guiones.append(f"## GUIÓN {i}:\n{parte.strip()}")
                    break

        return guiones[:num_esperados]

    def generar_guiones_separados(self, data: dict, num_guiones: int, usar_gemini=True, usar_gpt=False):
        """Genera guiones con consultas separadas."""
        guiones = []
        
        for i in range(1, num_guiones + 1):
            print(f"\n⚡ Generando Guión #{i} de {num_guiones}...")
            prompt = self.generar_prompt_individual(data, i, num_guiones)
            
            if usar_gemini:
                guion = self.generar_gemini(prompt)
                guiones.append(f"=== GUIÓN #{i} (Gemini) ===\n{guion}")
            
            if usar_gpt:
                guion = self.generar_chatgpt(prompt)
                guiones.append(f"=== GUIÓN #{i} (ChatGPT) ===\n{guion}")
            
            # Pausa para evitar rate limits
            if i < num_guiones:
                time.sleep(1)
        
        return guiones

    def generar_guiones_una_consulta(self, data: dict, num_guiones: int, usar_gemini=True, usar_gpt=False):
        """Genera múltiples guiones en una sola consulta."""
        guiones = []
        prompt = self.generar_prompt_una_consulta(data, num_guiones)
        
        if usar_gemini:
            print(f"\n⚡ Generando {num_guiones} guiones en una consulta (Gemini)...")
            contenido = self.generar_gemini(prompt)
            guiones_parseados = self.parsear_guiones_una_consulta(contenido, num_guiones)
            
            for i, guion in enumerate(guiones_parseados, 1):
                guiones.append(f"=== GUIÓN #{i} (Gemini) ===\n{guion}")
        
        if usar_gpt:
            print(f"\n⚡ Generando {num_guiones} guiones en una consulta (ChatGPT)...")
            contenido = self.generar_chatgpt(prompt)
            guiones_parseados = self.parsear_guiones_una_consulta(contenido, num_guiones)
            
            for i, guion in enumerate(guiones_parseados, 1):
                guiones.append(f"=== GUIÓN #{i} (ChatGPT) ===\n{guion}")
        
        return guiones

    @staticmethod
    def mostrar_guiones(guiones: list):
        """Muestra los guiones generados."""
        print("\n" + "="*60)
        print("🎬 GUIONES GENERADOS")
        print("="*60)
        
        for i, guion in enumerate(guiones, 1):
            print(f"\n[{i}] " + "="*50)
            print(guion)
            print("="*50)

    @staticmethod
    def guardar_guiones(guiones: list, title_archivo="guiones_seleccionados.txt"):
        """Guarda los guiones seleccionados."""
        if not guiones:
            print("\n❌ No hay guiones para guardar.")
            return
            
        with open(title_archivo, "w", encoding="utf-8") as f:
            f.write("\n\n" + "="*80 + "\n\n".join(guiones))
        print(f"\n✅ Guiones guardados en {title_archivo}")

    def run(self, json_path="video.json", consultas_separadas=False, usar_gemini=True, usar_gpt=False):
        """
        Ejecuta el generador con configuración flexible.
        
        Args:
            json_path: Ruta al archivo JSON con la configuración
            consultas_separadas: True para consultas separadas, False para una sola consulta
            usar_gemini: Usar Gemini API
            usar_gpt: Usar ChatGPT API
        """
        # Validaciones
        if not (usar_gemini or usar_gpt):
            print("❌ Error: Debe habilitar al menos una API (Gemini o ChatGPT)")
            return
        # 1. Leer configuración
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ Error: No se encontró el archivo {json_path}")
            return
        except json.JSONDecodeError:
            print(f"❌ Error: El archivo {json_path} no es un JSON válido")
            return

        num_guiones = int(data.get("num_guiones", 1))
        if not (1 <= num_guiones <= 5):
            print("❌ Error: num_guiones debe estar entre 1 y 5")
            return
        
        # 2. Mostrar configuración
        print(f"\n🎯 Configuración:")
        print(f"   📁 Video: {data['title']}")
        print(f"   📂 Categoría: {data['categoria']}")
        print(f"   ⏱️ Duración: {data['duration_target']}")
        print(f"   📊 Guiones: {num_guiones}")
        print(f"   🔄 Método: {'Consultas separadas' if consultas_separadas else 'Una consulta'}")
        print(f"   🤖 APIs: {'Gemini ' if usar_gemini else ''}{'ChatGPT' if usar_gpt else ''}")

        # 3. Generar guiones según configuración
        if consultas_separadas:
            guiones = self.generar_guiones_separados(data, num_guiones, usar_gemini, usar_gpt)
        else:
            guiones = self.generar_guiones_una_consulta(data, num_guiones, usar_gemini, usar_gpt)

        if not guiones:
            print("\n❌ No se pudieron generar guiones.")
            return

        # 4. Mostrar resultados
        self.mostrar_guiones(guiones)

        # 5. Selección interactiva
        while True:
            try:
                print(f"\n📋 Opciones disponibles:")
                for i in range(1, len(guiones) + 1):
                    print(f"   {i} - Guión #{i}")
                print(f"   todos - Todos los guiones")
                
                seleccion = input(f"\n✏️ Selecciona los guiones (ej: 1,3 o todos): ").strip()
                
                if seleccion.lower() in ['todos', 'all']:
                    guiones_seleccionados = guiones
                    break
                
                # Procesar selección numérica
                indices = []
                for num in seleccion.split(","):
                    num = num.strip()
                    if num.isdigit():
                        indice = int(num) - 1
                        if 0 <= indice < len(guiones):
                            indices.append(indice)
                        else:
                            print(f"⚠️ Número {num} fuera de rango (1-{len(guiones)})")
                
                if indices:
                    guiones_seleccionados = [guiones[i] for i in indices]
                    break
                else:
                    print("❌ Selección inválida. Intenta de nuevo.")
                    
            except Exception as e:
                print(f"❌ Error en selección: {e}")

        # 6. Guardar resultados
        if guiones_seleccionados:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            title_archivo = f"guiones_{timestamp}.txt"
            self.guardar_guiones(guiones_seleccionados, title_archivo)
            print(f"\n🎉 Proceso completado exitosamente!")
            print(f"   📄 {len(guiones_seleccionados)} guion(es) guardados")
            print(f"   📁 Archivo: {title_archivo}")
        else:
            print("\n❌ No se seleccionaron guiones para guardar.")


if __name__ == "__main__":
    # === CONFIGURACIÓN DE APIs ===
    from dotenv import load_dotenv
    import os
    
    load_dotenv()

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # === EJEMPLOS DE USO ===
    generador = GuionGeneratorConfigurable(OPENAI_API_KEY, GEMINI_API_KEY)
    
    # Ejemplo 1: Configuración por defecto (1 guión, una consulta, solo Gemini)
    # generador.run()
    
    # Ejemplo 2: 3 guiones, consultas separadas, solo Gemini
    # generador.run(consultas_separadas=True, num_guiones=3)
    
    # Ejemplo 3: 2 guiones, una consulta, ambas APIs
    # generador.run(num_guiones=2, usar_gemini=True, usar_gpt=True)
    
    # Ejemplo 4: Configuración personalizada completa
    generador.run(
        json_path="video.json",
        consultas_separadas=False,  # False = una consulta (por defecto)
        usar_gemini=True,           # Gemini habilitado (por defecto)
        usar_gpt=False              # ChatGPT deshabilitado (por defecto)
    )