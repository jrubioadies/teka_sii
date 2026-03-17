"""FastAPI application for SII XML generation service.

Endpoints:
    POST /api/v1/issued/generate     - Generate FacturasEmitidas XML from structured data
    POST /api/v1/received/generate   - Generate FacturasRecibidas XML from structured data
    POST /api/v1/issued/from-oracle  - Generate FacturasEmitidas XML from Oracle ERP flat data
    POST /api/v1/received/from-oracle - Generate FacturasRecibidas XML from Oracle ERP flat data
    GET  /api/v1/health              - Health check
"""

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.models.common import SIIResponse
from app.models.issued import IssuedInvoiceRequest
from app.models.received import ReceivedInvoiceRequest
from app.oracle.dff_mapper import map_oracle_issued_invoice, map_oracle_received_invoice
from app.validators.rules import validate_issued, validate_received
from app.xml_builder.issued import generate_issued_xml
from app.xml_builder.received import generate_received_xml

app = FastAPI(
    title="TEKA SII XML Generation Service",
    description="Generates AEAT SII SOAP XML envelopes for issued and received invoices, "
                "mapping Oracle ERP Cloud DFF fields to the SII schema.",
    version="1.0.0",
)


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "sii-xml-generator", "sii_version": "1.1"}


# --- Structured data endpoints ---


@app.post("/api/v1/issued/generate", response_model=SIIResponse)
def generate_issued(req: IssuedInvoiceRequest):
    """Generate SuministroLRFacturasEmitidas SOAP XML from structured request."""
    warnings = validate_issued(req)
    xml = generate_issued_xml(req)
    return SIIResponse(
        xml=xml,
        warnings=warnings,
        operation_type=req.operation_type,
        tipo_factura=req.tipo_factura,
    )


@app.post("/api/v1/issued/generate/xml", response_class=PlainTextResponse)
def generate_issued_xml_only(req: IssuedInvoiceRequest):
    """Generate raw XML (no JSON wrapper) for issued invoices."""
    return PlainTextResponse(
        content=generate_issued_xml(req),
        media_type="application/xml",
    )


@app.post("/api/v1/received/generate", response_model=SIIResponse)
def generate_received(req: ReceivedInvoiceRequest):
    """Generate SuministroLRFacturasRecibidas SOAP XML from structured request."""
    warnings = validate_received(req)
    xml = generate_received_xml(req)
    return SIIResponse(
        xml=xml,
        warnings=warnings,
        operation_type=req.operation_type,
        tipo_factura=req.tipo_factura,
    )


@app.post("/api/v1/received/generate/xml", response_class=PlainTextResponse)
def generate_received_xml_only(req: ReceivedInvoiceRequest):
    """Generate raw XML (no JSON wrapper) for received invoices."""
    return PlainTextResponse(
        content=generate_received_xml(req),
        media_type="application/xml",
    )


# --- Oracle ERP flat data endpoints ---


@app.post("/api/v1/issued/from-oracle", response_model=SIIResponse)
def issued_from_oracle(oracle_data: dict):
    """Generate issued invoice XML from Oracle ERP flat data dictionary.

    Accepts the flat field structure from Oracle ERP Cloud DFFs and maps
    it to the SII XML structure automatically.
    """
    req = map_oracle_issued_invoice(oracle_data)
    warnings = validate_issued(req)
    xml = generate_issued_xml(req)
    return SIIResponse(
        xml=xml,
        warnings=warnings,
        operation_type=req.operation_type,
        tipo_factura=req.tipo_factura,
    )


@app.post("/api/v1/received/from-oracle", response_model=SIIResponse)
def received_from_oracle(oracle_data: dict):
    """Generate received invoice XML from Oracle ERP flat data dictionary.

    Accepts the flat field structure from Oracle ERP Cloud DFFs and maps
    it to the SII XML structure automatically.
    """
    req = map_oracle_received_invoice(oracle_data)
    warnings = validate_received(req)
    xml = generate_received_xml(req)
    return SIIResponse(
        xml=xml,
        warnings=warnings,
        operation_type=req.operation_type,
        tipo_factura=req.tipo_factura,
    )
