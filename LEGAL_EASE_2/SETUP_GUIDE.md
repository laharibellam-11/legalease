# LEXI-CHAIN Setup & Troubleshooting Guide

## ✅ What Was Fixed

### 1. **Missing Dependencies**
- **Issue**: `ModuleNotFoundError: No module named 'uvicorn'`
- **Cause**: Python dependencies from `requirements.txt` were not installed
- **Solution**: Ran `pip install -r requirements.txt`

### 2. **Python Version Compatibility** (FIXED ✓)
- **Issue**: TypeError with type hints using `int | None` syntax
- **Cause**: Your environment runs Python 3.9.12, which doesn't support union type hints (`|`). This syntax is only available in Python 3.10+
- **Solution**: Updated 4 type hint declarations in:
  - `app/services/embedder.py` (2 fixes)
  - `app/services/rag.py` (1 fix)

Changed from: `int | None` → To: `Optional[int]`

---

## 📦 Dependencies Status

### Backend (Python)
| Package | Version | Status |
|---------|---------|--------|
| uvicorn | 0.39.0 | ✅ Installed |
| fastapi | 0.128.8 | ✅ Installed |
| motor | 3.7.1 | ✅ Installed |
| beanie | 2.0.1 | ✅ Installed |
| pydantic | 2.12.5 | ✅ Installed |
| chromadb | 1.5.5 | ✅ Installed |
| google-genai | 1.47.0 | ✅ Installed |

**Total**: 50+ Python packages installed

### Frontend (Node.js)
| Package | Status |
|---------|--------|
| react | ✅ Installed |
| vite | ✅ Installed |
| axios | ✅ Installed |
| react-router-dom | ✅ Installed |
| tailwindcss | ✅ Installed |

### Admin Panel (Node.js)
| Package | Status |
|---------|--------|
| react | ✅ Installed |
| vite | ✅ Installed |
| axios | ✅ Installed |
| recharts | ✅ Installed |

---

## 🚀 How to Run Everything

### Option 1: Automated PowerShell Script
```powershell
cd C:\Users\srika\Downloads\LEXI-CHAIN\LEXI-CHAIN
.\SETUP_AND_RUN.ps1
```
This will:
- Install all dependencies
- Start Backend (port 8000)
- Start Frontend (port 5173)
- Start Admin (port 5174)

### Option 2: Manual Startup (Recommended for Development)

#### Terminal 1 - Backend
```powershell
cd C:\Users\srika\Downloads\LEXI-CHAIN\LEXI-CHAIN\BACKEND
python run.py
```
Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

#### Terminal 2 - Frontend
```powershell
cd C:\Users\srika\Downloads\LEXI-CHAIN\LEXI-CHAIN\FRONTEND
npm run dev
```
Expected output:
```
  ➜  Local:   http://localhost:5173/
```

#### Terminal 3 - Admin
```powershell
cd C:\Users\srika\Downloads\LEXI-CHAIN\LEXI-CHAIN\ADMIN
npm run dev
```
Expected output:
```
  ➜  Local:   http://localhost:5174/
```

---

## 🌐 Accessing the Application

Once all services are running:

| Service | URL | Purpose |
|---------|-----|---------|
| **API** | http://localhost:8000 | Backend API |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Frontend** | http://localhost:5173 | Main user interface |
| **Admin** | http://localhost:5174 | Admin dashboard |

---

## ⚠️ Prerequisites Required to Run

1. **MongoDB** - Must be accessible at connection string in `.env`
2. **Google Gemini API Key** - Configured in `.env`
3. **Ollama (Optional)** - For local embeddings (if not available, will use fallback)

Check `.env` files in:
- `BACKEND/.env` - Backend configuration
- `FRONTEND/.env` - Frontend API URL
- `ADMIN/.env` - Admin API URL

---

## 🔧 If You Get Errors

### Error: `ModuleNotFoundError: No module named 'fastapi'`
```powershell
# Install backend dependencies
cd BACKEND
pip install -r requirements.txt
```

### Error: `npm ERR! code ERESOLVE`
```powershell
# Reinstall Node dependencies
cd FRONTEND  # or ADMIN
rm -r node_modules package-lock.json
npm install
```

### Error: `Connection refused to MongoDB`
- Ensure MongoDB is running
- Check connection string in `BACKEND/.env`
- Verify network connectivity to MongoDB Atlas (if cloud)

### Error: `TypeError: unsupported operand type(s) for |`
- This has been fixed in the current version
- If you see this again, ensure you have the latest files

---

## 📝 Common Commands

### Backend
```powershell
# Development mode (with auto-reload)
python run.py

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000

# Check for syntax errors
python -m py_compile main.py
```

### Frontend & Admin
```powershell
# Development mode
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

---

## 🐳 Docker Alternative

To run the backend in Docker:
```bash
cd BACKEND
docker build -t lexichain-backend .
docker run -p 8000:8000 --env-file .env lexichain-backend
```

---

## 📚 Project Structure Reference

```
LEXI-CHAIN/
├── BACKEND/               # FastAPI application
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Config, security, database
│   │   ├── models/       # MongoDB models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic
│   ├── requirements.txt   # Python dependencies
│   ├── run.py            # Entry point
│   └── .env              # Environment configuration
│
├── FRONTEND/             # React user interface
│   ├── src/
│   │   ├── pages/        # Route pages
│   │   ├── components/   # React components
│   │   ├── services/     # API client services
│   │   └── context/      # State management
│   ├── package.json      # Node dependencies
│   └── vite.config.js    # Vite build config
│
└── ADMIN/                # Admin dashboard
    ├── src/
    │   ├── pages/        # Admin pages
    │   ├── components/   # Dashboard components
    │   └── services/     # API client
    └── package.json      # Node dependencies
```

---

## ✨ Verification Checklist

- [x] Python dependencies installed (50+ packages)
- [x] Node dependencies installed (Frontend & Admin)
- [x] Python type hints compatible with Python 3.9
- [x] Backend imports successfully
- [x] All files compile without errors
- [x] `.env` files configured with API keys
- [x] Database initialization ready

---

## 🤝 Support

If you encounter issues:

1. Check error messages carefully
2. Verify all prerequisites are met (MongoDB, API keys)
3. Ensure you're in the correct directory
4. Check `.env` files are properly configured
5. Look for detailed logs in each terminal

