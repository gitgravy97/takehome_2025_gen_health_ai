from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import BinaryIO, List, Dict, Any
from datetime import datetime, timedelta
import json
import tempfile
import os
import pymupdf4llm
import ollama
from pdf2image import convert_from_path
import pytesseract
from src.models import Order, Patient, Prescriber, Device
from src.schemas import OrderCreate, ParsedOrderData, ParsedDeviceInfo, PatientCreate, PrescriberCreate


def get_or_create_patient(db: Session, patient_data: dict) -> int:
    """
    Lookup patient by medical_record_number, create if doesn't exist.

    Args:
        db: Database session
        patient_data: Dict with patient information including medical_record_number

    Returns:
        patient_id: The ID of the found or created patient
    """
    # Lookup by medical_record_number (unique identifier)
    patient = db.query(Patient).filter(
        Patient.medical_record_number == patient_data["medical_record_number"]
    ).first()

    if patient:
        return patient.id

    # Create new patient if not found
    new_patient = Patient(**patient_data)
    db.add(new_patient)
    db.flush()  # Get ID without committing the transaction
    return new_patient.id


def get_or_create_prescriber(db: Session, prescriber_data: dict) -> int:
    """
    Lookup prescriber by NPI, create if doesn't exist.

    Args:
        db: Database session
        prescriber_data: Dict with prescriber information including NPI

    Returns:
        prescriber_id: The ID of the found or created prescriber
    """
    # If NPI provided, lookup by NPI (unique identifier)
    if prescriber_data.get("npi"):
        prescriber = db.query(Prescriber).filter(
            Prescriber.npi == prescriber_data["npi"]
        ).first()

        if prescriber:
            return prescriber.id

    # Create new prescriber if not found
    new_prescriber = Prescriber(**prescriber_data)
    db.add(new_prescriber)
    db.flush()  # Get ID without committing the transaction
    return new_prescriber.id


def get_or_create_device(db: Session, device_data: dict) -> int:
    """
    Lookup device by SKU, create if doesn't exist.

    Args:
        db: Database session
        device_data: Dict with device information including SKU

    Returns:
        device_id: The ID of the found or created device
    """
    # If SKU provided, lookup by SKU (unique identifier)
    if device_data.get("sku"):
        device = db.query(Device).filter(
            Device.sku == device_data["sku"]
        ).first()

        if device:
            return device.id

    # Create new device if not found
    new_device = Device(**device_data)
    db.add(new_device)
    db.flush()  # Get ID without committing the transaction
    return new_device.id


def check_for_duplicate_orders(
    db: Session,
    patient_id: int,
    prescriber_id: int,
    item_name: str = None,
    hours_lookback: int = 48
) -> List[Dict[str, Any]]:
    """
    Check for potential duplicate orders based on patient, prescriber, and item.

    Args:
        db: Database session
        patient_id: ID of the patient
        prescriber_id: ID of the prescriber
        item_name: Optional item name to match
        hours_lookback: How many hours to look back for duplicates (default 48)

    Returns:
        List of dictionaries containing potential duplicate order information
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_lookback)

    # Query for recent orders with same patient and prescriber
    query = db.query(Order).filter(
        Order.patient_id == patient_id,
        Order.prescriber_id == prescriber_id,
        Order.id > 0  # Ensure we only get existing orders
    )

    # Filter by creation time if the Order model has a timestamp field
    # Note: You may need to add a created_at field to your Order model
    # For now, we'll just check all orders with matching patient/prescriber

    potential_duplicates = []

    for order in query.all():
        similarity_score = 0
        reasons = []

        # Check if item names match
        if item_name and order.item_name:
            if item_name.lower() == order.item_name.lower():
                similarity_score += 3
                reasons.append("Exact item name match")
            elif item_name.lower() in order.item_name.lower() or order.item_name.lower() in item_name.lower():
                similarity_score += 2
                reasons.append("Similar item name")

        # Check if quantities match
        # (Add more similarity checks as needed)

        if similarity_score >= 2:
            potential_duplicates.append({
                "order_id": order.id,
                "item_name": order.item_name,
                "item_quantity": order.item_quantity,
                "reason_prescribed": order.reason_prescribed,
                "similarity_score": similarity_score,
                "reasons": reasons
            })

    return potential_duplicates


def create_order(db: Session, order_data: OrderCreate):
    """
    Create a new order with relationships to patient, prescriber, and devices.
    Supports both existing IDs and nested objects (lookup/create pattern).

    Args:
        db: Database session
        order_data: OrderCreate schema containing order details

    Returns:
        The created Order object with all relationships loaded

    Raises:
        ValueError: If patient, prescriber, or any device doesn't exist, or if a database constraint is violated
    """
    # Resolve patient_id (either from provided ID or by lookup/create)
    if order_data.patient_id:
        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == order_data.patient_id).first()
        if not patient:
            raise ValueError(f"Patient with id {order_data.patient_id} does not exist")
        patient_id = order_data.patient_id
    else:
        # Lookup or create patient by medical_record_number
        patient_id = get_or_create_patient(db, order_data.patient.model_dump())

    # Resolve prescriber_id (either from provided ID or by lookup/create)
    if order_data.prescriber_id:
        # Verify prescriber exists
        prescriber = db.query(Prescriber).filter(Prescriber.id == order_data.prescriber_id).first()
        if not prescriber:
            raise ValueError(f"Prescriber with id {order_data.prescriber_id} does not exist")
        prescriber_id = order_data.prescriber_id
    else:
        # Lookup or create prescriber by NPI
        prescriber_id = get_or_create_prescriber(db, order_data.prescriber.model_dump())

    # Check for potential duplicate orders
    duplicate_warnings = check_for_duplicate_orders(
        db=db,
        patient_id=patient_id,
        prescriber_id=prescriber_id,
        item_name=order_data.item_name
    )

    # Create the order with base fields and foreign keys
    new_order = Order(
        item_name=order_data.item_name,
        order_cost_raw=order_data.order_cost_raw,
        order_cost_to_insurer=order_data.order_cost_to_insurer,
        item_quantity=order_data.item_quantity,
        reason_prescribed=order_data.reason_prescribed,
        patient_id=patient_id,
        prescriber_id=prescriber_id
    )

    # Handle devices - support both device_ids and device objects
    if order_data.device_ids:
        # Lookup devices by IDs
        devices = db.query(Device).filter(Device.id.in_(order_data.device_ids)).all()

        # Verify all device IDs exist
        found_device_ids = {device.id for device in devices}
        missing_device_ids = set(order_data.device_ids) - found_device_ids
        if missing_device_ids:
            raise ValueError(f"Devices with ids {missing_device_ids} do not exist")

        # Add devices to the order
        new_order.devices = devices
    elif order_data.devices:
        # Lookup or create devices by SKU
        device_objects = []
        for device_data in order_data.devices:
            # Extract device fields, excluding 'quantity' which is for the association table
            device_dict = device_data.model_dump()
            device_dict.pop('quantity', None)  # Remove quantity if present

            device_id = get_or_create_device(db, device_dict)
            device = db.query(Device).filter(Device.id == device_id).first()
            device_objects.append(device)

        # Add devices to the order
        new_order.devices = device_objects

    try:
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Failed to create order: Database integrity constraint violated. {str(e.orig)}") from e

    return {
        "order": new_order,
        "duplicate_warnings": duplicate_warnings,
        "has_duplicates": len(duplicate_warnings) > 0
    }


def parse_order_pdf(pdf_file: BinaryIO, filename: str) -> ParsedOrderData:
    """
    Parse a medical order PDF using LLM-based intelligent extraction.

    Uses pymupdf4llm to convert PDF to markdown, then Ollama (local LLM)
    to extract structured data based on our schemas.

    Args:
        pdf_file: Binary file object containing the PDF
        filename: Name of the uploaded file

    Returns:
        ParsedOrderData: Structured data extracted from the PDF

    Raises:
        ValueError: If PDF cannot be parsed or LLM extraction fails
    """
    try:
        # Step 1: Read PDF bytes and save to temporary file
        pdf_bytes = pdf_file.read()

        # Reset file pointer in case it's needed later
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)

        # Step 2: Create temporary file for pymupdf4llm
        # pymupdf4llm requires a file path, not bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_file.flush()
            tmp_path = tmp_file.name

        try:
            # Step 3: Convert PDF to markdown using pymupdf4llm
            # This creates LLM-friendly format with preserved structure
            md_text = pymupdf4llm.to_markdown(tmp_path)

            # If extraction failed or returned very little text, try OCR
            if not md_text or len(md_text.strip()) < 10:
                # Scanned PDF detected - use OCR to extract text
                images = convert_from_path(tmp_path)

                # Extract text from each page using OCR
                ocr_text_parts = []
                for i, image in enumerate(images):
                    page_text = pytesseract.image_to_string(image)
                    ocr_text_parts.append(f"\n--- Page {i+1} ---\n{page_text}")

                md_text = "\n".join(ocr_text_parts)

                if not md_text or len(md_text.strip()) < 10:
                    raise ValueError(f"PDF appears to be empty or unreadable even with OCR. Extracted {len(md_text) if md_text else 0} characters.")
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # Step 4: Create structured prompt for LLM
        extraction_prompt = f"""You are a medical document parser. Extract the following information from this medical order document and return it as valid JSON.

Required fields (use null if not found):
- patient.medical_record_number (string): Patient's MRN or medical record number
- patient.first_name (string): Patient's first name
- patient.last_name (string): Patient's last name
- patient.age (number or null): Patient's age in years

- prescriber.first_name (string): Prescriber's first name
- prescriber.last_name (string): Prescriber's last name
- prescriber.npi (string): 10-digit NPI number (use "0000000000" if not found)
- prescriber.phone_number (string or null): Phone number
- prescriber.email (string or null): Email address
- prescriber.clinic_name (string or null): Clinic or practice name
- prescriber.clinic_address (string or null): Clinic address

- devices (array): List of devices/items ordered, each with:
  - name (string): Device/item name
  - sku (string): SKU or product code
  - quantity (number): Quantity ordered

- order.item_name (string or null): Primary item name
- order.item_quantity (number or null): Total quantity
- order.reason_prescribed (string or null): Reason for order or diagnosis

Return ONLY valid JSON in this exact format:
{{
  "patient": {{
    "medical_record_number": "string",
    "first_name": "string",
    "last_name": "string",
    "age": number_or_null
  }},
  "prescriber": {{
    "first_name": "string",
    "last_name": "string",
    "npi": "string",
    "phone_number": "string_or_null",
    "email": "string_or_null",
    "clinic_name": "string_or_null",
    "clinic_address": "string_or_null"
  }},
  "devices": [
    {{
      "name": "string",
      "sku": "string",
      "quantity": number
    }}
  ],
  "order": {{
    "item_name": "string_or_null",
    "item_quantity": number_or_null",
    "reason_prescribed": "string_or_null"
  }}
}}

Document content:
{md_text}

JSON output:"""

        # Step 5: Call local LLM via Ollama
        # NOTE: Requires Ollama to be running with a model pulled
        # Run: ollama pull llama3.1:8b (or mistral, phi3, etc.)
        try:
            response = ollama.chat(
                model='llama3.1:8b',  # Free local model
                messages=[{
                    'role': 'user',
                    'content': extraction_prompt
                }],
                format='json',  # Request JSON output
                options={
                    'temperature': 0.1,  # Low temperature for consistent extraction
                }
            )

            llm_output = response['message']['content']

        except Exception as e:
            raise ValueError(f"LLM extraction failed. Is Ollama running? Run 'ollama pull llama3.1:8b' first. Error: {str(e)}")

        # Step 6: Parse LLM JSON output
        try:
            extracted_data = json.loads(llm_output)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {str(e)}\nOutput: {llm_output[:500]}")

        # Step 7: Convert to Pydantic models
        patient_data = PatientCreate(
            medical_record_number=extracted_data['patient']['medical_record_number'],
            first_name=extracted_data['patient']['first_name'],
            last_name=extracted_data['patient']['last_name'],
            age=extracted_data['patient'].get('age')
        )

        prescriber_data = PrescriberCreate(
            first_name=extracted_data['prescriber']['first_name'],
            last_name=extracted_data['prescriber']['last_name'],
            npi=extracted_data['prescriber']['npi'],
            phone_number=extracted_data['prescriber'].get('phone_number'),
            email=extracted_data['prescriber'].get('email'),
            clinic_name=extracted_data['prescriber'].get('clinic_name'),
            clinic_address=extracted_data['prescriber'].get('clinic_address')
        )

        devices = [
            ParsedDeviceInfo(
                name=device['name'],
                sku=device['sku'],
                quantity=device.get('quantity', 1)
            )
            for device in extracted_data.get('devices', [])
        ]

        order_data = extracted_data.get('order', {})

        return ParsedOrderData(
            patient=patient_data,
            prescriber=prescriber_data,
            devices=devices,
            item_name=order_data.get('item_name'),
            order_cost_raw=None,  # Usually not in PDF
            order_cost_to_insurer=None,
            item_quantity=order_data.get('item_quantity'),
            reason_prescribed=order_data.get('reason_prescribed'),
            confidence_score=0.9,  # LLM extraction typically high confidence
            extraction_notes=f"Extracted from {filename} using Ollama (llama3.1:8b)"
        )

    except Exception as e:
        # Provide helpful error messages
        if "connection" in str(e).lower():
            raise ValueError("Cannot connect to Ollama. Make sure Ollama is running: 'ollama serve'")
        elif "model" in str(e).lower():
            raise ValueError("Model not found. Run: 'ollama pull llama3.1:8b'")
        else:
            raise ValueError(f"PDF parsing failed: {str(e)}")


def process_order_pdf(db: Session, pdf_file: BinaryIO, filename: str) -> Order:
    """
    Complete end-to-end PDF processing: parse, create entities, and create order.

    This function:
    1. Parses the PDF to extract structured data
    2. Creates or looks up Patient by MRN
    3. Creates or looks up Prescriber by NPI
    4. Creates or looks up Devices by SKU
    5. Creates the Order with all relationships

    Args:
        db: Database session
        pdf_file: Binary file object containing the PDF
        filename: Name of the uploaded file

    Returns:
        Order: The created order with all relationships loaded

    Raises:
        ValueError: If PDF parsing fails or required data is missing
    """
    # Step 1: Parse the PDF to extract structured data
    parsed_data = parse_order_pdf(pdf_file, filename)

    # Step 2: Validate that we have required data
    if not parsed_data.patient:
        raise ValueError("Failed to extract patient information from PDF")
    if not parsed_data.prescriber:
        raise ValueError("Failed to extract prescriber information from PDF")

    # Step 3: Get or create patient
    patient_id = get_or_create_patient(db, parsed_data.patient.model_dump())

    # Step 4: Get or create prescriber
    prescriber_id = get_or_create_prescriber(db, parsed_data.prescriber.model_dump())

    # Step 5: Get or create devices
    device_ids = []
    if parsed_data.devices:
        for device_info in parsed_data.devices:
            # Convert ParsedDeviceInfo to Device model fields
            device_data = {
                "name": device_info.name,
                "sku": device_info.sku,
                "details": None,  # Not extracted from PDF
                "authorization_required": False,  # Default, can be updated later
                "cost_per_unit": None,  # Not extracted from PDF
                "device_type": None  # Not extracted from PDF
            }
            device_id = get_or_create_device(db, device_data)
            device_ids.append(device_id)

    # Step 6: Create the order
    new_order = Order(
        item_name=parsed_data.item_name,
        order_cost_raw=parsed_data.order_cost_raw,
        order_cost_to_insurer=parsed_data.order_cost_to_insurer,
        item_quantity=parsed_data.item_quantity,
        reason_prescribed=parsed_data.reason_prescribed,
        patient_id=patient_id,
        prescriber_id=prescriber_id
    )

    # Add devices to the order
    if device_ids:
        devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
        new_order.devices = devices

    try:
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Failed to create order: {str(e.orig)}") from e

    return new_order