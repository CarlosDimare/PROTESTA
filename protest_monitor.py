import requests
from bs4 import BeautifulSoup
import zhipuai
from datetime import datetime
import json
import os
from thefuzz import fuzz
import pytz
from ddgs import DDGS

# --- Configuración ---

# La clave de API se carga de forma segura desde las variables de entorno.
API_KEY = os.getenv("ZHIPU_API_KEY")

SITIOS_A_MONITOREAR = {
    "Prensa Obrera": "https://prensaobrera.com/",
    "Mundo Gremial": "https://www.mundogremial.com/",
    "Infobae Política": "https://www.infobae.com/politica/",
    "Maria Press": "https://www.mariapress.com/",
    "La Izquierda Diario": "https://www.laizquierdadiario.com/",
    "Pagina12": "https://www.pagina12.com.ar/secciones/el-pais",
    "Iprofesional": "https://www.iprofesional.com/",
    "Anred": "https://www.anred.org/",
    "Redeco": "https://www.redeco.com.ar/",
    "El Ciudadano": "https://elciudadanoweb.com/",
    "11noticias": "https://11noticias.com/", 
    "Conclusión": "https://www.conclusion.com.ar/",
    "INFONOROESTE": "https://infonoroeste.com.ar/",
    "INFOREGION": "https://www.inforegion.com.ar/",
    "ATE" : "https://ate.org.ar/",
    "Data Gremial": "https://www.datagremial.com/"
}

# Palabras clave para identificar noticias relevantes en los titulares
KEYWORDS = ["protesta", "movilización", "corte", "piquete", "acampe", "paro", "reclamo", "manifestación", "gremial", "sindical", "marcha", "concentración", "asamblea", "repudio", "huelga"]

# --- Cerebro del Robot (Análisis con IA) ---

def analizar_noticia_con_ia(texto_noticia, fecha_referencia):
    """
    Usa el modelo de IA para analizar el texto de una noticia y extraer detalles del evento.
    """
    try:
        client = zhipuai.ZhipuAI(api_key=API_KEY)
        # Formatear la fecha en español para que el modelo la entienda mejor en contexto.
        # Si el locale 'es_ES' no está disponible en el sistema, usa un formato estándar.
        try:
            import locale
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
            fecha_actual_para_prompt = fecha_referencia.strftime("%A %d de %B de %Y")
        except locale.Error:
            fecha_actual_para_prompt = fecha_referencia.strftime("%Y-%m-%d")

        prompt = f"""
        Eres un asistente de IA experto en lucha de clases en Argentina, tu misión exclusiva es monitorear protestas e informarlo en tiempo real.
        Analiza el siguiente texto de una noticia. La fecha de referencia es {fecha_actual_para_prompt}. Tu tarea es actuar como un detective de información y descubrir si el texto describe un evento de protesta (movilización, corte, marcha, etc.) que vaya a ocurrir en el futuro (incluyendo más tarde el mismo día de la referencia).

        Si encuentras un evento futuro, tu objetivo es rellenar TODOS los campos del siguiente JSON. Sé proactivo: infiere la información del contexto si no es explícita. Es crucial que intentes completar todos los campos.

        Formato de salida OBLIGATORIO (JSON):
        {{
          "es_evento_relevante": true,
          "fecha": "YYYY-MM-DD",
          "horario": "HH:MM",
          "lugar": "Lugar específico del evento",
          "quien": "Grupo, sindicato o colectivo que organiza",
          "tipo_medida": "Tipo de medida (ej: Paro, Marcha, Movilización, Piquete, Acampe)",
          "motivo": "Resumen conciso del reclamo"
        }}

        REGLAS ESTRICTAS:
        1.  **FECHA**: La fecha del evento debe ser en formato YYYY-MM-DD. Usa la fecha de referencia para calcular fechas relativas como "mañana" o "el próximo lunes".
        2.  **TIPO DE MEDIDA**: Identifica la naturaleza de la protesta. ¿Es un "Paro" de actividades? ¿Una "Marcha" hacia un lugar? ¿Un "Piquete" o "Corte" de calle? Sé específico.
        3.  **PERSISTENCIA**: No te rindas fácilmente. Si un dato no es obvio, reléelo y trata de inferirlo. Por ejemplo, si dice "el gremio de camioneros", `quien` es "Camioneros". Si dice "frente al Congreso", `lugar` es "Congreso Nacional".
        4.  **NO ESPECIFICADO**: Usa "No especificado" como ÚLTIMO RECURSO, y solo si es absolutamente imposible deducir la información. Prioriza siempre dar un dato, aunque sea aproximado.
        5.  **EVENTOS PASADOS**: Si el texto habla de un evento que ya ocurrió (ej: "la marcha de ayer fue masiva"), ignóralo y devuelve `{{"es_evento_relevante": false}}`.

        Si el texto no contiene información sobre una protesta futura, devuelve `{{"es_evento_relevante": false}}`.

        DEVUELVE ÚNICA Y EXCLUSIVAMENTE EL OBJETO JSON SOLICITADO, SIN EXPLICACIONES, COMENTARIOS O CUALQUIER OTRO TEXTO ADICIONAL.

        Texto de la noticia a analizar:
        ---
        {texto_noticia[:4000]}
        ---
        """

        response = client.chat.completions.create(
            model="glm-4.5-flash", # Usando el modelo especificado
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        
        contenido_respuesta = response.choices[0].message.content
        # Intentamos extraer el bloque JSON de forma más robusta.
        import re
        try:
            # Primero, busca un bloque de código JSON explícito.
            match = re.search(r"```json\s*(\{.*?\})\s*```", contenido_respuesta, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                # Si no lo encuentra, busca el primer objeto JSON que aparezca.
                match = re.search(r'\{.*\}', contenido_respuesta, re.DOTALL)
                if match:
                    json_str = match.group(0)
                else:
                    raise json.JSONDecodeError("No se encontró un objeto JSON válido en la respuesta.", contenido_respuesta, 0)
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"  [!] Error al decodificar JSON de la IA: {e} - Respuesta recibida: {contenido_respuesta}")
            return {"es_evento_relevante": False}

    except Exception as e:
        print(f"  [!] Error al analizar con la IA: {e}")
        return {"es_evento_relevante": False}


# --- Web Scraper ---

def obtener_texto_articulo(url):
    """
    Obtiene el texto plano de un artículo dado su URL.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Intenta encontrar el contenido principal del artículo (esto puede necesitar ajustes por sitio)
            cuerpo_articulo = soup.find('article') or soup.find('div', class_=lambda x: x and 'content' in x) or soup.find('div', class_=lambda x: x and 'post' in x)
            if cuerpo_articulo:
                parrafos = cuerpo_articulo.find_all('p')
                return ' '.join([p.get_text() for p in parrafos])
            else: # Fallback si no encuentra una estructura clara
                return ' '.join([p.get_text() for p in soup.find_all('p')])
        return None
    except requests.RequestException as e:
        print(f"  [!] Error al obtener el artículo {url}: {e}")
        return None


def monitorear_sitio(nombre_sitio, url_base, fecha_referencia, urls_procesadas):
    """
    Busca noticias relevantes en un sitio, evitando URLs ya procesadas.
    """
    print(f"[*] Monitoreando {nombre_sitio}...")
    eventos_encontrados = []
    urls_a_analizar = set()

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url_base, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"  [!] No se pudo acceder a {nombre_sitio} (código: {response.status_code}).")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)

        for link in links:
            titulo = link.get_text().strip().lower()
            if any(keyword in titulo for keyword in KEYWORDS):
                url_articulo = link['href']
                if not url_articulo.startswith('http'):
                    from urllib.parse import urljoin
                    url_articulo = urljoin(url_base, url_articulo)
                
                # La lógica clave: ignorar si ya fue procesada
                if url_articulo not in urls_procesadas:
                    urls_a_analizar.add(url_articulo)
        
        print(f"  [-] {len(urls_a_analizar)} artículos nuevos potencialmente relevantes encontrados.")

        # Limitar la cantidad de nuevos artículos a analizar para no exceder cuotas/costos
        for url in list(urls_a_analizar)[:5]:
            print(f"  -> Analizando: {url}")
            texto = obtener_texto_articulo(url)
            if texto:
                info_evento = analizar_noticia_con_ia(texto, fecha_referencia)
                if info_evento.get("es_evento_relevante"):
                    info_evento['fuente'] = url
                    if info_evento.get('quien', 'No especificado') == 'No especificado':
                        info_evento['quien'] = nombre_sitio
                    eventos_encontrados.append(info_evento)
                    print("    [+] Evento relevante detectado.")
            # Marcar como procesada para no volver a intentarlo en esta misma ejecución
            urls_procesadas.add(url)

    except Exception as e:
        print(f"  [!] Error monitoreando {nombre_sitio}: {e}")
    
    return eventos_encontrados



def imprimir_tabla_eventos(eventos):
    """
    Imprime una lista de eventos en un formato de tabla bien alineado.
    """
    if not eventos:
        print("✅ No se encontraron eventos programados para hoy en los sitios monitoreados.")
        return

    # Definir cabeceras y claves de datos
    cabeceras = {
        "fecha": "FECHA",
        "horario": "HORA",
        "tipo_medida": "QUÉ",
        "lugar": "LUGAR",
        "quien": "QUIÉN",
        "motivo": "MOTIVO"
    }
    claves = list(cabeceras.keys())

    # Definir anchos máximos para columnas que pueden ser muy largas
    max_anchos = {
        "motivo": 50,
        "lugar": 40,
        "quien": 30
    }

    # Calcular el ancho para cada columna
    anchos = {k: len(v) for k, v in cabeceras.items()}
    for evento in eventos:
        for clave in claves:
            contenido = str(evento.get(clave, '-'))
            ancho_contenido = len(contenido)
            if clave in max_anchos and ancho_contenido > max_anchos[clave]:
                ancho_contenido = max_anchos[clave]
            if ancho_contenido > anchos[clave]:
                anchos[clave] = ancho_contenido

    # Función para truncar texto
    def truncar(texto, ancho):
        if len(texto) > ancho:
            return texto[:ancho-3] + "..."
        return texto

    # Imprimir cabecera de la tabla
    linea_cabecera = " | ".join([cabeceras[k].ljust(anchos[k]) for k in claves])
    print(linea_cabecera)
    print("-" * len(linea_cabecera))

    # Imprimir filas de datos
    for evento in eventos:
        fila = []
        for clave in claves:
            contenido = str(evento.get(clave, '-'))
            ancho_columna = anchos[clave]
            if clave in max_anchos:
                contenido_truncado = truncar(contenido, ancho_columna)
                fila.append(contenido_truncado.ljust(ancho_columna))
            else:
                fila.append(contenido.ljust(ancho_columna))
        print(" | ".join(fila))

def consolidar_eventos(eventos):
    """
    Consolida eventos duplicados de diferentes fuentes, 
    combinando la información para completarla usando fuzzy string matching.
    """
    eventos_consolidados = []
    for evento_nuevo in eventos:
        encontrado = False
        for evento_existente in eventos_consolidados:
            # Criterios de similitud usando thefuzz
            lugar_ratio = fuzz.token_sort_ratio(evento_nuevo.get('lugar', ''), evento_existente.get('lugar', ''))
            quien_ratio = fuzz.token_sort_ratio(evento_nuevo.get('quien', ''), evento_existente.get('quien', ''))
            motivo_ratio = fuzz.token_sort_ratio(evento_nuevo.get('motivo', ''), evento_existente.get('motivo', ''))

            # Considerar el mismo evento si la fecha es la misma y hay una alta similitud en lugar, quien o motivo
            if (evento_nuevo.get('fecha') == evento_existente.get('fecha') and 
                (lugar_ratio > 80 or quien_ratio > 80 or motivo_ratio > 85)):
                
                # Es el mismo evento, consolidamos la información
                for clave in ['horario', 'lugar', 'quien', 'motivo']:
                    if evento_existente.get(clave) == 'No especificado' and evento_nuevo.get(clave) != 'No especificado':
                        evento_existente[clave] = evento_nuevo.get(clave)
                
                # Agregamos la nueva fuente a la lista de fuentes
                if isinstance(evento_existente.get('fuente'), list):
                    if evento_nuevo.get('fuente') not in evento_existente['fuente']:
                        evento_existente['fuente'].append(evento_nuevo.get('fuente'))
                else: 
                    evento_existente['fuente'] = [evento_existente.get('fuente'), evento_nuevo.get('fuente')]
                
                encontrado = True
                break
        
        if not encontrado:
            eventos_consolidados.append(evento_nuevo)
            
    # Convertir las listas de fuentes a strings para la impresión
    for evento in eventos_consolidados:
        if isinstance(evento.get('fuente'), list):
            evento['fuente'] = ", ".join(evento['fuente'])
            
    return eventos_consolidados

def buscar_datos_faltantes(evento, fecha_referencia):
    """
    Intenta encontrar datos faltantes (como el horario) para un evento 
    realizando una búsqueda web experimental.
    """
    if evento.get('horario', 'No especificado') != 'No especificado':
        return evento # No hay nada que buscar

    print(f"  [?] Buscando horario para el evento en '{evento.get('lugar')}'...")
    
    # Construir una consulta de búsqueda más natural y detallada
    motivo_corto = ' '.join(evento.get('motivo', '').split()[:5]) # Usar las primeras 5 palabras del motivo
    query = f"a qué hora es la protesta de {evento.get('quien', '')} en {evento.get('lugar', '')} el {evento.get('fecha', '')} por {motivo_corto}"
    
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=3))

        if not resultados:
            print("    [!] No se encontraron resultados en la búsqueda web.")
            return evento

        for resultado in resultados:
            url = resultado['href']
            print(f"    -> Analizando resultado de búsqueda: {url}")
            texto = obtener_texto_articulo(url)
            if texto:
                # Usamos la IA con un prompt enfocado solo en el horario
                prompt_horario = f"""
                Analiza el siguiente texto y dime SOLAMENTE la hora de inicio del evento de protesta. 
                La hora debe estar en formato HH:MM. Si no encuentras una hora, responde 'No especificado'.
                
                Texto:
                ---
                {texto[:4000]}
                ---
                """
                client = zhipuai.ZhipuAI(api_key=API_KEY)
                response = client.chat.completions.create(
                    model="glm-4.5-flash",
                    messages=[
                        {"role": "user", "content": prompt_horario}
                    ],
                )
                horario_encontrado = response.choices[0].message.content.strip()

                if horario_encontrado != 'No especificado':
                    print(f"      [+] ¡Horario encontrado!: {horario_encontrado}")
                    evento['horario'] = horario_encontrado
                    # Opcional: añadir la nueva fuente
                    if isinstance(evento.get('fuente'), str):
                        evento['fuente'] += ", " + url
                    return evento # Devolvemos el evento actualizado en cuanto encontramos el dato

    except Exception as e:
        print(f"    [!] Error durante la búsqueda de datos faltantes: {e}")

    return evento



def guardar_eventos_para_web(todos_los_eventos):
    """
    Guarda todos los eventos consolidados en un único archivo JSON para la web.
    """
    # Estructura final para el JSON
    output_data = {
        "last_updated": datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).isoformat(),
        "events": todos_los_eventos
    }

    try:
        with open('protests.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print("\n[💾] Base de datos de eventos guardada correctamente en protests.json.")
    except Exception as e:
        print(f"\n[!] Error al guardar el archivo JSON: {e}")

def get_processed_urls(eventos):
    """Extrae todas las URLs de fuentes de una lista de eventos."""
    urls = set()
    for evento in eventos:
        fuente = evento.get('fuente')
        if not fuente:
            continue
        
        if isinstance(fuente, list):
            for url in fuente:
                urls.add(url)
        elif isinstance(fuente, str):
            # Las fuentes pueden ser un string de URLs separadas por coma
            urls.update(u.strip() for u in fuente.split(','))
    return urls

def main():
    # Configurar la zona horaria de Argentina
    try:
        tz_argentina = pytz.timezone('America/Argentina/Buenos_Aires')
    except pytz.UnknownTimeZoneError:
        print("[!] No se pudo encontrar la zona horaria 'America/Argentina/Buenos_Aires'. Usando la hora local del sistema.")
        tz_argentina = None

    fecha_actual = datetime.now(tz_argentina)
    print(f"🤖 Iniciando Robot de Monitoreo de Protestas (Hora de Argentina: {fecha_actual.strftime('%Y-%m-%d %H:%M:%S')})...")

    # --- Cargar eventos históricos y URLs ya procesadas ---
    eventos_historicos = []
    urls_ya_procesadas = set()
    if os.path.exists('protests.json'):
        try:
            with open('protests.json', 'r', encoding='utf-8') as f:
                datos_viejos = json.load(f)
                eventos_historicos = datos_viejos.get('events', [])
                urls_ya_procesadas = get_processed_urls(eventos_historicos)
            print(f"🔍 Cargados {len(eventos_historicos)} eventos del historial. Se ignorarán {len(urls_ya_procesadas)} URLs ya procesadas.")
        except (json.JSONDecodeError, FileNotFoundError):
            print("[!] No se encontró historial de eventos o el archivo está dañado. Se creará uno nuevo.")
            eventos_historicos = []

    print(f"🗓️  Buscando nuevos eventos...")

    eventos_nuevos = []
    for nombre, url in SITIOS_A_MONITOREAR.items():
        eventos_nuevos.extend(monitorear_sitio(nombre, url, fecha_actual, urls_ya_procesadas))

    if not eventos_nuevos:
        print("\n✅ No se encontraron nuevos eventos en esta corrida.")
    else:
        print(f"\n🔄 Consolidando {len(eventos_nuevos)} eventos nuevos con {len(eventos_historicos)} del historial...")
    
    # --- Consolidar y completar datos ---
    eventos_a_consolidar = eventos_nuevos + eventos_historicos
    eventos_consolidados = consolidar_eventos(eventos_a_consolidar)

    eventos_completos = []
    fecha_actual_str = fecha_actual.strftime("%Y-%m-%d")
    for evento in eventos_consolidados:
        # Solo buscar datos faltantes para eventos futuros o de hoy para no gastar API en eventos viejos
        if evento.get('fecha', '') >= fecha_actual_str:
            # Y solo si el evento es uno de los recién encontrados
            if any(evento_nuevo['fuente'] in evento.get('fuente', '') for evento_nuevo in eventos_nuevos):
                 evento_actualizado = buscar_datos_faltantes(evento, fecha_actual)
                 eventos_completos.append(evento_actualizado)
            else:
                eventos_completos.append(evento)
        else:
            eventos_completos.append(evento)

    # --- Ordenar y mostrar ---
    eventos_completos.sort(key=lambda x: (x.get('fecha', '9999-12-31'), x.get('horario', '99:99')))
    
    print("\n" + "="*80)
    print(f"FIXTURE DE PROTESTAS COMPLETO".center(80))
    print("="*80 + "\n")
    imprimir_tabla_eventos(eventos_completos)

    # --- GUARDAR DATOS PARA LA WEB ---
    guardar_eventos_para_web(eventos_completos)

    print("\n🤖 Monitoreo finalizado.")

if __name__ == "__main__":
    main()
