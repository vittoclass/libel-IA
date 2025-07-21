from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Middleware para permitir CORS (útil para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos si es necesario
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"mensaje": "LibelIA API activa"}

@app.post("/evaluar")
async def evaluar_endpoint(
    alumno: str = Form(...),
    curso: str = Form(...),
    profesor: str = Form(...),
    departamento: str = Form(...),
    rubrica_file: UploadFile = File(None),
    rubrica_text: str = Form(None),
    evaluacion_file: UploadFile = File(None),
    evaluacion_text: str = Form(None)
):
    # Simulación de procesamiento real
    resultado = {
        "alumno": alumno,
        "curso": curso,
        "profesor": profesor,
        "departamento": departamento,
        "rubrica": rubrica_text or (rubrica_file.filename if rubrica_file else "No entregada"),
        "evaluacion": evaluacion_text or (evaluacion_file.filename if evaluacion_file else "No entregada"),
        "nota": 6.5,
        "retroalimentacion": "Buen trabajo, cumple con los criterios establecidos en la rúbrica."
    }
    return JSONResponse(content=resultado)