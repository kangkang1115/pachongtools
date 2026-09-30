# PM2 wrapper to start uvicorn
import uvicorn
uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
