from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx, os
from supabase import create_client, Client # Importar Supabase

# --- Configuración de Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = None # Inicializar como None, se asignará en startup

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
            # Opcional: Probar conexión a Supabase al inicio
            # response = supabase.table("evaluaciones").select("id").limit(1).execute()
            # print(f"Supabase test query successful: {response.data}")
        except Exception as e:
            print(f"ERROR: Could not initialize Supabase client: {e}")
            supabase = None # Asegúrate de que quede en None si falla
    else:
        print("WARNING: SUPABASE_URL or SUPABASE_KEY not set. Supabase features will be disabled.")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# Modelo de datos para la solicitud de evaluación desde el frontend
# Ahora incluye todos los campos que el frontend envía, incluyendo el prompt completo
class EvaluacionRequest(BaseModel):
    alumno: str
    evaluacion: str # El texto del estudiante
    rubrica: str    # La rúbrica
    curso: str
    nombrePrueba: str
    flexibilidadIA: int
    notaMinima: float
    prompt: str # El prompt completo generado en el frontend para Mistral

@app.post("/evaluar")
async def evaluar(data: EvaluacionRequest):
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_key:
        raise HTTPException(status_code=500, detail={"error": "Clave MISTRAL_API_KEY no definida"})

    headers = {"Authorization": f"Bearer {mistral_key}"}
    body = {
        "model": "mistral-large-latest", # Asegúrate de que este modelo sea el que quieres usar y esté disponible
        "messages": [{"role": "user", "content": data.prompt}], # Usamos el prompt completo del frontend
        "response_format": {"type": "json_object"}
    }
    async with httpx.AsyncClient() as client:
        try:
            # Aumentar el timeout por si la IA tarda en responder
            res = await client.post("https://api.mistral.ai/v1/chat/completions", json=body, headers=headers, timeout=120.0)
            res.raise_for_status() # Lanza una excepción para códigos de estado 4xx/5xx
            return res.json()
        except httpx.RequestError as exc:
            # Error de red, DNS, conexión, etc.
            raise HTTPException(status_code=500, detail={"error": f"Error de red o timeout al conectar con Mistral: {exc}"})
        except httpx.HTTPStatusError as exc:
            # Errores HTTP como 401 (no autorizado), 400 (bad request), 429 (rate limit), 500 (server error)
            error_detail = exc.response.text
            try:
                # Intenta parsear el error JSON de la API de Mistral si está disponible
                error_json = exc.response.json()
                error_detail = error_json.get("message", error_detail)
            except ValueError:
                pass # No es JSON
            raise HTTPException(status_code=exc.response.status_code, detail={"error": f"Error de la API de Mistral ({exc.response.status_code}): {error_detail}"})
        except Exception as exc:
            # Otros errores inesperados
            raise HTTPException(status_code=500, detail={"error": f"Error inesperado al evaluar con Mistral: {type(exc).__name__} - {exc}"})

@app.get("/memoria/{alumno}")
async def memoria(alumno: str):
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})
    
    try:
        # Busca evaluaciones por nombre de alumno (case-insensitive)
        # Puedes añadir más filtros si es necesario, por ejemplo por curso:
        # response = supabase.table("evaluaciones").select("*").ilike("alumno", f"%{alumno}%").ilike("curso", f"%{curso_opcional}%").order("timestamp", desc=True).execute()
        response = supabase.table("evaluaciones").select("*").ilike("alumno", f"%{alumno}%").order("timestamp", desc=True).execute()
        return JSONResponse(content={"evaluaciones": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al recuperar memoria de Supabase: {type(e).__name__} - {e}"})

@app.post("/guardar")
async def guardar(data: dict): # Cambiamos a dict para flexibilidad, ya que el frontend envía el JSON completo de la IA
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})

    try:
        # Extraer los campos relevantes del JSON completo de la IA para insertarlos en Supabase
        # Asegúrate de que estas claves existan en el JSON que envía tu frontend
        evaluation_data_for_db = {
            "id": data.get("id"), # Usamos el ID generado en el frontend (timestamp)
            "timestamp": data.get("timestamp"),
            "alumno": data.get("alumno"),
            "curso": data.get("curso"),
            "nombre_prueba": data.get("nombrePrueba"),
            "nota_final_aplicada": data.get("nota_final_aplicada"),
            "evaluacion_json": data # Guardamos el JSON completo en el campo JSONB
            # Si quieres guardar el texto de la evaluación y la rúbrica original (no están en el JSON de Mistral,
            # tendrías que enviarlos explícitamente desde el frontend junto con el resultado de la IA)
            # "texto_estudiante": data.get("texto_estudiante_original"), 
            # "rubrica_usada": data.get("rubrica_original")
        }
        
        # Insertar los datos en la tabla 'evaluaciones'
        response = supabase.table("evaluaciones").insert(evaluation_data_for_db).execute()
        return JSONResponse(content={"status": "Guardado exitosamente en Supabase", "data": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al guardar en Supabase: {type(e).__name__} - {e}"})

@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    azure_key = os.getenv("AZURE_VISION_KEY")
    azure_endpoint = os.getenv("AZURE_VISION_ENDPOINT")
    
    if not azure_key or not azure_endpoint:
        raise HTTPException(status_code=500, detail={"error": "Faltan claves de Azure"})

    image_bytes = await file.read()
    # Para la versión 3.2, el endpoint es /vision/v3.2/ocr
    # Si tu Azure Vision usa la API v4.0, el endpoint podría ser /vision/v4.0/read/sync o /vision/v3.2/read/analyze
    # Asegúrate de que tu endpoint y la URL aquí coincidan con la versión de la API que usas.
    # El frontend espera que el backend devuelva el texto extraído directamente, no la operación asíncrona de Azure.
    # El código actual para v3.2/ocr debería devolver el texto directamente si es una imagen simple.
    # Para PDFs o documentos multipágina, Azure v3.2/read/analyze es asíncrono, y el frontend ya espera eso.
    url = f"{azure_endpoint}/vision/v3.2/ocr?language=es" # Manteniendo v3.2/ocr como en tu original para imágenes
    
    headers = {
        "Ocp-Apim-Subscription-Key": azure_key,
        "Content-Type": "application/octet-stream"
    }

    async with httpx.AsyncClient() as client:
        try:
            # Aumentar el timeout por si el procesamiento de Azure tarda
            res = await client.post(url, headers=headers, content=image_bytes, timeout=60.0)
            res.raise_for_status()
            return res.json()
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