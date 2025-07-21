from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os

app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos desde la carpeta 'static'
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mostrar HTML principal
@app.get("/", response_class=HTMLResponse)
async def home():
    return FileResponse("static/index.html")

# Ruta para evaluación
@app.post("/evaluar")
async def evaluar(
    alumno: str = Form(...),
    curso: str = Form(...),
    profesor: str = Form(...),
    departamento: str = Form(...),
    rubrica_file: Optional[UploadFile] = File(None),
    rubrica_text: Optional[str] = Form(None),
    evaluacion_file: Optional[UploadFile] = File(None),
    evaluacion_text: Optional[str] = Form(None)
):
    # Aquí simulas la lógica de procesamiento. Luego puedes agregar OCR, GPT, etc.
    resultado = {
        "alumno": alumno,
        "curso": curso,
        "profesor": profesor,
        "departamento": departamento,
        "rubrica": rubrica_text or (rubrica_file.filename if rubrica_file else "No ingresada"),
        "evaluacion": evaluacion_text or (evaluacion_file.filename if evaluacion_file else "No ingresada"),
        "resultado": "Evaluación procesada correctamente (respuesta simulada)"
    }
    return JSONResponse(content=resultado)
