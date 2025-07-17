# Genius Evaluator X

Aplicación educativa avanzada que permite evaluar automáticamente pruebas manuscritas y digitales mediante IA.

---

## 🚀 Tecnologías Utilizadas

- ⚙️ **FastAPI** – Backend rápido y eficiente
- 🧠 **Mistral AI** – Evaluación pedagógica real, con nota, feedback y resumen
- 📷 **Azure Computer Vision OCR** – Extracción de texto desde imágenes de evaluaciones
- ☁️ **Supabase (opcional)** – Almacenamiento en la nube de resultados por estudiante
- 🌐 **HTML personalizado** – Interfaz clara y profesional lista para docentes

---

## ✨ Funcionalidades Principales

- Carga de imágenes de evaluaciones escaneadas o fotografiadas
- Extracción de nombre, curso y texto completo con OCR
- Evaluación de respuestas mediante rúbrica
- Feedback profesional con enfoque pedagógico
- Nota chilena (escala del 1.0 al 7.0)
- Opción de optimizar texto OCR antes de evaluar
- Visualización inmediata de resultados
- Preparado para guardar en Supabase y exportar informes

---

## ⚙️ Variables de Entorno

Asegúrate de configurar las siguientes variables:

```env
MISTRAL_API_KEY=tu_clave_mistral
AZURE_KEY=tu_clave_azure
AZURE_ENDPOINT=https://<tu-recurso>.cognitiveservices.azure.com
```

---

## 📁 Estructura del Proyecto

```
GeniusEvaluatorX/
│
├── main.py              # Backend FastAPI
├── static/
│   └── index.html       # Interfaz web
├── .env                 # Claves API (no subir a GitHub)
└── README.md            # Este archivo
```

---

## ✅ Instrucciones para usar

1. Clona el repositorio y agrega tus claves al `.env`
2. Ejecuta localmente con:
   ```bash
   uvicorn main:app --reload
   ```
3. Accede a `http://localhost:8000`
4. También puedes desplegar en [Railway](https://railway.app) o Replit

---

## 🧠 Créditos

Desarrollado por: **Ivan Badilla Alfaro**  
Proyecto: **LibélIA** – Innovación educativa con Inteligencia Artificial

---

## 📬 Contacto

📧 vittoclass@gmail.com  
📱 +56988131999
