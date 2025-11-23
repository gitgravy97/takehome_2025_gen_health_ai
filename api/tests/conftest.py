"""
Pytest configuration and fixtures for API testing.

This module provides shared fixtures for testing the FastAPI application,
including test database setup, test client, and sample data.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.database import Base
from src.main import app, get_db
from src.models import Patient, Prescriber, Device, Order


# Use in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test database engine
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database for each test.

    Yields:
        Database session for testing
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create a new session for the test
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a FastAPI test client with overridden database dependency.

    Args:
        db_session: Test database session fixture

    Returns:
        TestClient for making API requests
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest.fixture
def sample_patient(db_session):
    """
    Create a sample patient for testing.

    Args:
        db_session: Test database session

    Returns:
        Patient object
    """
    patient = Patient(
        medical_record_number="MRN12345",
        first_name="John",
        last_name="Doe",
        age=45
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture
def sample_prescriber(db_session):
    """
    Create a sample prescriber for testing.

    Args:
        db_session: Test database session

    Returns:
        Prescriber object
    """
    prescriber = Prescriber(
        first_name="Jane",
        last_name="Smith",
        npi="1234567890",
        phone_number="555-1234",
        email="jane.smith@example.com",
        clinic_name="Test Clinic",
        clinic_address="123 Main St, City, State 12345"
    )
    db_session.add(prescriber)
    db_session.commit()
    db_session.refresh(prescriber)
    return prescriber


@pytest.fixture
def sample_device(db_session):
    """
    Create a sample device for testing.

    Args:
        db_session: Test database session

    Returns:
        Device object
    """
    device = Device(
        sku="SKU-12345",
        name="Continuous Glucose Monitor",
        details="Medical grade glucose monitoring device",
        authorization_required=True,
        cost_per_unit=25000,  # $250.00 in cents
        device_type="Diabetes Monitoring"
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


@pytest.fixture
def sample_order(db_session, sample_patient, sample_prescriber, sample_device):
    """
    Create a sample order with relationships.

    Args:
        db_session: Test database session
        sample_patient: Patient fixture
        sample_prescriber: Prescriber fixture
        sample_device: Device fixture

    Returns:
        Order object
    """
    order = Order(
        item_name="Continuous Glucose Monitor",
        order_cost_raw=25000,
        order_cost_to_insurer=20000,
        item_quantity=1,
        reason_prescribed="Diabetes management",
        patient_id=sample_patient.id,
        prescriber_id=sample_prescriber.id
    )
    order.devices.append(sample_device)
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def sample_patient_data():
    """
    Provide sample patient data for testing create operations.

    Returns:
        Dictionary with patient data
    """
    return {
        "medical_record_number": "MRN67890",
        "first_name": "Alice",
        "last_name": "Johnson",
        "age": 32
    }


@pytest.fixture
def sample_prescriber_data():
    """
    Provide sample prescriber data for testing create operations.

    Returns:
        Dictionary with prescriber data
    """
    return {
        "first_name": "Robert",
        "last_name": "Brown",
        "npi": "9876543210",
        "phone_number": "555-9876",
        "email": "robert.brown@example.com",
        "clinic_name": "Health Center",
        "clinic_address": "456 Oak Ave, Town, State 54321"
    }


@pytest.fixture
def sample_device_data():
    """
    Provide sample device data for testing create operations.

    Returns:
        Dictionary with device data
    """
    return {
        "sku": "SKU-67890",
        "name": "Blood Pressure Monitor",
        "details": "Automatic blood pressure monitoring device",
        "authorization_required": False,
        "cost_per_unit": 15000,  # $150.00 in cents
        "device_type": "Cardiovascular Monitoring"
    }


@pytest.fixture
def sample_order_create_data(sample_patient, sample_prescriber):
    """
    Provide sample order creation data using existing patient and prescriber.

    Args:
        sample_patient: Patient fixture
        sample_prescriber: Prescriber fixture

    Returns:
        Dictionary with order creation data
    """
    return {
        "item_name": "Insulin Pump",
        "order_cost_raw": 50000,
        "order_cost_to_insurer": 40000,
        "item_quantity": 1,
        "reason_prescribed": "Type 1 Diabetes",
        "patient_id": sample_patient.id,
        "prescriber_id": sample_prescriber.id,
        "device_ids": []
    }
