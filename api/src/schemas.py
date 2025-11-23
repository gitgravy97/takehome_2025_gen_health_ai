from __future__ import annotations
from typing import List, Optional, Union
from pydantic import BaseModel, EmailStr, Field, model_validator


# ============= Patient Schemas =============
class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=150)

class PatientCreate(PatientBase):
    medical_record_number: str = Field(..., min_length=1, max_length=50, description="Unique medical record number")

class PatientRead(PatientBase):
    id: int
    medical_record_number: str

    class Config:
        from_attributes = True

# ============= Prescriber Schemas =============
class PrescriberBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    ## Todo Swap to int?
    npi: Optional[str] = Field(None, min_length=10, max_length=10, pattern=r'^\d{10}$')
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = Field(None, max_length=255)
    clinic_name: Optional[str] = Field(None, max_length=255)
    clinic_address: Optional[str] = None

class PrescriberCreate(PrescriberBase):
    pass

class PrescriberRead(PrescriberBase):
    id: int

    class Config:
        from_attributes = True

# ============= Device Schemas =============
class DeviceBase(BaseModel):
    sku: Optional[str] = Field(None, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    details: Optional[str] = None
    authorization_required: bool = False
    cost_per_unit: Optional[int] = Field(None, ge=0, description="Cost in cents")
    device_type: Optional[str] = Field(None, max_length=100)

class DeviceCreate(DeviceBase):
    pass

class DeviceRead(DeviceBase):
    id: int

    class Config:
        from_attributes = True

# ============= Order Schemas =============
class OrderBase(BaseModel):
    item_name: Optional[str] = Field(None, max_length=255)
    order_cost_raw: Optional[int] = Field(None, ge=0, description="Cost in cents")
    order_cost_to_insurer: Optional[int] = Field(None, ge=0, description="Cost in cents")
    item_quantity: Optional[int] = Field(None, ge=1)
    reason_prescribed: Optional[str] = None

class OrderCreate(OrderBase):
    # Accept either patient_id OR patient object (for lookup/create)
    patient_id: Optional[int] = Field(None, description="ID of existing patient")
    patient: Optional[PatientCreate] = Field(None, description="Patient data for lookup/create by MRN")

    # Accept either prescriber_id OR prescriber object (for lookup/create)
    prescriber_id: Optional[int] = Field(None, description="ID of existing prescriber")
    prescriber: Optional[PrescriberCreate] = Field(None, description="Prescriber data for lookup/create by NPI")

    # Accept either device_ids OR devices objects (for lookup/create)
    device_ids: Optional[List[int]] = Field(default=[], description="List of device IDs for this order")
    devices: Optional[List[DeviceCreate]] = Field(default=[], description="Device data for lookup/create by SKU")

    @model_validator(mode='after')
    def validate_patient_and_prescriber(self):
        # Must provide either patient_id or patient object (but not both)
        if not self.patient_id and not self.patient:
            raise ValueError("Must provide either patient_id or patient data")
        if self.patient_id and self.patient:
            raise ValueError("Cannot provide both patient_id and patient data")

        # Must provide either prescriber_id or prescriber object (but not both)
        if not self.prescriber_id and not self.prescriber:
            raise ValueError("Must provide either prescriber_id or prescriber data")
        if self.prescriber_id and self.prescriber:
            raise ValueError("Cannot provide both prescriber_id and prescriber data")

        return self

class OrderRead(OrderBase):
    id: int
    patient_id: int
    prescriber_id: int
    patient: PatientRead
    prescriber: PrescriberRead
    devices: List[DeviceRead] = []

    class Config:
        from_attributes = True


# ============= Order-Device Association Schema =============
class OrderDeviceAssociation(BaseModel):
    """Schema for the many-to-many relationship between orders and devices"""
    order_id: int
    device_id: int
    quantity: int = Field(default=1, ge=1)

    class Config:
        from_attributes = True

# ============= Extended Schemas with Relationships =============
class PatientWithOrders(PatientRead):
    """Patient schema including all their orders"""
    orders: List[OrderRead] = []

    class Config:
        from_attributes = True


class PrescriberWithOrders(PrescriberRead):
    """Prescriber schema including all their orders"""
    orders: List[OrderRead] = []

    class Config:
        from_attributes = True

class DeviceWithOrders(DeviceRead):
    """Device schema including all orders it appears in"""
    orders: List[OrderRead] = []

    class Config:
        from_attributes = True


# ============= Duplicate Detection Schemas =============
class DuplicateWarning(BaseModel):
    """Warning about a potential duplicate order"""
    order_id: int
    item_name: Optional[str] = None
    item_quantity: Optional[int] = None
    reason_prescribed: Optional[str] = None
    similarity_score: int
    reasons: List[str]


class OrderCreateResponse(BaseModel):
    """Response for order creation including duplicate warnings"""
    order: OrderRead
    duplicate_warnings: List[DuplicateWarning] = []
    has_duplicates: bool = False


# ============= PDF Parsing Schemas =============
class ParsedDeviceInfo(BaseModel):
    """Device information extracted from PDF"""
    name: Optional[str] = None
    sku: Optional[str] = None
    quantity: Optional[int] = 1


class ParsedOrderData(BaseModel):
    """Complete order data extracted from PDF"""
    # Patient info
    patient: Optional[PatientCreate] = None

    # Prescriber info
    prescriber: Optional[PrescriberCreate] = None

    # Device info
    devices: List[ParsedDeviceInfo] = []

    # Order details
    item_name: Optional[str] = None
    order_cost_raw: Optional[int] = None
    order_cost_to_insurer: Optional[int] = None
    item_quantity: Optional[int] = None
    reason_prescribed: Optional[str] = None

    # Metadata
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score of the extraction (0-1)")
    extraction_notes: Optional[str] = Field(None, description="Any notes or warnings from the extraction process")