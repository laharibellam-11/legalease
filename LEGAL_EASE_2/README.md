# LegalEase - AI-Powered Legal Document Analyzer

## Architecture

- **Backend**: FastAPI + MongoDB + ChromaDB + Google Gemini
- **Frontend**: React 18 + Vite + Tailwind CSS 3
- **Admin**: React 18 + Vite + Tailwind CSS 3 + Recharts

## Quick Start

### 1. Backend

```bash
cd BACKEND
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# Copy .env.example to .env and fill in values
cp .env.example .env

# Run
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd FRONTEND
npm install
npm run dev          # http://localhost:5173
```

### 3. Admin Panel

```bash
cd ADMIN
npm install
npm run dev          # http://localhost:5174
```

## Environment Variables (Backend)

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `JWT_SECRET` | Random secret for JWT signing |
| `CHROMA_PERSIST_DIR` | Path for ChromaDB persistence |
| `UPLOAD_DIR` | Directory for uploaded PDFs |
| `CORS_ORIGINS` | Allowed origins (comma-separated) |

## Default Ports

| Service | Port |
|---------|------|
| Backend API | 8000 |
| Frontend | 5173 |
| Admin Panel | 5174 |

## Creating an Admin User

Register via the frontend, then update the role directly in MongoDB:

```javascript
db.users.updateOne({ email: "admin@example.com" }, { $set: { role: "admin" } })
```

## Deployment

- **Frontend / Admin**: Deploy to Vercel (`vercel.json` included for SPA rewrites)
- **Backend**: Deploy to Railway or Render using the included `Dockerfile`

## Key Features

- PDF upload with OCR fallback (PyMuPDF + Tesseract)
- RAG-powered Q&A with citation support
- Automatic clause extraction (10 clause types)
- Risk scoring engine (8 risk rules)
- Multi-document comparison
- Real-time processing status
- Admin analytics dashboard
