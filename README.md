# Monitor de Protestas

## Descripción

Este proyecto es un sistema automatizado para monitorear, analizar y presentar información sobre protestas, movilizaciones y otros eventos de reclamo en Argentina. Utiliza un script de Python para rastrear sitios de noticias, extrae información relevante mediante inteligencia artificial y la presenta en una interfaz web simple y clara.

## Características Principales

-   **Monitoreo Automatizado:** Rastrea múltiples sitios de noticias y agencias de forma automática en busca de artículos sobre protestas.
-   **Análisis con IA:** Utiliza un modelo de lenguaje (LLM) para leer las noticias y extraer datos estructurados como fecha, hora, lugar, organizadores y motivo del evento.
-   **Consolidación de Datos:** Identifica y fusiona eventos duplicados reportados por diferentes fuentes para crear un listado único y coherente.
-   **Búsqueda de Información Faltante:** Intenta completar datos no especificados (como el horario) realizando búsquedas web adicionales.
-   **Interfaz Web Clara:** Muestra los eventos en una página web con pestañas para "Ayer", "Hoy" y "Mañana".
-   **Estado del Evento:** Calcula y muestra dinámicamente si un evento está "Programado", "En desarrollo" o "Finalizado".
-   **Fuente Original:** Permite acceder fácilmente al artículo original desde donde se extrajo la información.

## Cómo Funciona

El sistema se compone de dos partes principales:

1.  **Backend (Python):** El script `protest_monitor.py` se encarga de:
    *   Visitar los sitios web definidos en `SITIOS_A_MONITOREAR`.
    *   Buscar artículos que contengan palabras clave relacionadas con protestas.
    *   Enviar el texto de los artículos a una API de IA (`ZhipuAI`) para su análisis y extracción de datos.
    *   Consolidar los resultados, eliminar duplicados y enriquecer la información.
    *   Guardar todos los eventos en el archivo `protests.json`.

2.  **Frontend (HTML/CSS/JS):** La interfaz web (`index.html`, `style.css`, `script.js`):
    *   Lee el archivo `protests.json` para obtener los datos de los eventos.
    *   Clasifica los eventos en las pestañas "Ayer", "Hoy" y "Mañana".
    *   Renderiza la información en tablas fáciles de leer.
    *   Actualiza el estado de los eventos en tiempo real y gestiona la interactividad (ver fuentes, etc.).

## Instalación y Uso

Sigue estos pasos para poner en marcha el monitor en tu propio entorno:

1.  **Clonar el Repositorio:**
    ```bash
    git clone https://github.com/tu-usuario/tu-repositorio.git
    cd tu-repositorio
    ```

2.  **Instalar Dependencias de Python:**
    Asegúrate de tener Python 3 instalado. Luego, instala las librerías necesarias:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configurar la Clave de API:**
    El script utiliza la API de ZhipuAI. Necesitas obtener una clave de API y configurarla como una variable de entorno.

    En Linux/macOS:
    ```bash
    export ZHIPU_API_KEY="tu_api_key_aqui"
    ```

    En Windows:
    ```bash
    set ZHIPU_API_KEY="tu_api_key_aqui"
    ```

4.  **Ejecutar el Monitor:**
    Para iniciar el proceso de monitoreo y generar/actualizar el archivo `protests.json`, ejecuta:
    ```bash
    python protest_monitor.py
    ```
    El script imprimirá en la consola los eventos que vaya encontrando.

5.  **Ver los Resultados:**
    Abre el archivo `index.html` en tu navegador web para ver el monitor de protestas en acción.

## Tecnologías Utilizadas

-   **Backend:**
    -   Python
    -   `requests` (para peticiones HTTP)
    -   `BeautifulSoup4` (para web scraping)
    -   `zhipuai` (para la integración con el modelo de IA)
    -   `thefuzz` (para la consolidación de eventos duplicados)
    -   `python-dateutil`, `pytz` (para manejo de fechas y zonas horarias)
    -   `ddgs` (para búsquedas web)

-   **Frontend:**
    -   HTML5
    -   CSS3
    -   JavaScript (Vanilla)
