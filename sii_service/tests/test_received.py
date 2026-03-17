"""Tests for received invoice XML generation."""

import sys
import os

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
    Titular,
)
from app.models.received import (
    DesgloseFacturaRecibida,
    DesgloseIVARecibida,
    ISPBlock,
    ReceivedInvoiceDFF,
    ReceivedInvoiceRequest,
)
from app.oracle.dff_mapper import map_oracle_received_invoice
from app.validators.rules import validate_received
from app.xml_builder.received import generate_received_xml


def _make_domestic_received() -> ReceivedInvoiceRequest:
    """Create a sample domestic received invoice request."""
    return ReceivedInvoiceRequest(
        titular=Titular(nombre_razon="TEKA Industrial S.A.", nif="A20025212"),
        tipo_comunicacion=TipoComunicacion.A0,
        periodo=PeriodoLiquidacion(ejercicio="2025", periodo="01"),
        num_serie="INV-2025-001",
        fecha_expedicion="15-01-2025",
        tipo_factura=TipoFactura.F1,
        clave_regimen=ClaveRegimen.R01,
        importe_total="1210.00",
        descripcion_operacion="Compra de servicios informaticos",
        cuota_deducible="210.00",
        fecha_reg_contable="20-01-2025",
        contraparte=Contraparte(
            nombre_razon="Proveedor Nacional S.L.",
            identification=CounterpartyID(nif="A14635387"),
        ),
        desglose=DesgloseFacturaRecibida(
            desglose_iva=DesgloseIVARecibida(
                detalles=[
                    DetalleIVA(
                        tipo_impositivo="21",
                        base_imponible="1000.00",
                        cuota="210.00",
                    )
                ]
            )
        ),
        dff=ReceivedInvoiceDFF(),
        operation_type=OperationType.DOMESTIC,
    )


def test_domestic_received_xml_structure():
    """Test that domestic received invoice generates valid XML structure."""
    req = _make_domestic_received()
    xml = generate_received_xml(req)

    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
    assert "<siiLR:SuministroLRFacturasRecibidas>" in xml
    assert "<sii:NombreRazon>TEKA Industrial S.A.</sii:NombreRazon>" in xml
    assert "<sii:NIF>A20025212</sii:NIF>" in xml
    assert "<sii:TipoComunicacion>A0</sii:TipoComunicacion>" in xml
    assert "<sii:NumSerieFacturaEmisor>INV-2025-001</sii:NumSerieFacturaEmisor>" in xml
    assert "<sii:TipoFactura>F1</sii:TipoFactura>" in xml
    assert "<sii:CuotaSoportada>210.00</sii:CuotaSoportada>" in xml
    assert "<sii:CuotaDeducible>210.00</sii:CuotaDeducible>" in xml
    assert "<sii:FechaRegContable>20-01-2025</sii:FechaRegContable>" in xml
    assert "<sii:NIF>A14635387</sii:NIF>" in xml
    assert "</soapenv:Envelope>" in xml


def test_domestic_received_no_warnings():
    req = _make_domestic_received()
    warnings = validate_received(req)
    assert len(warnings) == 0


def test_received_with_isp():
    """Test received invoice with InversionSujetoPasivo (reverse charge)."""
    req = _make_domestic_received()
    req.inversion_sujeto_pasivo = True
    req.desglose.inversion_sujeto_pasivo = ISPBlock(
        detalles=[
            DetalleIVA(
                tipo_impositivo="21",
                base_imponible="500.00",
                cuota="105.00",
                bien_inversion="N",
            )
        ]
    )
    xml = generate_received_xml(req)
    assert "<sii:InversionSujetoPasivo>" in xml
    assert "<sii:CuotaSoportada>105.00</sii:CuotaSoportada>" in xml


def test_received_eu_supplier():
    """Test received invoice from EU supplier uses IDOtro."""
    req = _make_domestic_received()
    req.operation_type = OperationType.EU
    req.contraparte = Contraparte(
        nombre_razon="Italiana SpA",
        identification=CounterpartyID(
            id_otro=IDOtro(
                codigo_pais="IT",
                id_type=IDType.T02,
                id_value="IT01234567890",
            )
        ),
    )
    xml = generate_received_xml(req)
    assert "<sii:CodigoPais>IT</sii:CodigoPais>" in xml
    assert "<sii:IDType>02</sii:IDType>" in xml
    assert "<sii:ID>IT01234567890</sii:ID>" in xml


def test_isp_flag_without_lines_warns():
    """ISP flag set but no ISP lines should produce a warning."""
    req = _make_domestic_received()
    req.inversion_sujeto_pasivo = True
    warnings = validate_received(req)
    codes = [w.code for w in warnings]
    assert "SII-E008" in codes


def test_oracle_mapper_domestic_received():
    """Test Oracle DFF mapper for a domestic received invoice."""
    oracle_data = {
        "company_name": "TEKA Industrial S.A.",
        "company_nif": "A20025212",
        "invoice_number": "PROV-2025-050",
        "invoice_date": "10-03-2025",
        "fecha_reg_contable": "12-03-2025",
        "fiscal_year": "2025",
        "fiscal_period": "03",
        "supplier_name": "Suministros Madrid S.L.",
        "supplier_country": "ES",
        "supplier_tax_id": "B11223344",
        "tipo_factura": "F1",
        "clave_regimen": "01",
        "importe_total": "3630.00",
        "descripcion": "Compra materiales",
        "cuota_deducible": "630.00",
        "vat_lines": [
            {"rate": "21", "base": "3000.00", "cuota": "630.00"},
        ],
    }
    req = map_oracle_received_invoice(oracle_data)
    assert req.operation_type == OperationType.DOMESTIC
    assert req.contraparte.identification.nif == "B11223344"

    xml = generate_received_xml(req)
    assert "<sii:NumSerieFacturaEmisor>PROV-2025-050</sii:NumSerieFacturaEmisor>" in xml
    assert "<sii:CuotaDeducible>630.00</sii:CuotaDeducible>" in xml


def test_oracle_mapper_import_dua():
    """Test Oracle DFF mapper for import DUA (F5)."""
    oracle_data = {
        "company_name": "TEKA Industrial S.A.",
        "company_nif": "A20025212",
        "invoice_number": "DUA-2025-001",
        "invoice_date": "05-02-2025",
        "fecha_reg_contable": "08-02-2025",
        "fiscal_year": "2025",
        "fiscal_period": "02",
        "supplier_name": "China Exports Co.",
        "supplier_country": "CN",
        "supplier_tax_id": "CN9988776655",
        "tipo_factura": "F5",
        "clave_regimen": "01",
        "importe_total": "15000.00",
        "descripcion": "Import DUA components",
        "cuota_deducible": "3150.00",
        "vat_lines": [
            {"rate": "21", "base": "15000.00", "cuota": "3150.00"},
        ],
    }
    req = map_oracle_received_invoice(oracle_data)
    assert req.operation_type == OperationType.IMPORT
    assert req.contraparte.identification.id_otro is not None
    assert req.contraparte.identification.id_otro.codigo_pais == "CN"
