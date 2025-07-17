from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os, httpx
from PIL import Image
import pytesseract

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("static/index.html")

async def extract_text_from_image(file: UploadFile) -> str:
    contents = await file.read()
    with open("temp_image.jpg", "wb") as f:
        f.write(contents)
    image = Image.open("temp_image.jpg")
    text = pytesseract.image_to_string(image)
    return text.strip()

@app.post("/evaluar")
async def evaluar(
    file: UploadFile = File(...),
    nombre: str = Form(...),
    curso: str = Form(...),
    asignatura: str = Form(""),
    rubrica: str = Form("")
):
    texto_extraido = await extract_text_from_image(file)

    prompt = f"""
Eres un evaluador experto con alta formación pedagógica en Latinoamérica. Evalúa rigurosamente este contenido como si fueras un profesor especializado.

Nombre del estudiante: {nombre}
Curso: {curso}
Asignatura: {asignatura or "Detectar automáticamente"}
Rúbrica (si aplica): {rubrica}

Texto escaneado desde imagen:
{texto_extraido}

Entrega los resultados como un JSON profesional con esta estructura:
{{
  "asignatura": "Asignatura detectada o especificada",
  "tipo": "Tipo de evaluación (por ejemplo: desarrollo, alternativa, prueba de arte, etc.)",
  "puntaje": "Puntaje estimado en base a calidad, exactitud, profundidad",
  "nota": "Nota chilena del 1.0 al 7.0",
  "feedback": "Retroalimentación profesional, clara y formativa"
}}
"""

    headers = {
        "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "mistral-large-latest",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=body
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

            # Usamos eval solo si estamos seguros que es un JSON puro
            result = eval(content.strip()) if content.strip().startswith("{") else {
                "asignatura": asignatura or "Desconocida",
                "tipo": "No detectado",
                "puntaje": "-",
                "nota": "-",
                "feedback": content.strip()
            }

    except Exception as e:
        result = {
            "asignatura": asignatura or "Desconocida",
            "tipo": "Desconocido",
            "puntaje": "-",
            "nota": "-",
            "feedback": f"Error interno del servidor: {str(e)}"
        }

    return JSONResponse(content=result)
