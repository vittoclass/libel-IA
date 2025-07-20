
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
import httpx, os, base64, io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Evaluacion(BaseModel):
    nombre_estudiante: str
    curso: str
    nombre_profesor: str
    departamento: str
    rubrica: str
    texto: str

AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_KEY")
MISTRAL_KEY = os.getenv("MISTRAL_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@app.post("/evaluar")
async def evaluar(data: Evaluacion):
    prompt = f"""EVALÚA ESTE TEXTO ESCANEADO
Nombre del estudiante: {data.nombre_estudiante}
Curso: {data.curso}
Profesor: {data.nombre_profesor}
Departamento: {data.departamento}

Rúbrica:
{data.rubrica}

Texto del estudiante:
{data.texto}

ENTREGA UN INFORME COMPLETO POR ESTUDIANTE EN FORMATO JSON CON:
- Nota de 1 a 7
- Feedback profesional
- Fortalezas
- Debilidades
- Informe resumen para el profesor
"""

    headers = {
        "Authorization": f"Bearer {MISTRAL_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": "json"
    }
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=body)
        result = r.json()
    return result

@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    content = await file.read()
    encoded = base64.b64encode(content).decode()

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/json"
    }
    params = {"language": "es"}
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{AZURE_ENDPOINT}/vision/v3.2/read/analyze",
            headers=headers, content=content
        )
        if r.status_code != 202:
            return {"error": "No se pudo analizar la imagen", "detalle": r.text}
        operation_location = r.headers["Operation-Location"]

        # Esperar resultado
        import asyncio
        await asyncio.sleep(3)
        r = await client.get(operation_location, headers=headers)
        result = r.json()
        texto = ""
        if "analyzeResult" in result:
            for line in result["analyzeResult"]["readResults"][0]["lines"]:
                texto += line["text"] + "\n"
        return {"texto": texto.strip()}
