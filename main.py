from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx, os, json

app = FastAPI()

# Montar la carpeta 'static' si deseas servir otros recursos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ruta raíz para mostrar index.html
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse("index.html")

# Modelo para evaluar
class Evaluacion(BaseModel):
    alumno: str
    curso: str
    profesor: str
    departamento: str
    evaluacion: str
    rubrica: str

# Ruta para evaluación
@app.post("/evaluar")
async def evaluar(data: Evaluacion):
    prompt = f"""
EVALUACIÓN IA
Alumno: {data.alumno}
Curso: {data.curso}
Profesor: {data.profesor}
Departamento: {data.departamento}
Texto del estudiante:
{data.evaluacion}

Con base en la siguiente rúbrica:
{data.rubrica}

Devuelve evaluación en JSON: puntaje (nota 1.0 a 7.0), feedback profesional por secciones, fortalezas y debilidades.
"""

    headers = {"Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"}
    body = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": "json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=body)
            response.raise_for_status()
            result = response.json()
            return JSONResponse(content=result)
        except httpx.HTTPError as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

# Ruta para guardar resultado en Supabase (opcional si ya está en tu sistema)
@app.post("/guardar")
async def guardar_resultado(request: Request):
    data = await request.json()
    # Aquí va tu lógica de Supabase, si ya la integraste
    return {"message": "Resultado guardado correctamente"}
