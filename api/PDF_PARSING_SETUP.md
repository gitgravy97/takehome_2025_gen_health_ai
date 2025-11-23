# PDF Parsing Setup with Ollama (Free LLM)

This system uses **Ollama** to run a local LLM for intelligent PDF extraction - completely free!

## Prerequisites

### 1. Install Ollama

**macOS/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download

### 2. Pull the LLM Model

We use Llama 3.1 (8B) - it's fast and accurate for extraction:

```bash
ollama pull llama3.1:8b
```

**Alternative models** (if you have more RAM/want better quality):
```bash
ollama pull mistral         # 7B model, good balance
ollama pull llama3.1        # 70B model, best quality but slower
ollama pull phi3            # 3B model, fastest but less accurate
```

### 3. Install OCR Dependencies (for scanned PDFs)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

**macOS:**
```bash
brew install tesseract poppler
```

**Windows:**
- Download Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
- Download Poppler from https://github.com/oschwartz10612/poppler-windows/releases

### 4. Start Ollama Service

Ollama runs as a background service:

```bash
ollama serve
```

Or it may auto-start after installation. Check if it's running:
```bash
ollama list
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  1. Upload PDF                                               │
│     POST /orders/parse-pdf                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Try Text Extraction (pymupdf4llm)                        │
│     Attempts to extract embedded text from PDF               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
                  Success?
                  /     \
                Yes     No
                 │       │
                 │       ▼
                 │    ┌────────────────────────────────────────┐
                 │    │  2b. OCR Fallback (Tesseract)          │
                 │    │      - Convert pages to images         │
                 │    │      - Extract text via OCR            │
                 │    └────────────┬───────────────────────────┘
                 │                 │
                 └─────────────┬───┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Send to Local LLM (Ollama)                               │
│     Structured prompt with JSON schema                       │
│     Model: llama3.1:8b (FREE, runs locally)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. LLM Extracts Structured Data                             │
│     - Patient info (MRN, name, age)                          │
│     - Prescriber info (NPI, contact details)                 │
│     - Devices (name, SKU, quantity)                          │
│     - Order details (reason, quantity)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Create/Lookup Entities                                   │
│     - Get or create Patient (by MRN)                         │
│     - Get or create Prescriber (by NPI)                      │
│     - Get or create Devices (by SKU)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Create Order → Return Result                             │
│     Complete order with all relationships                    │
└─────────────────────────────────────────────────────────────┘
```

## Testing

### Check Ollama is Running

```bash
curl http://localhost:11434/api/tags
```

Should return list of installed models.

### Test PDF Upload

Use the `test_api.http` file or curl:

```bash
curl -X POST http://localhost:8000/orders/parse-pdf \
  -F "file=@sample_order.pdf"
```

## Troubleshooting

### Error: "Cannot connect to Ollama"
**Solution:** Start Ollama service:
```bash
ollama serve
```

### Error: "Model not found"
**Solution:** Pull the model:
```bash
ollama pull llama3.1:8b
```

### Error: "PDF appears to be empty even with OCR"
- Check if PDF file is valid (not corrupted)
- Scanned PDFs are automatically handled with OCR fallback
- If OCR fails, ensure Tesseract and Poppler are installed correctly

### Slow Extraction
- Use a smaller model: `ollama pull phi3`
- Update code to use `phi3` instead of `llama3.1:8b`
- Or upgrade to a machine with more RAM/GPU

## Cost Analysis

| Component | Cost |
|-----------|------|
| Ollama | **FREE** - runs locally |
| llama3.1:8b model | **FREE** - open source |
| pymupdf4llm | **FREE** - open source |
| Tesseract OCR | **FREE** - open source |
| pdf2image | **FREE** - open source |
| RAM usage | ~8GB for llama3.1:8b |
| API calls | **NONE** - everything local |

**Total: $0/month** 🎉

**OCR Note**: Scanned PDFs take 5-10 seconds longer to process due to OCR, but remain completely free.

Compare to cloud alternatives:
- OpenAI GPT-4: ~$0.03/page
- Claude: ~$0.02/page
- AWS Textract: ~$0.0015/page

For 1000 PDFs/month: **Save $15-30/month**

## Customization

### Change Model

Edit `services.py` line 255:
```python
response = ollama.chat(
    model='mistral',  # Change to any installed model
    ...
)
```

### Adjust Temperature

Lower = more consistent, Higher = more creative:
```python
options={
    'temperature': 0.1,  # 0.0-1.0
}
```

### Improve Extraction Prompt

Edit the `extraction_prompt` in `services.py` to add more fields or better instructions.

## Production Considerations

1. **Error Handling**: Already implemented with helpful messages
2. **Scaling**: Ollama can handle ~10-20 concurrent requests
3. **Monitoring**: Add logging for extraction quality/confidence
4. **Fallback**: Could add cloud LLM as backup if Ollama fails
5. **Security**: Ollama runs locally - no data leaves your server

## Next Steps

- [x] Test with real medical order PDFs (both text and scanned)
- [x] Add OCR support for scanned documents
- [ ] Adjust prompt based on your specific PDF format
- [ ] Fine-tune extraction confidence scoring
- [ ] Add validation for extracted data quality
- [ ] Consider adding OCR language packs for non-English PDFs
