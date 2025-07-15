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
    prompt: str # El prompt completo generado en el frontend

@app.post("/evaluar")
async def evaluar(data: EvaluacionRequest):
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_key:
        raise HTTPException(status_code=500, detail={"error": "Clave MISTRAL_API_KEY no definida"})

    headers = {"Authorization": f"Bearer {mistral_key}"}
    body = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": data.prompt}],
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

@app.get("/memoria/{alumno}") # Endpoint para buscar por alumno (se mantiene)
async def memoria(alumno: str):
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})
    
    try:
        response = supabase.table("evaluaciones").select("*").ilike("alumno", f"%{alumno}%").order("timestamp", desc=True).execute()
        return JSONResponse(content={"evaluaciones": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al recuperar memoria de Supabase: {type(e).__name__} - {e}"})

@app.get("/memoria/all") # NUEVO: Endpoint para obtener todas las evaluaciones
async def memoria_all():
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})
    
    try:
        response = supabase.table("evaluaciones").select("*").order("timestamp", desc=True).execute()
        return JSONResponse(content={"evaluaciones": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al recuperar todas las evaluaciones de Supabase: {type(e).__name__} - {e}"})

# Modelo para la estructura completa de una evaluación tal como se guarda del frontend
class EvaluacionCompleta(BaseModel):
    id: int
    timestamp: int
    alumno: str
    curso: str
    nombrePrueba: str
    nota_final_aplicada: float
    feedback_general: str

    # Campos que el frontend añade para guardar el contexto original
    texto_evaluado: str = None
    rubrica_usada: str = None
    flexibilidadIA: int = None
    notaMinima: float = None


@app.post("/guardar") # Actualizado: Guarda la evaluación completa, incluyendo texto/rúbrica original
async def guardar(data: EvaluacionCompleta):
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})

    try:
        # Los datos del frontend ya están en el formato deseado
        # Simplemente mapeamos los campos a las columnas de Supabase
        evaluation_data_for_db = {
            "id": data.id, # El ID generado por el frontend (timestamp)
            "timestamp": data.timestamp,
            "alumno": data.alumno,
            "curso": data.curso,
            "nombre_prueba": data.nombrePrueba,
            "nota_final_aplicada": data.nota_final_aplicada,
            "texto_evaluado": data.texto_evaluado, # Guardar texto original
            "rubrica_usada": data.rubrica_usada,   # Guardar rúbrica usada
            "evaluacion_json": data.dict() # Guardar el dict completo de la evaluación tal como viene del frontend
        }
        
        response = supabase.table("evaluaciones").insert(evaluation_data_for_db).execute()
        return JSONResponse(content={"status": "Guardado exitosamente en Supabase", "data": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Error al guardar en Supabase: {type(e).__name__} - {e}"})

@app.delete("/eliminar_evaluacion/{eval_id}") # NUEVO: Endpoint para eliminar una evaluación
async def eliminar_evaluacion(eval_id: int): # eval_id corresponde al 'id' de la evaluación (timestamp)
    if not supabase:
        raise HTTPException(status_code=500, detail={"error": "Supabase no está inicializado. Verifica las variables de entorno."})

    try:
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
    
    # Para la versión 3.2 de Read API (asíncrona), el endpoint es /vision/v3.2/read/analyze
    # Esta es la más recomendada para PDFs y documentos multipágina
    read_api_url = f"{azure_endpoint}/vision/v3.2/read/analyze"
    
    headers = {
        "Ocp-Apim-Subscription-Key": azure_key,
        "Content-Type": "application/octet-stream"
    }

    async with httpx.AsyncClient() as client:
        try:
            # Paso 1: Enviar la imagen/documento para análisis
            read_response = await client.post(read_api_url, headers=headers, content=image_bytes, timeout=60.0)
            read_response.raise_for_status()

            operation_location = read_response.headers.get("Operation-Location")
            if not operation_location:
                raise HTTPException(status_code=500, detail={"error": "No se recibió Operation-Location de Azure Read API."})

            # Paso 2: Sondear los resultados del análisis
            result_data = {}
            status = "notStarted"
            max_retries = 15
            retries = 0
            while status in ["notStarted", "running"] and retries < max_retries:
                # No cerramos el cliente `client` aquí para reusar la conexión,
                # pero sí esperamos para no inundar Azure con peticiones
                await asyncio.sleep(1)
                retries += 1
                result_response = await client.get(operation_location, headers={"Ocp-Apim-Subscription-Key": azure_key}, timeout=60.0)
                result_response.raise_for_status()
                result_data = result_response.json()
                status = result_data.get("status")

            if status == "succeeded":
                # Extraer texto de readResults (estructura común para v3.2 y v4.0 Read API)
                extracted_text_content = ""
                if result_data.get("analyzeResult") and result_data["analyzeResult"].get("readResults"):
                    # Recorrer páginas y líneas
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
            # Corrección de la línea 231: Eliminada la comilla doble extra al final de la cadena de detalle
            raise HTTPException(status_code=500, detail={"error": f"Error inesperado al procesar OCR: {type(exc).__name__} - {exc}"})