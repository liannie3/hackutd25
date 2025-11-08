# 🧙‍♀️ HackUTD25 Setup

## Prerequisites

Install these first:
- **Python 3.8+** - [Download here](https://www.python.org/downloads/)
- **Node.js 18+** - [Download here](https://nodejs.org/)

## Backend Setup (5 minutes)

### 1. Navigate to backend folder
```bash
cd backend
```

### 2. Create virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the server
```bash
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5000
```

✅ **Backend is ready!** Keep this terminal open.

---

## Frontend Setup (5 minutes)

### 1. Open a NEW terminal and navigate to frontend
```bash
cd frontend
```

### 2. Install dependencies
```bash
npm install
```

This will take 1-2 minutes the first time.

### 3. Start the dev server
```bash
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in 500 ms

  ➜  Local:   http://localhost:5173/
```
✅ **Frontend is ready!** Open http://localhost:5173 in your browser.

---

## Quick Test

1. Make sure backend terminal shows: `Running on http://127.0.0.1:5000`
2. Make sure frontend terminal shows: `Local: http://localhost:3000`
3. Open browser to `http://localhost:3000`
4. You should see the dashboard!

---

## Project Structure
```
potion-dashboard/
├── backend/
│   ├── app.py              # Flask server (run this)
│   └── requirements.txt    # Python packages
│
└── frontend/
    ├── src/                # React code
    ├── package.json        # Node packages
    └── vite.config.js      # Frontend config
```

---

## Working on the Project

### Starting Work (Every Time)

**Terminal 1 - Backend:**
```bash
cd backend
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Stopping

Press `Ctrl + C` in both terminals.

---

## Testing the API

Open http://localhost:5000 in your browser - you should see:
```Welcome to the HackUTD API proxy! 
```