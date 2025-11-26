"""
Unit tests for FastAPI endpoints.

Tests all API routes including order CRUD operations and PDF parsing endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from io import BytesIO

from src.schemas import ParsedOrderData, PatientCreate, PrescriberCreate, ParsedDeviceInfo


class TestRootEndpoint:
    """Test the root endpoint."""

    def test_read_root(self, client: TestClient):
        """Test GET / returns welcome message."""
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}


class TestGetOrderEndpoint:
    """Test the GET /order endpoint."""

    def test_get_existing_order(self, client: TestClient, sample_order):
        """Test retrieving an existing order by ID."""
        response = client.get(f"/order?order_id={sample_order.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_order.id
        assert data["item_name"] == sample_order.item_name

    def test_get_nonexistent_order(self, client: TestClient):
        """Test retrieving a non-existent order returns 404."""
        response = client.get("/order?order_id=99999")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_get_order_with_relationships(self, client: TestClient, sample_order):
        """Test that order includes patient, prescriber, and device relationships."""
        response = client.get(f"/order?order_id={sample_order.id}")

        assert response.status_code == 200
        data = response.json()

        # Verify patient relationship
        assert "patient_id" in data
        assert data["patient_id"] == sample_order.patient_id

        # Verify prescriber relationship
        assert "prescriber_id" in data
        assert data["prescriber_id"] == sample_order.prescriber_id


class TestCreateOrderEndpoint:
    """Test the POST /order endpoint."""

    def test_create_order_with_existing_ids(self, client: TestClient, sample_patient, sample_prescriber):
        """Test creating an order with existing patient and prescriber IDs."""
        order_data = {
            "item_name": "Test Device",
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 1,
            "reason_prescribed": "Testing",
            "patient_id": sample_patient.id,
            "prescriber_id": sample_prescriber.id,
            "device_ids": []
        }

        response = client.post("/order", json=order_data)

        assert response.status_code == 200
        data = response.json()
        assert "order" in data
        assert data["order"]["item_name"] == order_data["item_name"]
        assert data["order"]["patient_id"] == sample_patient.id
        assert data["order"]["prescriber_id"] == sample_prescriber.id

    def test_create_order_with_patient_object(self, client: TestClient, sample_prescriber):
        """Test creating an order with patient data (lookup/create)."""
        order_data = {
            "item_name": "Test Device",
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 1,
            "reason_prescribed": "Testing",
            "patient": {
                "medical_record_number": "MRN-NEW-001",
                "first_name": "New",
                "last_name": "Patient",
                "age": 50
            },
            "prescriber_id": sample_prescriber.id,
            "device_ids": []
        }

        response = client.post("/order", json=order_data)

        assert response.status_code == 200
        data = response.json()
        assert "order" in data
        assert data["order"]["patient"]["medical_record_number"] == "MRN-NEW-001"

    def test_create_order_with_prescriber_object(self, client: TestClient, sample_patient):
        """Test creating an order with prescriber data (lookup/create)."""
        order_data = {
            "item_name": "Test Device",
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 1,
            "reason_prescribed": "Testing",
            "patient_id": sample_patient.id,
            "prescriber": {
                "first_name": "New",
                "last_name": "Prescriber",
                "npi": "1111111111",
                "phone_number": "555-1111",
                "email": "new@example.com",
                "clinic_name": "New Clinic",
                "clinic_address": "New Address"
            },
            "device_ids": []
        }

        response = client.post("/order", json=order_data)

        assert response.status_code == 200
        data = response.json()
        assert "order" in data
        assert data["order"]["prescriber"]["npi"] == "1111111111"

    def test_create_order_with_devices(self, client: TestClient, sample_patient, sample_prescriber):
        """Test creating an order with device data."""
        order_data = {
            "item_name": "Test Device",
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 2,
            "reason_prescribed": "Testing",
            "patient_id": sample_patient.id,
            "prescriber_id": sample_prescriber.id,
            "devices": [
                {
                    "sku": "SKU-TEST-001",
                    "name": "Test Device 1",
                    "details": "Test details",
                    "authorization_required": False,
                    "cost_per_unit": 5000,
                    "device_type": "Test"
                },
                {
                    "sku": "SKU-TEST-002",
                    "name": "Test Device 2",
                    "details": "Test details 2",
                    "authorization_required": True,
                    "cost_per_unit": 7500,
                    "device_type": "Test"
                }
            ]
        }

        response = client.post("/order", json=order_data)

        assert response.status_code == 200
        data = response.json()
        assert "order" in data
        assert len(data["order"]["devices"]) == 2

    def test_create_order_invalid_patient_id(self, client: TestClient, sample_prescriber):
        """Test creating an order with non-existent patient ID returns error."""
        order_data = {
            "item_name": "Test Device",
            "patient_id": 99999,
            "prescriber_id": sample_prescriber.id,
            "device_ids": []
        }

        response = client.post("/order", json=order_data)

        assert response.status_code == 422  # Unprocessable Entity

    def test_create_order_invalid_prescriber_id(self, client: TestClient, sample_patient):
        """Test creating an order with non-existent prescriber ID returns error."""
        order_data = {
            "item_name": "Test Device",
            "patient_id": sample_patient.id,
            "prescriber_id": 99999,
            "device_ids": []
        }

        response = client.post("/order", json=order_data)

        assert response.status_code == 422  # Unprocessable Entity

    def test_create_order_missing_patient_and_prescriber(self, client: TestClient):
        """Test creating an order without patient or prescriber returns validation error."""
        order_data = {
            "item_name": "Test Device",
            "device_ids": []
        }

        response = client.post("/order", json=order_data)

        assert response.status_code == 422  # Validation error

    def test_create_order_returns_duplicate_warnings(self, client: TestClient, sample_order):
        """Test that creating a similar order returns duplicate warnings."""
        order_data = {
            "item_name": sample_order.item_name,
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 1,
            "reason_prescribed": "Testing",
            "patient_id": sample_order.patient_id,
            "prescriber_id": sample_order.prescriber_id,
            "device_ids": []
        }

        response = client.post("/order", json=order_data)

        assert response.status_code == 200
        data = response.json()
        assert data["has_duplicates"] is True
        assert len(data["duplicate_warnings"]) > 0


class TestParsePDFPreviewEndpoint:
    """Test the POST /orders/parse-pdf-preview endpoint."""

    def test_parse_pdf_preview_invalid_file_type(self, client: TestClient):
        """Test uploading non-PDF file returns error."""
        # Create a fake text file
        file_content = b"This is not a PDF"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = client.post("/orders/parse-pdf-preview", files=files)

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_parse_pdf_preview_file_too_large(self, client: TestClient):
        """Test uploading file larger than limit returns error."""
        # Create a fake PDF that's too large (> 10MB)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        files = {"file": ("test.pdf", BytesIO(large_content), "application/pdf")}

        response = client.post("/orders/parse-pdf-preview", files=files)

        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]

    @patch('src.services.parse_order_pdf')
    def test_parse_pdf_preview_success(self, mock_parse_pdf, client: TestClient):
        """Test successfully parsing a PDF preview."""
        # Mock the parse_order_pdf function
        mock_parsed_data = ParsedOrderData(
            patient=PatientCreate(
                medical_record_number="MRN12345",
                first_name="John",
                last_name="Doe",
                age=45
            ),
            prescriber=PrescriberCreate(
                first_name="Dr",
                last_name="Smith",
                npi="1234567890",
                phone_number="555-1234",
                email="dr.smith@example.com",
                clinic_name="Test Clinic",
                clinic_address="123 Main St"
            ),
            devices=[
                ParsedDeviceInfo(
                    name="Test Device",
                    sku="SKU-001",
                    quantity=1
                )
            ],
            item_name="Test Device",
            item_quantity=1,
            reason_prescribed="Testing",
            confidence_score=0.9,
            extraction_notes="Test extraction"
        )
        mock_parse_pdf.return_value = mock_parsed_data

        # Create a fake PDF file
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}

        response = client.post("/orders/parse-pdf-preview", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["patient"]["medical_record_number"] == "MRN12345"
        assert data["prescriber"]["npi"] == "1234567890"
        assert len(data["devices"]) == 1

    @patch('src.services.parse_order_pdf')
    def test_parse_pdf_preview_parsing_error(self, mock_parse_pdf, client: TestClient):
        """Test handling PDF parsing errors."""
        # Mock parsing error
        mock_parse_pdf.side_effect = ValueError("Failed to parse PDF")

        # Create a fake PDF file
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}

        response = client.post("/orders/parse-pdf-preview", files=files)

        assert response.status_code == 400
        assert "Failed to parse PDF" in response.json()["detail"]


class TestParseAndCreateOrderFromPDFEndpoint:
    """Test the POST /orders/parse-pdf endpoint."""

    def test_parse_pdf_invalid_file_type(self, client: TestClient):
        """Test uploading non-PDF file returns error."""
        # Create a fake text file
        file_content = b"This is not a PDF"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = client.post("/orders/parse-pdf-direct-create", files=files)

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_parse_pdf_file_too_large(self, client: TestClient):
        """Test uploading file larger than limit returns error."""
        # Create a fake PDF that's too large (> 10MB)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        files = {"file": ("test.pdf", BytesIO(large_content), "application/pdf")}

        response = client.post("/orders/parse-pdf-direct-create", files=files)

        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]

    @patch('src.services.process_order_pdf')
    def test_parse_pdf_and_create_order_success(self, mock_process_pdf, client: TestClient, db_session, sample_patient, sample_prescriber, sample_device):
        """Test successfully parsing PDF and creating order."""
        # Create a mock order to return
        from src.models import Order
        mock_order = Order(
            id=1,
            item_name="Test Device",
            order_cost_raw=10000,
            order_cost_to_insurer=8000,
            item_quantity=1,
            reason_prescribed="Testing",
            patient_id=sample_patient.id,
            prescriber_id=sample_prescriber.id
        )
        mock_order.patient = sample_patient
        mock_order.prescriber = sample_prescriber
        mock_order.devices = [sample_device]

        mock_process_pdf.return_value = mock_order

        # Create a fake PDF file
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}

        response = client.post("/orders/parse-pdf-direct-create", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["item_name"] == "Test Device"
        assert data["patient_id"] == sample_patient.id
        assert data["prescriber_id"] == sample_prescriber.id

    @patch('src.services.process_order_pdf')
    def test_parse_pdf_processing_error(self, mock_process_pdf, client: TestClient):
        """Test handling PDF processing errors."""
        # Mock processing error
        mock_process_pdf.side_effect = ValueError("Failed to process PDF")

        # Create a fake PDF file
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}

        response = client.post("/orders/parse-pdf-direct-create", files=files)

        assert response.status_code == 400
        assert "Failed to process PDF" in response.json()["detail"]

    @patch('src.services.process_order_pdf')
    def test_parse_pdf_generic_error(self, mock_process_pdf, client: TestClient):
        """Test handling generic errors during PDF processing."""
        # Mock generic error
        mock_process_pdf.side_effect = Exception("Unexpected error")

        # Create a fake PDF file
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}

        response = client.post("/orders/parse-pdf-direct-create", files=files)

        assert response.status_code == 500
        assert "Failed to process PDF" in response.json()["detail"]
