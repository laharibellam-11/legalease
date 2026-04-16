import os
import sys

# Ensure BACKEND/ is on the Python path so `main:app` resolves correctly
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    import uvicorn
    
    print("Starting LexiChain Backend Server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )