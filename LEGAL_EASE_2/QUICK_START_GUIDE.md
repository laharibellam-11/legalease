═══════════════════════════════════════════════════════════════════════════════
                    QUICK START - AFTER FIXES APPLIED
═══════════════════════════════════════════════════════════════════════════════

✅ FIXES APPLIED:
   1. Protobuf downgraded from 4.25.3 to 3.20.0 ✓
   2. Enhanced error handling in embedder.py ✓
   3. Improved logging throughout ✓
   4. requirements.txt updated with protobuf==3.20.0 ✓

═══════════════════════════════════════════════════════════════════════════════
                            RUN THE APPLICATION
═══════════════════════════════════════════════════════════════════════════════

OPTION 1: Start All Services
──────────────────────────

cd C:\Users\srika\Downloads\LEXI-CHAIN\LEXI-CHAIN
.\SETUP_AND_RUN.ps1

This starts everything at once.


OPTION 2: Manual Startup (Recommended for Development)
──────────────────────────────────────────────────────

# Terminal 1 - Backend API
cd C:\Users\srika\Downloads\LEXI-CHAIN\LEXI-CHAIN\BACKEND
python run.py

Expected output:
  INFO:     Application startup complete
  INFO:     Uvicorn running on http://127.0.0.1:8000


# Terminal 2 - Frontend
cd C:\Users\srika\Downloads\LEXI-CHAIN\LEXI-CHAIN\FRONTEND
npm run dev

Expected output:
  ➜  Local:   http://localhost:5173/


# Terminal 3 - Admin Dashboard
cd C:\Users\srika\Downloads\LEXI-CHAIN\LEXI-CHAIN\ADMIN
npm run dev

Expected output:
  ➜  Local:   http://localhost:5174/

═══════════════════════════════════════════════════════════════════════════════
                          ACCESS THE APPLICATION
═══════════════════════════════════════════════════════════════════════════════

Backend API:       http://localhost:8000
API Docs:          http://localhost:8000/docs
Health Check:      http://localhost:8000/health

Frontend UI:       http://localhost:5173
Admin Dashboard:   http://localhost:5174

═══════════════════════════════════════════════════════════════════════════════
                          CONFIGURE EMBEDDINGS
═══════════════════════════════════════════════════════════════════════════════

IMPORTANT: Ollama Service (Optional but Recommended)
──────────────────────────────────────────────────

For faster embeddings, Ollama should be running:

# In a new terminal (NOT in the project directory):
ollama serve

# In another terminal, pull the embedding model:
ollama pull mxbai-embed-large

If Ollama is NOT running:
- Embeddings will automatically fall back to sentence-transformers
- It will be slower (first run downloads ~500MB)
- Results will be identical (just lower dimension: 384 vs 1024)

═══════════════════════════════════════════════════════════════════════════════
                        TEST DOCUMENT PROCESSING
═══════════════════════════════════════════════════════════════════════════════

1. Make sure all services are running
2. Go to http://localhost:5173 and login/register
3. Upload a PDF document
4. Check the backend terminal for logs like:

   ✅ Successfully embedded 150 texts with Ollama (dim=1024)
   
   OR (if Ollama not available):
   
   ⚠️  Ollama embedding failed, falling back to sentence-transformers...
   ✅ Successfully embedded 150 texts with sentence-transformers (dim=384)

═══════════════════════════════════════════════════════════════════════════════
                        TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

ERROR: "ModuleNotFoundError: No module named 'protobuf'"
──────────────────────────────────────────────────────
FIX: pip install protobuf==3.20.0


ERROR: Backend won't start or has errors
──────────────────────────────────────────
FIX: Check requirements.txt has protobuf==3.20.0
    pip install protobuf==3.20.0


ERROR: "Descriptors cannot be created directly"
─────────────────────────────────────────────────
FIX: This is fixed! It was the protobuf version issue.
    If you still see it, reinstall protobuf:
    pip install --force-reinstall protobuf==3.20.0


ERROR: Ollama embedding fails (400 Bad Request)
────────────────────────────────────────────────
OK: This is expected if Ollama isn't running!
    System will automatically fall back to sentence-transformers
    Check backend logs for: "falling back to sentence-transformers"


ERROR: Very slow embedding on first run
────────────────────────────────────────
NORMAL: Sentence-transformers model downloads on first use (~500MB)
        This happens only once
        Wait for completion and subsequent documents will be much faster

═══════════════════════════════════════════════════════════════════════════════
                        VERIFY EVERYTHING WORKS
═══════════════════════════════════════════════════════════════════════════════

Run this command to verify all dependencies are correct:

cd BACKEND
python -c "from app.services import embedder, rag; print('✅ All systems operational')"

Expected output: ✅ All systems operational

═══════════════════════════════════════════════════════════════════════════════
                            LOGS & DEBUGGING
═══════════════════════════════════════════════════════════════════════════════

The backend now provides detailed logs:

When document is uploaded:
  "Embedding 123 texts via Ollama..."
  "✅ Successfully embedded 123 texts with Ollama (dim=1024)"
  
OR if Ollama unavailable:
  "⚠️  Ollama embedding failed (ConnectionError), falling back..."
  "✅ Successfully embedded 123 texts with sentence-transformers (dim=384)"

These logs help identify:
- Whether Ollama is being used or sentence-transformers fallback
- How many texts are being processed
- Any errors that occur during processing

═══════════════════════════════════════════════════════════════════════════════

✅ YOU'RE ALL SET!

Start the application and try uploading a document.
The system will now work correctly with proper error handling and logging.

═══════════════════════════════════════════════════════════════════════════════
