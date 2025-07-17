from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx, os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Página principal
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# Modelo para evaluación
class Evaluacion(BaseModel):
    alumno: str
    curso: str
    evaluacion: str
    rubrica: str
    optimizar: bool = False

@app.post("/evaluar")
async def evaluar(data: Evaluacion):
    prompt = f"""
ERES UN DOCENTE IA ENTRENADO EN CURRÍCULUM LATINOAMERICANO Y CHILENO.

Tu objetivo es evaluar una respuesta de estudiante considerando rúbrica, claridad, reflexión y profundidad.

Nombre del estudiante: {data.alumno}
Curso: {data.curso}

Texto del estudiante:
"""
{data.evaluacion}
"""

Rúbrica:
{data.rubrica}

Actúa como docente real. Da feedback claro, afectivo, basado en evidencia. Entrega:
- nota (del 1.0 al 7.0)
- retroalimentación profesional con aciertos y mejoras
- resumen breve para informe del profesor

NO agregues elementos ficticios ni invenciones.

Responde en formato JSON:
{{
  "nota": número,
  "feedback": "texto",
  "resumen": "texto"
}}
"""

    headers = {
        "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"
    }

    body = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=body)

    if response.status_code != 200:
        return JSONResponse(content={"error": "Error en Mistral API", "detalle": response.text}, status_code=500)

    return JSONResponse(content=response.json())

@app.post("/extraer-texto")
async def extraer_texto_azure(file: UploadFile = File(...)):
    AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
    AZURE_KEY = os.getenv("AZURE_KEY")

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/octet-stream"
    }

    params = {
        "language": "es",
        "readingOrder": "natural"
    }

    img_bytes = await file.read()
    url = f"{AZURE_ENDPOINT}/vision/v3.2/read/analyze"

    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, params=params, content=img_bytes)
        if res.status_code != 202:
            return JSONResponse(content={"error": "Error OCR Azure", "detalle": res.text}, status_code=400)

        operation_url = res.headers["Operation-Location"]

        import asyncio
        for _ in range(10):
            await asyncio.sleep(1.5)
            result = await client.get(operation_url, headers=headers)
            result_data = result.json()
            if result_data.get("status") == "succeeded":
                break

    lineas = []
    for region in result_data["analyzeResult"]["readResults"]:
        for line in region["lines"]:
            lineas.append(line["text"])

    texto_extraido = "\n".join(lineas)

    # Buscar nombre y curso
    nombre = ""
    curso = ""
    for linea in lineas:
        l = linea.lower()
        if "nombre" in l:
            nombre = linea.split(":")[-1].strip()
        elif "curso" in l:
            curso = linea.split(":")[-1].strip()

    return {
        "nombre": nombre if nombre else "No detectado",
        "curso": curso if curso else "No detectado",
        "texto": texto_extraido
    }

@app.post("/guardar")
async def guardar_resultado(request: Request):
    data = await request.json()
    # Aquí podrías conectar con Supabase o base de datos externa
    return {"status": "ok", "mensaje": "Guardado correctamente (demo)"}
