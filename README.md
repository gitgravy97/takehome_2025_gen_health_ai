# Medical Order PDF Parser

An intelligent medical order processing system that extracts structured data from PDF documents using local LLM technology, allows user review and editing, and persists the data to a PostgreSQL database with duplicate detection.

## Notes from McCoy
I'm hitting that time limit so going to wrap things up here and get documenting before the clock runs out

Next Steps I would go for
- I just realized I grabbed user Age rather than DOB, fairly easy fix
- Setting up users w/ JWT's so then we can meaningfully authenticate user actions and audit log them
- Setting up a docker file because that'd make repeated setup easier, plus make K8's easier to set up when the time comes
- Front-end validation would be another "low-time-investment, high-payoff" in terms of data governance//integrity
- Having not worked with specifically PHI I am certain that there's regulatory compliance things that'd need to be done
  in taking this to production viability
- Setting up a data contract to keep frontend sync'd up with backend's data structures typescript-wise
- More unit testing

## 🎯 Overview

This application automates the extraction of medical order information from PDF documents (both text-based and scanned images) and provides a user-friendly interface for reviewing, editing, and saving the data. The system uses AI-powered extraction with **zero API costs** by running entirely locally.

## ✨ Features

### Core Functionality
- **📄 PDF Processing**: Supports both text-based PDFs and scanned documents (via OCR)
- **🤖 AI-Powered Extraction**: Uses local Llama 3.1 model for intelligent data extraction
- **✏️ Editable Review**: Review and modify extracted data before database submission
- **⚠️ Duplicate Detection**: Automatically warns about potential duplicate orders
- **🔄 Idempotent Entity Creation**: Smart lookup/create for patients, prescribers, and devices

### Data Management
- **Patient Information**: MRN, name, age
- **Prescriber Information**: NPI, name, contact details, clinic information
- **Device/Equipment**: Name, SKU, quantity tracking
- **Order Details**: Item name, quantity, costs, prescribing reasons

## 🏗️ Architecture

```
gen_health_ai/
├── api/                    # FastAPI Backend
│   ├── src/
│   │   ├── main.py        # API endpoints
│   │   ├── models.py      # SQLAlchemy ORM models
│   │   ├── schemas.py     # Pydantic validation schemas
│   │   ├── services.py    # Business logic & PDF parsing
│   │   └── database.py    # Database configuration
│   ├── alembic/           # Database migrations
│   └── requirements.txt   # Python dependencies
│
└── ui/                    # React Frontend
    ├── src/
    │   ├── App.jsx        # Main React component
    │   └── App.css        # Styling
    ├── package.json       # Node dependencies
    └── vite.config.js     # Vite configuration
```

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Relational database
- **Alembic**: Database migration management
- **Ollama + Llama 3.1**: Local LLM for data extraction (FREE!)
- **PyMuPDF4LLM**: PDF text extraction
- **Tesseract + pdf2image**: OCR for scanned documents
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Vanilla CSS**: Modern styling with gradients and animations

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Ollama (for local LLM)
- Tesseract OCR
- Poppler (for PDF to image conversion)

## 🚀 Installation

### 1. Clone the Repository

```bash
cd /path/to/your/workspace
git clone <repository-url>
cd gen_health_ai
```

### 2. Backend Setup

```bash
cd api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (optional)
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_DB=postgres_gen_health_ai
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
```

### 3. Database Setup

```bash
# Create the database
createdb postgres_gen_health_ai

# Run migrations
alembic upgrade head
```

### 4. Install Ollama and LLM

```bash
# Install Ollama (see https://ollama.ai)
# Then pull the Llama 3.1 model
ollama pull llama3.1:8b

# Start Ollama service
ollama serve
```

### 5. Install OCR Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr poppler-utils
```

**macOS:**
```bash
brew install tesseract poppler
```

**Windows:**
- Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
- Download Poppler from: https://github.com/oschwartz10612/poppler-windows/releases

### 6. Frontend Setup

```bash
cd ../ui

# Install dependencies
npm install
```

## 🎮 Usage

### Start the Backend

```bash
cd api
source venv/bin/activate
uvicorn src.main:app --reload
```

Backend will be available at: `http://localhost:8000`

### Start the Frontend

```bash
cd ui
npm run dev
```

Frontend will be available at: `http://localhost:3000`

### Using the Application

1. **Upload PDF**: Select a medical order PDF file
2. **Parse**: Click "Upload and Parse" to extract data
3. **Review & Edit**: Review the extracted information and make any necessary corrections
   - Edit patient information (MRN, name, age)
   - Edit prescriber details (NPI, contact info)
   - Edit order details (item, quantity, costs, reason)
   - Add/remove/edit devices
4. **Save**: Click "Save to Database" to persist the order
5. **Review Results**: See the saved order with database IDs and any duplicate warnings

## 📡 API Endpoints

### PDF Processing

**Parse PDF (Preview Only)**
```http
POST /orders/parse-pdf-preview
Content-Type: multipart/form-data

Returns: ParsedOrderData (no database persistence)
```

**Parse PDF and Save** (Legacy)
```http
POST /orders/parse-pdf
Content-Type: multipart/form-data

Returns: OrderRead (auto-saves to database)
```

### Order Management

**Create Order**
```http
POST /order
Content-Type: application/json

Body: {
  "patient": { "medical_record_number": "MRN123", ... },
  "prescriber": { "first_name": "John", "last_name": "Doe", ... },
  "devices": [{ "name": "Device Name", "sku": "SKU123" }],
  "item_name": "Order Item",
  "item_quantity": 1,
  ...
}

Returns: OrderCreateResponse (includes duplicate warnings)
```

**Get Order**
```http
GET /order?order_id=1

Returns: OrderRead
```

## 🔍 Features in Detail

### Intelligent PDF Parsing

The system uses a two-stage approach:
1. **Text Extraction**: Attempts to extract text directly from PDF
2. **OCR Fallback**: If minimal text is found, converts pages to images and uses OCR

The extracted text is then sent to a local Llama 3.1 model with a structured prompt to extract:
- Patient demographics and identifiers
- Prescriber information and credentials
- Device/equipment details
- Order-specific information

### Duplicate Detection

When saving an order, the system checks for potential duplicates by:
- Matching patient and prescriber
- Comparing item names (exact and partial matches)
- Calculating a similarity score
- Displaying warnings without blocking submission

Example warning:
```
⚠️ Potential Duplicate Orders Detected
Order #15 - Wheelchair (Qty: 1)
  Reasons: Exact item name match
```

### Idempotent Entity Creation

Patients, prescribers, and devices use "get or create" logic:
- **Patients**: Lookup by Medical Record Number (MRN)
- **Prescribers**: Lookup by National Provider Index (NPI)
- **Devices**: Lookup by Stock Keeping Unit (SKU)

This prevents duplicate entities in the database.

## 💾 Database Schema

### Core Tables

**patients**
- `id` (PK)
- `medical_record_number` (Unique)
- `first_name`, `last_name`, `age`

**prescribers**
- `id` (PK)
- `npi` (Unique, Optional)
- `first_name`, `last_name`
- `phone_number`, `email`
- `clinic_name`, `clinic_address`

**devices**
- `id` (PK)
- `sku` (Unique, Optional)
- `name`
- `device_type`, `details`
- `cost_per_unit`, `authorization_required`

**orders**
- `id` (PK)
- `patient_id` (FK), `prescriber_id` (FK)
- `item_name`, `item_quantity`
- `order_cost_raw`, `order_cost_to_insurer`
- `reason_prescribed`

**order_devices** (Junction Table)
- `order_id` (FK), `device_id` (FK)
- `quantity`

## 🧪 Development

### Running Migrations

Create a new migration:
```bash
cd api
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

### Adding New Fields

1. Update the model in `api/src/models.py`
2. Update the schema in `api/src/schemas.py`
3. Create and run migration
4. Update frontend if needed

## 💰 Cost Analysis

**Traditional Approach (Cloud APIs):**
- OpenAI GPT-4 Vision: ~$0.01-0.03 per page
- Document AI services: ~$1.50 per 1000 pages
- **Monthly cost for 500 PDFs**: $15-30+

**This Implementation (Local):**
- Ollama: FREE
- Tesseract OCR: FREE
- **Monthly cost**: $0 💰

## 🐛 Troubleshooting

### PDF Parsing Fails

**Error: "Model not found"**
```bash
# Pull the required model
ollama pull llama3.1:8b

# Verify Ollama is running
ollama list
```

**Error: "Tesseract not found"**
- Ensure Tesseract is installed and in your PATH
- On Windows, add Tesseract installation directory to PATH

### Database Connection Issues

```bash
# Verify PostgreSQL is running
pg_isready

# Check connection settings
psql -U postgres -d postgres_gen_health_ai
```

### Frontend 404 Errors

- Ensure Vite proxy is configured for both `/order` and `/orders`
- Restart the Vite dev server after config changes

## 📝 License

[Your License Here]

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgments

- Ollama for providing free local LLM infrastructure
- Tesseract OCR for open-source text recognition
- FastAPI and React communities for excellent documentation

---

**Built with ❤️ for efficient medical order processing**
