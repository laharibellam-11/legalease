# ⚖️ LEGALEASE: AI Legal Document Analyser

## 🚀 Overview
LEGALEASE is an AI-powered legal document analysis platform designed to simplify complex legal agreements and help users identify potential risks before signing.

It acts as a **smart legal assistant** by converting lengthy legal documents into clear, actionable insights.

---

## 🎯 Problem Statement
Legal documents are often complex and difficult to understand.  
Most people sign them without fully reading or understanding the risks involved.

LEGALEASE solves this problem by providing:
- Easy-to-understand summaries  
- Risk detection  
- Clause extraction  
- Interactive AI-based assistance  

---

## 💡 Key Features

- 📄 **Document Upload & Processing**  
  Upload PDF or scanned legal documents  

- ⚠️ **Risk Analysis (Dual Engine)**  
  - Rule-based detection  
  - AI-based semantic analysis  

- 📑 **Clause Extraction**  
  Identifies key clauses like confidentiality, liability, termination  

- 🤖 **AI Chat Assistant (RAG-based)**  
  Ask questions like *“Is this contract safe?”*  

- 📊 **Risk Dashboard**  
  Displays Low / Medium / High risk levels  

- 📝 **Summary Generation**  
  Converts complex legal text into simple summaries  

---

## 🏗️ System Architecture

The system follows a layered architecture:

- **Frontend:** React, Vite, Tailwind CSS  
- **Backend:** FastAPI (Python)  
- **AI Models:** Legal-BERT, LLM  
- **Database:** MongoDB  
- **Vector Database:** ChromaDB  

---

## 🔄 Workflow

1. Upload legal document  
2. Extract text (PDF / OCR)  
3. Preprocess text  
4. Extract clauses  
5. Perform risk analysis  
6. Generate summary  
7. Store embeddings  
8. Chatbot interaction  
9. Display results  

---

## 🛠️ Technologies Used

- **Frontend:** React, HTML, CSS, JavaScript  
- **Backend:** Python, FastAPI  
- **Database:** MongoDB, ChromaDB  
- **AI Models:** Legal-BERT, LLM  
- **Processing:** PyMuPDF, Tesseract OCR  
- **Other Tools:** Docker, Uvicorn, Nginx  

---

## 📊 Results

- Clause Extraction: ~88% Precision, 85% Recall  
- QA Accuracy: ~90–92%  
- Processing Time: 3–6 seconds  

---

## 🔮 Future Scope

- Multilingual support  
- Contract comparison feature  
- Mobile application  
- Voice-based interaction  
- Blockchain-based document security  



## 📌 Conclusion

LEGALEASE simplifies legal documents using AI and helps users make safe and informed decisions without requiring legal expertise.

---

## ⭐ Tagline
**"No one should sign a document without understanding it."**
