¡Absolutamente\! Aquí tienes el archivo `main.py` completo y **corregido**. Por favor, **reemplaza TODO el contenido de tu archivo `main.py` con este código.** Este incluye la corrección del `SyntaxError` que veíamos, las mejoras de la IA para metacognición y calibración de nota 7.0, y la preparación para la memoria de aprendizaje.

````python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx, os
from supabase import create_client, Client
import asyncio # Necesario para el asyncio.sleep

# --- Configuración de Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = None

# Debug: Verifica si las variables están presentes
print("DEBUG - MISTRAL_API_KEY:", os.getenv("MISTRAL_API_KEY"))
print("DEBUG - AZURE_VISION_KEY:", os.getenv("AZURE_VISION_KEY"))
print("DEBUG - AZURE_VISION_ENDPOINT:", os.getenv("AZURE_VISION_ENDPOINT"))
print("DEBUG - SUPABASE_URL:", SUPABASE_URL)
print("DEBUG - SUPABASE_KEY:", SUPABASE_KEY)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    global supabase
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("Supabase client initialized.")
        except Exception as e:
            print(f"ERROR: Could not initialize Supabase client: {e}")
            supabase = None
    else:
        print("WARNING: SUPABASE_URL or SUPABASE_KEY not set. Supabase features will be disabled.")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# Modelo de datos para la solicitud de evaluación desde el frontend
class EvaluacionRequest(BaseModel):
    alumno: str
    evaluacion: str # El texto del estudiante
    rubrica: str    # La rúbrica
    curso: str
    nombrePrueba: str
    flexibilidadIA: int
    notaMinima: float
    prompt: str # El prompt completo generado en el frontend (para retroalimentación general/rúbricas)

@app.post("/evaluar")
async def evaluar(data: EvaluacionRequest):
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_key:
        raise HTTPException(status_code=500, detail={"error": "Clave MISTRAL_API_KEY no definida"})

    # --- Lógica de Metacognición y Calibración de Nota 7.0 ---
    metacognition_directives = """
    ### DIRECTIVAS CLAVE PARA LA EVALUACIÓN (METAGOGNACIÓN PEDAGÓGICA) ###
    Actúa como un docente experto y empático que comprende profundamente la situación contextual y pedagógica de cada estudiante. Tu juicio es profesional y tu feedback, constructivo.

    1.  **Juicio Global y Calibración de Nota (Escala Chilena 1.0 a 7.0):**
        * Antes de asignar puntajes, forma una *impresión holística y justa* del trabajo del estudiante (ej. Excelente, Muy Bueno, Suficiente, Insuficiente).
        * **CALIBRA tus puntajes y la `nota_sugerida_ia` para que coincidan con esta impresión global y la escala chilena (1.0 a 7.0).**
        * **Nota 7.0 (Excelencia):** RESÉRVALA para trabajos que **superan significativamente las expectativas**, demuestran un **dominio sobresaliente, originalidad, creatividad o una profundidad analítica excepcional**. No es solo un trabajo perfecto, es inspirador.
        * **Nota 4.0 (Aprobación Mínima):** Debe reflejar el cumplimiento básico de los requisitos, con fallos pero que permiten la aprobación.
        * **Considera los porcentajes de exigencia estándar y la transformación a nota chilena para una calibración realista.**
    2.  **Valoración del Esfuerzo y Progreso:**
        * Si el contexto del curso o la prueba sugiere adaptaciones (Diferenciada, PIE, Apoyo, Adecuación), sé **más generoso con los puntajes parciales** y en tu juicio global.
        * Enfoca el feedback en los logros, el progreso y los próximos pasos realistas, valorando el esfuerzo por encima de la perfección absoluta cuando el contexto lo justifique.
    3.  **Retroalimentación Formativa y Justificación con Citas:**
        * Ofrece siempre feedback constructivo y útil.
        * Tanto en "Puntos Fuertes" como en "Sugerencias de Mejora" (o análisis por criterio), **justifica tus afirmaciones citando fragmentos específicos (5-15 palabras) del propio texto del estudiante como evidencia.**
        * Asegura que los "Sugerencias de Mejora" sean pasos concretos, claros y alcanzables.

    """
    
    # --- Recuperar instrucciones de retroalimentación a la IA desde Supabase ---
    instrucciones_adicionales_ia = ""
    if supabase:
        try:
            # Buscar instrucciones generales
            res_general = await supabase.table("retroalimentacion_ia").select("instruccion").eq("tipo_contexto", "general").execute()
            for item in res_general.data:
                instrucciones_adicionales_ia += f"- General: {item['instruccion']}\n"

            # Buscar instrucciones por curso
            if data.curso:
                res_curso = await supabase.table("retroalimentacion_ia").select("instruccion").eq("tipo_contexto", "curso").eq("id_contexto", data.curso.lower()).execute()
                for item in res_curso.data:
                    instrucciones_adicionales_ia += f"- Curso '{data.curso}': {item['instruccion']}\n"
            
            # Buscar instrucciones por alumno
            if data.alumno:
                res_alumno = await supabase.table("retroalimentacion_ia").select("instruccion").eq("tipo_contexto", "alumno").eq("id_contexto", data.alumno.lower()).execute()
                for item in res_alumno.data:
                    instrucciones_adicionales_ia += f"- Alumno '{data.alumno}': {item['instruccion']}\n"
            
            if instrucciones_adicionales_ia:
                instrucciones_adicionales_ia = "### INSTRUCCIONES ADICIONALES DEL DOCENTE PARA LA IA (APRENDIZAJE) ###\n" + instrucciones_adicionales_ia + "\n"
                print(f"DEBUG: Se encontraron instrucciones adicionales para la IA:\n{instrucciones_adicionales_ia}")

        except Exception as e:
            print(f"WARNING: Error al recuperar instrucciones de IA de Supabase: {e}")
            instrucciones_adicionales_ia = ""


    # Lógica de contexto pedagógico desde el frontend (mantenida y reforzada)
    context_prompt_from_frontend = ""
    # El frontend ya construye el contextoPrompt y lo incluye en data.prompt para la evaluación principal
    # Aquí lo vamos a reconstruir para asegurar consistencia y permitir que nuestro prompt sea la fuente de verdad
    curso_lower = data.curso.lower()
    nombre_prueba_lower = data.nombrePrueba.lower()

    if "diferenciada" in curso_lower or "diferenciada" in nombre_prueba_lower or \
       "pie" in curso_lower or "pie" in nombre_prueba_lower or \
       "adecuación" in curso_lower or "adecuación" in nombre_prueba_lower:
        context_prompt_from_frontend = "Has detectado que esta es una evaluación con consideraciones especiales (diferenciada, PIE, adecuación). Tu evaluación debe ser extremadamente comprensiva y formativa."
    elif "superior" in curso_lower or "universidad" in nombre_prueba_lower or \
         "tesis" in nombre_prueba_lower or "investigación avanzada" in nombre_prueba_lower:
        context_prompt_from_frontend = "Has detectado que esta es una evaluación de nivel superior. Espera un análisis crítico profundo, argumentación sólida y un lenguaje académico. Sé riguroso en tu feedback."
    elif "inicial" in curso_lower or "prekinder" in curso_lower or \
         "kinder" in curso_lower or "juego" in nombre_prueba_lower or \
         "actividad lúdica" in nombre_prueba_lower:
        context_prompt_from_frontend = "Has detectado que esta es una evaluación para educación inicial. Enfócate en el desarrollo de habilidades básicas, la participación y la creatividad. Usa un lenguaje muy simple y positivo."

    if context_prompt_from_frontend:
        context_prompt_from_frontend = "### CONTEXTO PEDAGÓGICO AUTOMÁTICO ###\n" + context_prompt_from_frontend + "\n"


    # Estilo de flexibilidad (desde el slider del frontend)
    flexibility_description = ""
    if 0 <= data.flexibilidadIA <= 2:
        flexibility_description = "Eres un evaluador extremadamente RÍGIDO y LITERAL en tu análisis."
    elif 3 <= data.flexibilidadIA <= 7:
        flexibility_description = "Eres un evaluador EQUILIBRADO en tu análisis, buscando un balance entre rigor y comprensión."
    elif 8 <= data.flexibilidadIA <= 10:
        flexibility_description = "Eres un evaluador muy FLEXIBLE y HOLÍSTICO. Valora la intención y el panorama general más que los pequeños detalles."
    
    if flexibility_description:
        flexibility_description = f"### NIVEL DE FLEXIBILIDAD DEL DOCENTE (AJUSTE) ###\n{flexibility_description}\n"


    final_prompt_to_mistral = f"""
    {metacognition_directives}
    {instrucciones_adicionales_ia}
    {context_prompt_from_frontend}
    {flexibility_description}

    ### INFORMACIÓN DE LA EVALUACIÓN ###
    - Alumno: "{data.alumno}"
    - Curso/Asignatura: "{data.curso}"
    - Nombre de la Prueba/Actividad: "{data.nombrePrueba}"
    - Rúbrica:
    ```
    {data.rubrica}
    ```
    - Texto del estudiante a evaluar:
    ```
    {data.evaluacion}
    ```

    ### TAREA Y FORMATO DE SALIDA JSON (OBLIGATORIO) ###
    Responde ÚNICAMENTE con un objeto JSON válido con la siguiente estructura, asegurando que todas las justificaciones usen citas del texto del estudiante:
    {{
        "feedback_general": "Resumen conciso y empático del desempeño general del estudiante.",
        "analisis_por_criterio": {{
            "Criterio 1": "Análisis del desempeño en este criterio, incluyendo puntaje y justificación con cita del texto. Ej: 'Claridad (3/5): El estudiante presenta ideas claras como en \"ideas claras y bien expresadas\".'",
            "Criterio 2": "..."
        }},
        "puntaje_calculado_ia": "Puntaje numérico total obtenido según la rúbrica.",
        "escala_puntaje": "El puntaje máximo total de la rúbrica.",
        "nota_sugerida_ia": "La nota sugerida en escala 1.0 a 7.0, calibrada según las directivas de metacognición.",
        "sugerencias_mejora": [
            {{ "descripcion": "Sugerencia concreta.", "cita": "Cita relevante del texto." }},
            {{ "descripcion": "...", "cita": "..." }}
        ],
        "puntos_fuertes": [
            {{ "descripcion": "Punto fuerte específico.", "cita": "Cita relevante del texto." }},
            {{ "descripcion": "...", "cita": "..." }}
        ]
    }}
    Asegúrate de que todas las citas sean exactas y provengan del 'Texto del estudiante a evaluar'.
    """

    headers = {"Authorization": f"Bearer {mistral_key}"}
    body = {
        "model": "mistral-large-latest", # O el modelo más adecuado que tengas
        "messages": [{"role": "user", "content": final_prompt_to_mistral}],
        "response_format": {"type": "json_object"}
    }
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post("https://api.mistral.ai/v1/chat/completions", json=body, headers=headers, timeout=120.0)
            res.raise_for_status()
            return res.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail={"error": f"Error de red o timeout al conectar con Mistral: {exc}"})
        except httpx.HTTPStatusError as exc:
            error_detail = exc.response.text
            try:
                error_json = exc.response.json()
                error_detail = error_json.get("message", error_detail)
            except ValueError:
                pass
            raise HTTPException(status_code=exc.response.status_code, detail={"error": f"Error de la API de Mistral ({exc.response.status_code}): {error_detail}"})
        except Exception as exc:
            raise HTTPException(status_code=500, detail={"error": f"Error inesperado al evaluar con Mistral: {type(exc).__name__} - {exc}"})

# --- Modelo para la retroalimentación a la IA ---
class FeedbackIA(BaseModel):
    timestamp: int
    tipo_contexto: str # 'alumno', 'curso', 'general'
    id_contexto: str   # Nombre del alumno o curso, o 'general'
    instruccion: str   # La instrucción/retroalimentación del profesor para la IA

@app.post("/retroalimentacion_ia") # NUEVO: Endpoint para guardar retroalimentación a la IA
async def guardar_retroalimentacion_ia(data: FeedbackIA):
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})
    try:
        feedback_data_for_db = {
            "timestamp": data.timestamp,
            "tipo_contexto": data.tipo_contexto,
            "id_contexto": data.id_contexto.lower(), # Guardar en minúsculas para búsquedas consistentes
            "instruccion": data.instruccion
        }
        response = supabase.table("retroalimentacion_ia").insert(feedback_data_for_db).execute()
        return JSONResponse(content={"status": "Retroalimentación guardada", "data": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al guardar retroalimentación de IA: {type(e).__name__} - {e}"})


@app.get("/memoria/{alumno}")
async def memoria(alumno: str):
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})
    try:
        response = supabase.table("evaluaciones").select("*").ilike("alumno", f"%{alumno}%").order("timestamp", desc=True).execute()
        return JSONResponse(content={"evaluaciones": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al recuperar memoria de Supabase: {type(e).__name__} - {e}"})

@app.get("/memoria/all")
async def memoria_all():
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})
    try:
        response = supabase.table("evaluaciones").select("*").order("timestamp", desc=True).execute()
        return JSONResponse(content={"evaluaciones": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al recuperar todas las evaluaciones de Supabase: {type(e).__name__} - {e}"})

class EvaluacionCompleta(BaseModel):
    id: int
    timestamp: int
    alumno: str
    curso: str
    nombrePrueba: str
    nota_final_aplicada: float
    feedback_general: str
    texto_evaluado: str = None
    rubrica_usada: str = None
    flexibilidadIA: int = None
    notaMinima: float = None
    
    # Si Mistral devuelve un JSON más complejo (analisis_por_criterio, sugerencias_mejora, puntos_fuertes)
    # y queremos guardarlo completo, lo incluimos así:
    analisis_por_criterio: dict = None
    puntaje_calculado_ia: float = None
    escala_puntaje: float = None
    nota_sugerida_ia: float = None
    sugerencias_mejora: list = None
    puntos_fuertes: list = None


@app.post("/guardar")
async def guardar(data: EvaluacionCompleta):
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})

    try:
        evaluation_data_for_db = {
            "id": data.id,
            "timestamp": data.timestamp,
            "alumno": data.alumno,
            "curso": data.curso,
            "nombre_prueba": data.nombrePrueba,
            "nota_final_aplicada": data.nota_final_aplicada,
            "texto_evaluado": data.texto_evaluado,
            "rubrica_usada": data.rubrica_usada,
            "evaluacion_json": data.dict() # Guarda el dict completo del modelo Pydantic
        }
        
        response = supabase.table("evaluaciones").insert(evaluation_data_for_db).execute()
        return JSONResponse(content={"status": "Guardado exitosamente en Supabase", "data": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al guardar en Supabase: {type(e).__name__} - {e}"})

@app.delete("/eliminar_evaluacion/{eval_id}")
async def eliminar_evaluacion(eval_id: int):
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})

    try:
        # Asegúrate de que el ID en Supabase sea de tipo INTEGER/BIGINT si eval_id es int
        response = supabase.table("evaluaciones").delete().eq("id", eval_id).execute()
        if response.data:
            return JSONResponse(content={"status": "Evaluación eliminada exitosamente", "id": eval_id})
        else:
            raise HTTPException(status_code=404, detail={"error": "Evaluación no encontrada"})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al eliminar de Supabase: {type(e).__name__} - {e}"})


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    azure_key = os.getenv("AZURE_VISION_KEY")
    azure_endpoint = os.getenv("AZURE_VISION_ENDPOINT")
    
    if not azure_key or not azure_endpoint:
        raise HTTPException(status_code=500, detail={"error": "Faltan claves de Azure"})

    image_bytes = await file.read()
    
    read_api_url = f"{azure_endpoint}/vision/v3.2/read/analyze"
    
    headers = {
        "Ocp-Apim-Subscription-Key": azure_key,
        "Content-Type": "application/octet-stream"
    }

    async with httpx.AsyncClient() as client:
        try:
            read_response = await client.post(read_api_url, headers=headers, content=image_bytes, timeout=60.0)
            read_response.raise_for_status()

            operation_location = read_response.headers.get("Operation-Location")
            if not operation_location:
                raise HTTPException(status_code=500, detail={"error": "No se recibió Operation-Location de Azure Read API."})

            result_data = {}
            status = "notStarted"
            max_retries = 15
            retries = 0
            while status in ["notStarted", "running"] and retries < max_retries:
                await asyncio.sleep(1) # Espera 1 segundo
                retries += 1
                # Crear un nuevo cliente httpx para cada sondeo si el anterior puede estar cerrado
                async with httpx.AsyncClient() as poll_client:
                    result_response = await poll_client.get(operation_location, headers={"Ocp-Apim-Subscription-Key": azure_key}, timeout=60.0)
                    result_response.raise_for_status()
                    result_data = result_response.json()
                    status = result_data.get("status")

            if status == "succeeded":
                extracted_text_content = ""
                if result_data.get("analyzeResult") and result_data["analyzeResult"].get("readResults"):
                    for page in result_data["analyzeResult"]["readResults"]:
                        if page.get("lines"):
                            for line in page["lines"]:
                                extracted_text_content += line.get("text", "") + "\n"
                    return JSONResponse(content={"status": "succeeded", "readResults": [{"content": extracted_text_content}]})
                else:
                    return JSONResponse(content={"status": "succeeded", "readResults": [{"content": "[No se detectó texto en el documento.]"}]})
            else:
                raise HTTPException(status_code=500, detail={"error": f"Azure Read API falló o no completó: {status}. Detalles: {result_data}"})

        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail={"error": f"Error de red o timeout al conectar con Azure OCR: {exc}"})
        except httpx.HTTPStatusError as exc:
            error_detail = exc.response.text
            try:
                error_json = exc.response.json()
                error_detail = error_json.get("message", error_detail)
            except ValueError:
                pass
            raise HTTPException(status_code=exc.response.status_code, detail={"error": f"Error de la API de Azure OCR ({exc.response.status_code}): {error_detail}"})
        except Exception as exc:
            raise HTTPException(status_code=500, detail={"error": f"Error inesperado al procesar OCR: {type(exc).__name__} - {exc}"})
````