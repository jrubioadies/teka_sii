"""Tests for issued invoice XML generation."""

import sys
import os

# Add parent dir to path so 'app' package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.common import (
    ClaveRegimen,
    Contraparte,
    CounterpartyID,
    DetalleIVA,
    IDOtro,
    IDType,
    OperationType,
    PeriodoLiquidacion,
    TipoComunicacion,
    TipoFactura,
    TipoNoExenta,
    Titular,
)
from app.models.issued import (
    DesgloseFacturaBlock,
    IssuedInvoiceDFF,
    IssuedInvoiceRequest,
    NoExentaBlock,
    SujetaBlock,
    TipoDesglose,
)
from app.oracle.dff_mapper import map_oracle_issued_invoice
from app.validators.rules import validate_issued
from app.xml_builder.issued import generate_issued_xml


def _make_domestic_request() -> IssuedInvoiceRequest:
    """Create a sample domestic issued invoice request."""
    return IssuedInvoiceRequest(
        titular=Titular(nombre_razon="TEKA Industrial S.A.", nif="A20025212"),
        tipo_comunicacion=TipoComunicacion.A0,
        periodo=PeriodoLiquidacion(ejercicio="2025", periodo="01"),
        num_serie="FE-2025-001",
        fecha_expedicion="15-01-2025",
        tipo_factura=TipoFactura.F1,
        clave_regimen=ClaveRegimen.R01,
        importe_total="1210.00",
        descripcion_operacion="Venta de electrodomesticos",
        ref_externa="SO-2025-001",
        contraparte=Contraparte(
            nombre_razon="Cliente Nacional S.L.",
            identification=CounterpartyID(nif="B12345678"),
        ),
        tipo_desglose=TipoDesglose(
            desglose_factura=DesgloseFacturaBlock(
                sujeta=SujetaBlock(
                    no_exenta=NoExentaBlock(
                        tipo_no_exenta=TipoNoExenta.S1,
                        detalles_iva=[
                            DetalleIVA(
                                tipo_impositivo="21",
                                base_imponible="1000.00",
                                cuota="210.00",
                            )
                        ],
                    )
                )
            )
        ),
        dff=IssuedInvoiceDFF(),
        operation_type=OperationType.DOMESTIC,
    )


def test_domestic_issued_xml_structure():
    """Test that domestic issued invoice generates valid XML structure."""
    req = _make_domestic_request()
    xml = generate_issued_xml(req)

    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
    assert "<siiLR:SuministroLRFacturasEmitidas>" in xml
    assert "<sii:NombreRazon>TEKA Industrial S.A.</sii:NombreRazon>" in xml
    assert "<sii:NIF>A20025212</sii:NIF>" in xml
    assert "<sii:TipoComunicacion>A0</sii:TipoComunicacion>" in xml
    assert "<sii:Ejercicio>2025</sii:Ejercicio>" in xml
    assert "<sii:Periodo>01</sii:Periodo>" in xml
    assert "<sii:NumSerieFacturaEmisor>FE-2025-001</sii:NumSerieFacturaEmisor>" in xml
    assert "<sii:TipoFactura>F1</sii:TipoFactura>" in xml
    assert "<sii:ClaveRegimenEspecialOTrascendencia>01</sii:ClaveRegimenEspecialOTrascendencia>" in xml
    assert "<sii:ImporteTotal>1210.00</sii:ImporteTotal>" in xml
    assert "<sii:TipoNoExenta>S1</sii:TipoNoExenta>" in xml
    assert "<sii:TipoImpositivo>21</sii:TipoImpositivo>" in xml
    assert "<sii:BaseImponible>1000.00</sii:BaseImponible>" in xml
    assert "<sii:CuotaRepercutida>210.00</sii:CuotaRepercutida>" in xml
    assert "<sii:NIF>B12345678</sii:NIF>" in xml
    assert "</soapenv:Envelope>" in xml


def test_domestic_issued_no_warnings():
    """Domestic F1 with contraparte should have no warnings."""
    req = _make_domestic_request()
    warnings = validate_issued(req)
    assert len(warnings) == 0


def test_f1_without_contraparte_warns():
    """F1 without contraparte should produce a warning."""
    req = _make_domestic_request()
    req.contraparte = None
    warnings = validate_issued(req)
    codes = [w.code for w in warnings]
    assert "SII-E004" in codes


def test_eu_issued_uses_id_otro():
    """EU customer should use IDOtro with IDType 02."""
    req = _make_domestic_request()
    req.operation_type = OperationType.EU
    req.contraparte = Contraparte(
        nombre_razon="Deutsche Firma GmbH",
        identification=CounterpartyID(
            id_otro=IDOtro(
                codigo_pais="DE",
                id_type=IDType.T02,
                id_value="DE123456789",
            )
        ),
    )
    xml = generate_issued_xml(req)
    assert "<sii:CodigoPais>DE</sii:CodigoPais>" in xml
    assert "<sii:IDType>02</sii:IDType>" in xml
    assert "<sii:ID>DE123456789</sii:ID>" in xml


def test_oracle_mapper_domestic():
    """Test Oracle DFF mapper for a domestic issued invoice."""
    oracle_data = {
        "company_name": "TEKA Industrial S.A.",
        "company_nif": "A20025212",
        "invoice_number": "FE-2025-100",
        "invoice_date": "20-03-2025",
        "fiscal_year": "2025",
        "fiscal_period": "03",
        "customer_name": "Distribuciones ABC S.L.",
        "customer_country": "ES",
        "customer_tax_id": "B99887766",
        "tipo_factura": "F1",
        "clave_regimen": "01",
        "importe_total": "2420.00",
        "descripcion": "Venta hornos industriales",
        "vat_lines": [
            {"rate": "21", "base": "2000.00", "cuota": "420.00"},
        ],
    }
    req = map_oracle_issued_invoice(oracle_data)
    assert req.operation_type == OperationType.DOMESTIC
    assert req.contraparte.identification.nif == "B99887766"

    xml = generate_issued_xml(req)
    assert "<sii:NumSerieFacturaEmisor>FE-2025-100</sii:NumSerieFacturaEmisor>" in xml
    assert "<sii:ImporteTotal>2420.00</sii:ImporteTotal>" in xml


def test_oracle_mapper_eu():
    """Test Oracle DFF mapper auto-detects EU operation."""
    oracle_data = {
        "company_name": "TEKA Industrial S.A.",
        "company_nif": "A20025212",
        "invoice_number": "FE-2025-200",
        "invoice_date": "15-02-2025",
        "fiscal_year": "2025",
        "fiscal_period": "02",
        "customer_name": "French Company SARL",
        "customer_country": "FR",
        "customer_tax_id": "FR12345678901",
        "tipo_factura": "F1",
        "clave_regimen": "01",
        "importe_total": "5000.00",
        "descripcion": "Export EU goods",
        "vat_lines": [
            {"rate": "0", "base": "5000.00", "cuota": "0.00"},
        ],
    }
    req = map_oracle_issued_invoice(oracle_data)
    assert req.operation_type == OperationType.EU
    assert req.contraparte.identification.id_otro is not None
    assert req.contraparte.identification.id_otro.id_type == IDType.T02
