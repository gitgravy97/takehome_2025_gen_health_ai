from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from . import database
from . import models
from . import schemas
from . import services

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def validate_pdf_file(file: UploadFile, max_size_mb: int = 10):
    """
    Validate that uploaded file is a PDF and within size limits.

    Args:
        file: The uploaded file to validate
        max_size_mb: Maximum file size in megabytes (default: 10)

    Returns:
        The file content as bytes

    Raises:
        HTTPException: If validation fails
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are accepted."
        )

    # Validate file size
    content = await file.read()
    max_size = max_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {max_size_mb}MB."
        )

    # Reset file pointer after reading
    await file.seek(0)

    return content

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/order")
def read_user(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail=None)
    return order

@app.post("/order", response_model=schemas.OrderCreateResponse)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        result = services.create_order(db, order)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.post("/orders/parse-pdf-preview", response_model=schemas.ParsedOrderData)
async def parse_pdf_preview(file: UploadFile = File(...)):
    """
    Parse a medical order PDF and return extracted data WITHOUT persisting to database.

    This endpoint only extracts structured data from the PDF:
    - Patient information (name, MRN, age)
    - Prescriber information (name, NPI, contact details)
    - Device/item information (name, SKU, quantity)
    - Order details (costs, reason, etc.)

    Use this endpoint to preview/edit the extracted data before submission.
    Returns parsed data that can be edited and then submitted via POST /order.
    """
    # Validate PDF file
    await validate_pdf_file(file)

    try:
        # Parse PDF without persisting to database
        parsed_data = services.parse_order_pdf(file.file, file.filename)
        return parsed_data
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse PDF: {str(e)}"
        )


@app.post("/orders/parse-pdf-direct-create", response_model=schemas.OrderRead)
async def parse_and_create_order_from_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Parse a medical order PDF and automatically create the order with all dependencies.

    This endpoint performs a complete end-to-end workflow:
    1. Parses the uploaded PDF to extract structured data
    2. Creates or looks up Patient (by medical record number)
    3. Creates or looks up Prescriber (by NPI)
    4. Creates or looks up Devices (by SKU)
    5. Creates the Order with all relationships

    Upload a PDF file containing a medical order with:
    - Patient information (name, MRN, age)
    - Prescriber information (name, NPI, contact details)
    - Device/item information (name, SKU, quantity)
    - Order details (costs, reason, etc.)

    Returns the created Order object with all relationships populated.
    """
    # Validate PDF file
    await validate_pdf_file(file)

    try:
        # Process PDF: parse, create entities, and create order
        created_order = services.process_order_pdf(db, file.file, file.filename)
        return created_order
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {str(e)}"
        )
    