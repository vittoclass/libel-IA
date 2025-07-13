from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx, os

# Debug: Verifica si las variables están presentes
print("DEBUG - MISTRAL_API_KEY:", os.getenv("MISTRAL_API_KEY"))
print("DEBUG - AZURE_VISION_KEY:", os.getenv("AZURE_VISION_KEY"))
print("DEBUG - AZURE_VISION_ENDPOINT:", os.getenv("AZURE_VISION_ENDPOINT"))

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

class Evaluacion(BaseModel):
    alumno: str
    evaluacion: str
    rubrica: str

@app.post("/evaluar")
async def evaluar(data: Evaluacion):
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_key:
        return JSONResponse(content={"error": "Clave MISTRAL_API_KEY no definida"}, status_code=500)

    prompt = f"""EVALUACIÓN IA\n\nAlumno: {data.alumno}\nRúbrica: {data.rubrica}\nTexto del estudiante: {data.evaluacion}\n\nResponde con feedback, puntaje y análisis en JSON"""
    headers = {"Authorization": f"Bearer {mistral_key}"}
    body = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    async with httpx.AsyncClient() as client:
        res = await client.post("https://api.mistral.ai/v1/chat/completions", json=body, headers=headers)
        return res.json()

@app.get("/memoria/{alumno}")
async def memoria(alumno: str):
    return {"learningContext": f"Memoria del alumno {alumno} aún no implementada."}

@app.post("/guardar")
async def guardar(data: dict):
    return {"status": "Guardado (ficticio por ahora)"}

@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    azure_key = os.getenv("AZURE_VISION_KEY")
    azure_endpoint = os.getenv("AZURE_VISION_ENDPOINT")
    
    if not azure_key or not azure_endpoint:
        return JSONResponse(content={"error": "Faltan claves de Azure"}, status_code=500)

    image_bytes = await file.read()
    url = f"{azure_endpoint}/vision/v3.2/ocr?language=es"
    headers = {
        "Ocp-Apim-Subscription-Key": azure_key,
        "Content-Type": "application/octet-stream"
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, content=image_bytes)
        return res.json()
