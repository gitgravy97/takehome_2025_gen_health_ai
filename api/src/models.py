from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, Table
from sqlalchemy.orm import relationship

from src.database import Base


# Association table for Order-Device many-to-many relationship
order_devices = Table(
    'order_devices',
    Base.metadata,
    Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
    Column('device_id', Integer, ForeignKey('devices.id'), primary_key=True),
    Column('quantity', Integer, default=1)  # Quantity of this device in the order
)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(255))
    order_cost_raw = Column(Integer)  # Cost in cents
    # todo :: is order_cost_to_patient worth including?
    order_cost_to_insurer = Column(Integer)  # Cost in cents
    item_quantity = Column(Integer)
    reason_prescribed = Column(Text)

    # TODO Add "order_date" field

    # Foreign keys for many-to-one relationships
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    prescriber_id = Column(Integer, ForeignKey('prescribers.id'), nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="orders")
    prescriber = relationship("Prescriber", back_populates="orders")
    devices = relationship("Device", secondary=order_devices, back_populates="orders")


#### TODO make this be birthdate
class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    medical_record_number = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    age = Column(Integer)

    # Relationship - one patient can have many orders
    orders = relationship("Order", back_populates="patient")


class Prescriber(Base):
    __tablename__ = "prescribers"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    # National Provider Index, official doctor identifier
    npi = Column(String(10), unique=True, index=True)
    phone_number = Column(String(20))
    email = Column(String(255))
    clinic_name = Column(String(255))
    clinic_address = Column(Text)

    # Relationship - one prescriber can have many orders
    orders = relationship("Order", back_populates="prescriber")


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, index=True)
    name = Column(String(255), nullable=False)
    details = Column(Text)
    authorization_required = Column(Boolean, default=False)
    cost_per_unit = Column(Integer)  # Cost in cents
    device_type = Column(String(100))  # TODO: Consider using enum

    # Relationship
    orders = relationship("Order", secondary=order_devices, back_populates="devices")


# TODO :: Order Status
# TODO :: Prescribed For Details?