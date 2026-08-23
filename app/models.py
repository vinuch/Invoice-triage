"""
Data models for invoice extraction.
This is the contract every part of the pipeline agrees on.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float
    total: float


class VendorInfo(BaseModel):
    name: str
    address: Optional[str] = None
    tax_id: Optional[str] = None
    confidence: float = Field(ge=0, le=1)


class InvoiceDetails(BaseModel):
    number: str
    date: Optional[str] = None
    due_date: Optional[str] = None
    terms: Optional[str] = None
    po_number: Optional[str] = None
    confidence: float = Field(ge=0, le=1)


class Financials(BaseModel):
    currency: str = "USD"
    subtotal: float
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    total: float
    confidence: float = Field(ge=0, le=1)


class Flag(BaseModel):
    type: str
    severity: str  # "low" | "medium" | "high"
    message: str


class Extraction(BaseModel):
    document_id: str
    vendor: VendorInfo
    invoice: InvoiceDetails
    financials: Financials
    line_items: list[LineItem] = []
    category: Optional[str] = None
    overall_confidence: float = Field(ge=0, le=1)


class TriageResult(BaseModel):
    extraction: Extraction
    flags: list[Flag] = []
    status: str  # "approved" | "flagged" | "needs_review" | "error"
    summary: str
