"""
Unit tests for service functions.

Tests the business logic in services.py including entity creation,
lookups, duplicate detection, and order processing.
"""

import pytest
from sqlalchemy.orm import Session

from src import services
from src.models import Patient, Prescriber, Device, Order
from src.schemas import OrderCreate, PatientCreate, PrescriberCreate, DeviceCreate


class TestGetOrCreatePatient:
    """Test the get_or_create_patient function."""

    def test_create_new_patient(self, db_session: Session, sample_patient_data):
        """Test creating a new patient."""
        patient_id = services.get_or_create_patient(db_session, sample_patient_data)

        # Verify patient was created
        patient = db_session.query(Patient).filter(Patient.id == patient_id).first()
        assert patient is not None
        assert patient.medical_record_number == sample_patient_data["medical_record_number"]
        assert patient.first_name == sample_patient_data["first_name"]
        assert patient.last_name == sample_patient_data["last_name"]
        assert patient.age == sample_patient_data["age"]

    def test_get_existing_patient(self, db_session: Session, sample_patient):
        """Test retrieving an existing patient by MRN."""
        patient_data = {
            "medical_record_number": sample_patient.medical_record_number,
            "first_name": "Different",
            "last_name": "Name",
            "age": 99
        }

        patient_id = services.get_or_create_patient(db_session, patient_data)

        # Should return the existing patient's ID
        assert patient_id == sample_patient.id

        # Patient data should remain unchanged
        patient = db_session.query(Patient).filter(Patient.id == patient_id).first()
        assert patient.first_name == sample_patient.first_name
        assert patient.last_name == sample_patient.last_name

    def test_create_patient_without_age(self, db_session: Session):
        """Test creating a patient without age (optional field)."""
        patient_data = {
            "medical_record_number": "MRN99999",
            "first_name": "NoAge",
            "last_name": "Person",
            "age": None
        }

        patient_id = services.get_or_create_patient(db_session, patient_data)

        patient = db_session.query(Patient).filter(Patient.id == patient_id).first()
        assert patient is not None
        assert patient.age is None


class TestGetOrCreatePrescriber:
    """Test the get_or_create_prescriber function."""

    def test_create_new_prescriber(self, db_session: Session, sample_prescriber_data):
        """Test creating a new prescriber."""
        prescriber_id = services.get_or_create_prescriber(db_session, sample_prescriber_data)

        # Verify prescriber was created
        prescriber = db_session.query(Prescriber).filter(Prescriber.id == prescriber_id).first()
        assert prescriber is not None
        assert prescriber.npi == sample_prescriber_data["npi"]
        assert prescriber.first_name == sample_prescriber_data["first_name"]
        assert prescriber.last_name == sample_prescriber_data["last_name"]

    def test_get_existing_prescriber_by_npi(self, db_session: Session, sample_prescriber):
        """Test retrieving an existing prescriber by NPI."""
        prescriber_data = {
            "first_name": "Different",
            "last_name": "Doctor",
            "npi": sample_prescriber.npi,
            "phone_number": "999-9999",
            "email": "different@example.com",
            "clinic_name": "Different Clinic",
            "clinic_address": "Different Address"
        }

        prescriber_id = services.get_or_create_prescriber(db_session, prescriber_data)

        # Should return the existing prescriber's ID
        assert prescriber_id == sample_prescriber.id

        # Prescriber data should remain unchanged
        prescriber = db_session.query(Prescriber).filter(Prescriber.id == prescriber_id).first()
        assert prescriber.first_name == sample_prescriber.first_name

    def test_create_prescriber_without_npi(self, db_session: Session):
        """Test creating a prescriber without NPI (should still create)."""
        prescriber_data = {
            "first_name": "NoNPI",
            "last_name": "Doctor",
            "npi": None,
            "phone_number": "555-0000",
            "email": "nonpi@example.com",
            "clinic_name": "Clinic",
            "clinic_address": "Address"
        }

        prescriber_id = services.get_or_create_prescriber(db_session, prescriber_data)

        prescriber = db_session.query(Prescriber).filter(Prescriber.id == prescriber_id).first()
        assert prescriber is not None
        assert prescriber.npi is None


class TestGetOrCreateDevice:
    """Test the get_or_create_device function."""

    def test_create_new_device(self, db_session: Session, sample_device_data):
        """Test creating a new device."""
        device_id = services.get_or_create_device(db_session, sample_device_data)

        # Verify device was created
        device = db_session.query(Device).filter(Device.id == device_id).first()
        assert device is not None
        assert device.sku == sample_device_data["sku"]
        assert device.name == sample_device_data["name"]
        assert device.cost_per_unit == sample_device_data["cost_per_unit"]

    def test_get_existing_device_by_sku(self, db_session: Session, sample_device):
        """Test retrieving an existing device by SKU."""
        device_data = {
            "sku": sample_device.sku,
            "name": "Different Name",
            "details": "Different details",
            "authorization_required": False,
            "cost_per_unit": 99999,
            "device_type": "Different Type"
        }

        device_id = services.get_or_create_device(db_session, device_data)

        # Should return the existing device's ID
        assert device_id == sample_device.id

        # Device data should remain unchanged
        device = db_session.query(Device).filter(Device.id == device_id).first()
        assert device.name == sample_device.name

    def test_create_device_without_sku(self, db_session: Session):
        """Test creating a device without SKU (should still create)."""
        device_data = {
            "sku": None,
            "name": "NoSKU Device",
            "details": None,
            "authorization_required": False,
            "cost_per_unit": 10000,
            "device_type": "Test"
        }

        device_id = services.get_or_create_device(db_session, device_data)

        device = db_session.query(Device).filter(Device.id == device_id).first()
        assert device is not None
        assert device.sku is None


class TestCheckForDuplicateOrders:
    """Test the check_for_duplicate_orders function."""

    def test_no_duplicates_found(self, db_session: Session, sample_patient, sample_prescriber):
        """Test when no duplicate orders exist."""
        duplicates = services.check_for_duplicate_orders(
            db_session,
            patient_id=sample_patient.id,
            prescriber_id=sample_prescriber.id,
            item_name="Unique Item"
        )

        assert len(duplicates) == 0

    def test_exact_match_duplicate(self, db_session: Session, sample_order):
        """Test detecting duplicate with exact item name match."""
        duplicates = services.check_for_duplicate_orders(
            db_session,
            patient_id=sample_order.patient_id,
            prescriber_id=sample_order.prescriber_id,
            item_name=sample_order.item_name
        )

        assert len(duplicates) == 1
        assert duplicates[0]["order_id"] == sample_order.id
        assert "Exact item name match" in duplicates[0]["reasons"]
        assert duplicates[0]["similarity_score"] >= 2

    def test_similar_item_name_duplicate(self, db_session: Session, sample_order):
        """Test detecting duplicate with similar item name."""
        # Create order with item containing the sample order's item name
        duplicates = services.check_for_duplicate_orders(
            db_session,
            patient_id=sample_order.patient_id,
            prescriber_id=sample_order.prescriber_id,
            item_name=f"{sample_order.item_name} Plus"
        )

        assert len(duplicates) == 1
        assert duplicates[0]["order_id"] == sample_order.id
        assert "Similar item name" in duplicates[0]["reasons"]

    def test_no_duplicate_different_patient(self, db_session: Session, sample_order, sample_patient_data):
        """Test that orders for different patients are not considered duplicates."""
        # Create a different patient
        different_patient = Patient(**sample_patient_data)
        db_session.add(different_patient)
        db_session.commit()

        duplicates = services.check_for_duplicate_orders(
            db_session,
            patient_id=different_patient.id,
            prescriber_id=sample_order.prescriber_id,
            item_name=sample_order.item_name
        )

        assert len(duplicates) == 0

    def test_no_duplicate_different_prescriber(self, db_session: Session, sample_order, sample_prescriber_data):
        """Test that orders from different prescribers are not considered duplicates."""
        # Create a different prescriber
        different_prescriber = Prescriber(**sample_prescriber_data)
        db_session.add(different_prescriber)
        db_session.commit()

        duplicates = services.check_for_duplicate_orders(
            db_session,
            patient_id=sample_order.patient_id,
            prescriber_id=different_prescriber.id,
            item_name=sample_order.item_name
        )

        assert len(duplicates) == 0


class TestCreateOrder:
    """Test the create_order function."""

    def test_create_order_with_existing_ids(self, db_session: Session, sample_order_create_data):
        """Test creating an order using existing patient and prescriber IDs."""
        order_create = OrderCreate(**sample_order_create_data)

        result = services.create_order(db_session, order_create)

        # Verify order was created
        assert "order" in result
        assert result["order"].id is not None
        assert result["order"].item_name == sample_order_create_data["item_name"]
        assert result["order"].patient_id == sample_order_create_data["patient_id"]
        assert result["order"].prescriber_id == sample_order_create_data["prescriber_id"]

    def test_create_order_with_patient_object(self, db_session: Session, sample_prescriber, sample_patient_data):
        """Test creating an order with patient data (lookup/create pattern)."""
        order_data = {
            "item_name": "Test Device",
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 1,
            "reason_prescribed": "Testing",
            "patient": PatientCreate(**sample_patient_data),
            "prescriber_id": sample_prescriber.id,
            "device_ids": []
        }

        order_create = OrderCreate(**order_data)
        result = services.create_order(db_session, order_create)

        # Verify order was created
        assert result["order"].id is not None

        # Verify patient was created
        patient = db_session.query(Patient).filter(
            Patient.medical_record_number == sample_patient_data["medical_record_number"]
        ).first()
        assert patient is not None
        assert result["order"].patient_id == patient.id

    def test_create_order_with_prescriber_object(self, db_session: Session, sample_patient, sample_prescriber_data):
        """Test creating an order with prescriber data (lookup/create pattern)."""
        order_data = {
            "item_name": "Test Device",
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 1,
            "reason_prescribed": "Testing",
            "patient_id": sample_patient.id,
            "prescriber": PrescriberCreate(**sample_prescriber_data),
            "device_ids": []
        }

        order_create = OrderCreate(**order_data)
        result = services.create_order(db_session, order_create)

        # Verify order was created
        assert result["order"].id is not None

        # Verify prescriber was created
        prescriber = db_session.query(Prescriber).filter(
            Prescriber.npi == sample_prescriber_data["npi"]
        ).first()
        assert prescriber is not None
        assert result["order"].prescriber_id == prescriber.id

    def test_create_order_with_device_ids(self, db_session: Session, sample_patient, sample_prescriber, sample_device):
        """Test creating an order with existing device IDs."""
        order_data = {
            "item_name": "Test Device",
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 1,
            "reason_prescribed": "Testing",
            "patient_id": sample_patient.id,
            "prescriber_id": sample_prescriber.id,
            "device_ids": [sample_device.id]
        }

        order_create = OrderCreate(**order_data)
        result = services.create_order(db_session, order_create)

        # Verify order was created with device
        assert result["order"].id is not None
        assert len(result["order"].devices) == 1
        assert result["order"].devices[0].id == sample_device.id

    def test_create_order_with_device_objects(self, db_session: Session, sample_patient, sample_prescriber, sample_device_data):
        """Test creating an order with device data (lookup/create pattern)."""
        order_data = {
            "item_name": "Test Device",
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 1,
            "reason_prescribed": "Testing",
            "patient_id": sample_patient.id,
            "prescriber_id": sample_prescriber.id,
            "devices": [DeviceCreate(**sample_device_data)]
        }

        order_create = OrderCreate(**order_data)
        result = services.create_order(db_session, order_create)

        # Verify order was created
        assert result["order"].id is not None

        # Verify device was created
        device = db_session.query(Device).filter(
            Device.sku == sample_device_data["sku"]
        ).first()
        assert device is not None
        assert len(result["order"].devices) == 1
        assert result["order"].devices[0].id == device.id

    def test_create_order_invalid_patient_id(self, db_session: Session, sample_prescriber):
        """Test creating an order with non-existent patient ID."""
        order_data = {
            "item_name": "Test Device",
            "patient_id": 99999,  # Non-existent ID
            "prescriber_id": sample_prescriber.id,
            "device_ids": []
        }

        order_create = OrderCreate(**order_data)

        with pytest.raises(ValueError, match="Patient with id 99999 does not exist"):
            services.create_order(db_session, order_create)

    def test_create_order_invalid_prescriber_id(self, db_session: Session, sample_patient):
        """Test creating an order with non-existent prescriber ID."""
        order_data = {
            "item_name": "Test Device",
            "patient_id": sample_patient.id,
            "prescriber_id": 99999,  # Non-existent ID
            "device_ids": []
        }

        order_create = OrderCreate(**order_data)

        with pytest.raises(ValueError, match="Prescriber with id 99999 does not exist"):
            services.create_order(db_session, order_create)

    def test_create_order_invalid_device_ids(self, db_session: Session, sample_patient, sample_prescriber):
        """Test creating an order with non-existent device IDs."""
        order_data = {
            "item_name": "Test Device",
            "patient_id": sample_patient.id,
            "prescriber_id": sample_prescriber.id,
            "device_ids": [99999]  # Non-existent ID
        }

        order_create = OrderCreate(**order_data)

        with pytest.raises(ValueError, match="Devices with ids .* do not exist"):
            services.create_order(db_session, order_create)

    def test_create_order_with_duplicate_warning(self, db_session: Session, sample_order):
        """Test that duplicate warnings are returned when creating similar orders."""
        order_data = {
            "item_name": sample_order.item_name,  # Same item name
            "order_cost_raw": 10000,
            "order_cost_to_insurer": 8000,
            "item_quantity": 1,
            "reason_prescribed": "Testing",
            "patient_id": sample_order.patient_id,  # Same patient
            "prescriber_id": sample_order.prescriber_id,  # Same prescriber
            "device_ids": []
        }

        order_create = OrderCreate(**order_data)
        result = services.create_order(db_session, order_create)

        # Verify duplicate warning was returned
        assert result["has_duplicates"] is True
        assert len(result["duplicate_warnings"]) > 0
        assert result["duplicate_warnings"][0]["order_id"] == sample_order.id

    def test_create_order_lookup_existing_patient_by_mrn(self, db_session: Session, sample_patient, sample_prescriber):
        """Test that providing existing patient MRN returns the same patient."""
        patient_data = PatientCreate(
            medical_record_number=sample_patient.medical_record_number,
            first_name="Different",
            last_name="Name",
            age=99
        )

        order_data = {
            "item_name": "Test Device",
            "patient": patient_data,
            "prescriber_id": sample_prescriber.id,
            "device_ids": []
        }

        order_create = OrderCreate(**order_data)
        result = services.create_order(db_session, order_create)

        # Should use the existing patient, not create a new one
        assert result["order"].patient_id == sample_patient.id

        # Verify only one patient exists with that MRN
        patient_count = db_session.query(Patient).filter(
            Patient.medical_record_number == sample_patient.medical_record_number
        ).count()
        assert patient_count == 1

    def test_create_order_lookup_existing_prescriber_by_npi(self, db_session: Session, sample_patient, sample_prescriber):
        """Test that providing existing prescriber NPI returns the same prescriber."""
        prescriber_data = PrescriberCreate(
            first_name="Different",
            last_name="Name",
            npi=sample_prescriber.npi,
            phone_number="999-9999",
            email="different@example.com",
            clinic_name="Different Clinic",
            clinic_address="Different Address"
        )

        order_data = {
            "item_name": "Test Device",
            "patient_id": sample_patient.id,
            "prescriber": prescriber_data,
            "device_ids": []
        }

        order_create = OrderCreate(**order_data)
        result = services.create_order(db_session, order_create)

        # Should use the existing prescriber, not create a new one
        assert result["order"].prescriber_id == sample_prescriber.id

        # Verify only one prescriber exists with that NPI
        prescriber_count = db_session.query(Prescriber).filter(
            Prescriber.npi == sample_prescriber.npi
        ).count()
        assert prescriber_count == 1
