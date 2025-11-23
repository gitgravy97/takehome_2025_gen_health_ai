# Medical Order Parser - Frontend

React-based frontend for uploading and parsing medical order PDFs.

## Setup

Install dependencies:
```bash
npm install
```

## Running the App

Start the development server:
```bash
npm run dev
```

The app will be available at http://localhost:3000

## Prerequisites

Make sure the backend API is running on port 8000:
```bash
cd ../api
uvicorn src.main:app --reload
```

Also ensure Ollama is running with the required model:
```bash
ollama serve
ollama pull llama3.1:8b
```

## Usage

1. Click "Choose File" and select a PDF containing a medical order
2. Click "Upload and Parse"
3. The extracted data will be displayed in four columns:
   - **Patient**: MRN, name, age
   - **Prescriber**: Name, NPI, contact information
   - **Order**: Item details, costs, reason prescribed
   - **Devices**: List of devices/items ordered

## Error Handling

If the upload fails, an error message will be displayed showing why the parsing was unsuccessful. Common errors include:
- Ollama not running
- Model not downloaded
- Invalid PDF format
- Missing required data in the PDF
