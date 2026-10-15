"""Order record model for persistent storage of customer orders."""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class OrderRecord(SQLModel, table=True):
    """Order record model stored in PostgreSQL for persistent order tracking and ledger."""

    __tablename__ = "order_records"

    order_id: str = Field(primary_key=True, index=True)
    platform: str = Field(index=True)
    item_name: str
    quantity: int = Field(default=1)
    delivery_address: str
    subtotal: str
    tax: str
    delivery_fee: str
    total: str
    eta_desc: str
    carrier_name: str
    vehicle: str
    txn_id: str
    is_food: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
