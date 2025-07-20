from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx, os, json

app = FastAPI()

# Montar carpeta estática para servir recursos si los hay
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ruta raíz → Muestra el HTML principal
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse("index.html")

# Modelo para los datos de evaluación
class Evaluacion(BaseModel):
    alumno: str
    curso: str
    profesor: str
    departamento: str
    evaluacion: str
    rubrica: str

# Ruta de evaluación conectada a Mistral AI
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

    headers = {"Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}", "Content-Type": "application/json"}
    body = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=body)
            response.raise_for_status()
            result = response.json()

            if 'choices' in result and result['choices']:
                output = result['choices'][0]['message']['content']
                try:
                    parsed = json.loads(output)
                    return JSONResponse(content=parsed)
                except json.JSONDecodeError:
                    return JSONResponse(content={"error": "La IA no devolvió JSON válido", "respuesta": output}, status_code=500)
            else:
                return JSONResponse(content={"error": "Respuesta inesperada del modelo"}, status_code=500)

        except httpx.HTTPStatusError as e:
            return JSONResponse(status_code=e.response.status_code, content={"error": f"HTTP error: {e.response.text}"})
        except httpx.HTTPError as e:
            return JSONResponse(status_code=500, content={"error": f"Error de conexión: {str(e)}"})

# Ruta para guardar resultados (opcional, para Supabase o base futura)
@app.post("/guardar")
async def guardar_resultado(request: Request):
    data = await request.json()
    return {"message": "Resultado guardado correctamente"}

