# aabha
An intelligent voice companion that understands context, remembers what matters, and helps you navigate everyday life.


For agent start:
    lk agent dev src/aabha/agent/worker.py                        

For fastapi server start:
    uvicorn src.aabha.api.main:app --host 0.0.0.0 --port 8080     