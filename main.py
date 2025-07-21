from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx, os, json, aiofiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse("index.html")

# Ruta para evaluar desde archivos o texto directo
@app.post("/evaluar")
async def evaluar(
    alumno: str = Form(...),
    curso: str = Form(...),
    profesor: str = Form(...),
    departamento: str = Form(...),
    rubrica_text: str = Form(None),
    evaluacion_text: str = Form(None),
    rubrica_file: UploadFile = File(None),
    evaluacion: UploadFile = File(None)
):
    # OCR API Setup
    azure_endpoint = os.getenv("AZURE_OCR_ENDPOINT")
    azure_key = os.getenv("AZURE_OCR_KEY")
    headers = {
        "Ocp-Apim-Subscription-Key": azure_key,
        "Content-Type": "application/octet-stream"
    }

    async def extract_text_from_file(file: UploadFile):
        content = await file.read()
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{azure_endpoint}/vision/v3.2/read/analyze",
                headers=headers,
                content=content
            )
            operation_url = r.headers.get("Operation-Location")
            if not operation_url:
                return ""

            # Esperar procesamiento
            import asyncio
            for _ in range(10):
                await asyncio.sleep(1.5)
                status = await client.get(operation_url, headers={"Ocp-Apim-Subscription-Key": azure_key})
                result = status.json()
                if result.get("status") == "succeeded":
                    lines = result["analyzeResult"]["readResults"][0]["lines"]
                    return "\n".join([line["text"] for line in lines])
        return ""

    # Extraer rúbrica
    rubrica = rubrica_text or ""
    if rubrica_file:
        rubrica = await extract_text_from_file(rubrica_file)

    # Extraer evaluación
    evaluacion_str = evaluacion_text or ""
    if evaluacion:
        evaluacion_str = await extract_text_from_file(evaluacion)

    prompt = f"""
EVALUACIÓN IA
Alumno: {alumno}
Curso: {curso}
Profesor: {profesor}
Departamento: {departamento}

Texto del estudiante:
{evaluacion_str}

Con base en la siguiente rúbrica:
{rubrica}

Devuelve evaluación en JSON: puntaje (nota 1.0 a 7.0), feedback profesional por secciones, fortalezas y debilidades.
"""

    mistral_headers = {"Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"}
    mistral_body = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": "json"
    }

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post("https://api.mistral.ai/v1/chat/completions", headers=mistral_headers, json=mistral_body)
            r.raise_for_status()
            result = r.json()
            return JSONResponse(content=result)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/guardar")
async def guardar_resultado(request: Request):
    data = await request.json()
    # Lógica futura: guardar en Supabase
    return {"message": "Resultado guardado correctamente"}
