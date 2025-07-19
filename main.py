from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os, httpx, base64
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


class Evaluacion(BaseModel):
    alumno: str
    evaluacion: str
    rubrica: str


@app.post("/evaluar")
async def evaluar(data: Evaluacion):
    prompt = f"""
EVALUACIÓN IA

Alumno: {data.alumno}
Rúbrica: {data.rubrica}
Texto del estudiante: {data.evaluacion}

Responde con feedback profesional, nota en escala chilena (1.0 a 7.0) y análisis detallado.
Entrega el resultado en formato JSON con las claves: nota, retroalimentacion, fortalezas, debilidades.
"""
    headers = {"Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"}
    body = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.mistral.ai/v1/chat/completions", json=body, headers=headers)

    return JSONResponse(content=response.json())


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    content = await file.read()
    encoded_image = base64.b64encode(content).decode("utf-8")

    headers = {
        "Ocp-Apim-Subscription-Key": os.getenv("AZURE_VISION_KEY"),
        "Content-Type": "application/octet-stream"
    }

    endpoint = os.getenv("AZURE_VISION_ENDPOINT") + "/vision/v3.2/read/analyze"

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, content=content, headers=headers)
        operation_location = response.headers.get("Operation-Location")

        if not operation_location:
            return JSONResponse(status_code=500, content={"error": "No se pudo obtener la URL de operación"})

        # Esperar a que el análisis esté listo
        for _ in range(10):
            result = await client.get(operation_location, headers=headers)
            data = result.json()
            if data.get("status") == "succeeded":
                break
            await asyncio.sleep(1)

    # Extraer texto
    text = ""
    for line in data["analyzeResult"]["readResults"]:
        for l in line["lines"]:
            text += l["text"] + "\n"

    return JSONResponse(content={"texto_extraido": text})
