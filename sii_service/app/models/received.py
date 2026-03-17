"""Pydantic models for SII Received Invoices (FacturasRecibidas)."""

from typing import Optional

from pydantic import BaseModel, Field

from .common import (
    ClaveRegimen,
    Contraparte,
    DetalleIVA,
    FacturaRectificada,
    ImporteRectificacion,
    OperationType,
    PeriodoLiquidacion,
    TipoComunicacion,
    TipoFactura,
    TipoRectificativa,
    Titular,
)


class DesgloseIVARecibida(BaseModel):
    """Standard VAT breakdown lines for received invoices."""
    detalles: list[DetalleIVA] = Field(..., min_length=1)


class ISPBlock(BaseModel):
    """InversionSujetoPasivo (reverse charge) lines."""
    detalles: list[DetalleIVA] = Field(..., min_length=1)


class DesgloseFacturaRecibida(BaseModel):
    """VAT breakdown for a received invoice."""
    desglose_iva: DesgloseIVARecibida
    inversion_sujeto_pasivo: Optional[ISPBlock] = None


class ReceivedInvoiceDFF(BaseModel):
    """Oracle DFF fields specific to received invoices."""
    origen_factura: Optional[str] = Field(None, description="DSP/MAN/EDI")
    tipo_rectificativa: Optional[TipoRectificativa] = None
    facturas_rectificadas: Optional[list[FacturaRectificada]] = None
    importe_rectificacion: Optional[ImporteRectificacion] = None
    intra_eu_key: Optional[str] = Field(None, description="09 or 10 for intra-EU")
    intra_eu_subtype: Optional[str] = Field(None, description="bienes or servicios")
    late_submission: bool = Field(default=False)
    simplified_invoice: bool = Field(default=False)
    billing_agreement: Optional[str] = Field(None, max_length=15)
    third_party_invoice: bool = Field(default=False)
    context_value: Optional[str] = Field(None, description="PURCHASE/IMPORT/INTRAEU")


class ReceivedInvoiceRequest(BaseModel):
    """Full request to generate a received invoice (FacturasRecibidas) XML."""
    # Header
    titular: Titular
    tipo_comunicacion: TipoComunicacion = Field(default=TipoComunicacion.A0)
    periodo: PeriodoLiquidacion

    # Invoice identification
    num_serie: str = Field(..., description="Supplier invoice number")
    num_serie_resumen_fin: Optional[str] = Field(None, description="F4 summary last invoice")
    fecha_expedicion: str = Field(..., description="Supplier issue date (dd-mm-yyyy)")

    # Invoice details
    tipo_factura: TipoFactura = Field(default=TipoFactura.F1)
    clave_regimen: ClaveRegimen = Field(default=ClaveRegimen.R01)
    clave_regimen_adicional_1: Optional[ClaveRegimen] = None
    clave_regimen_adicional_2: Optional[ClaveRegimen] = None
    importe_total: str = Field(..., description="Total invoice amount")
    descripcion_operacion: str = Field(..., description="Operation description")
    ref_externa: Optional[str] = None
    cuota_deducible: str = Field(..., description="Deductible VAT amount")
    fecha_reg_contable: str = Field(..., description="Accounting registration date (dd-mm-yyyy)")
    fecha_operacion: Optional[str] = Field(None, description="Transaction date if different")

    # Counterparty (supplier)
    contraparte: Contraparte

    # ISP flag
    inversion_sujeto_pasivo: bool = Field(default=False)

    # VAT breakdown
    desglose: DesgloseFacturaRecibida

    # Oracle DFF fields
    dff: ReceivedInvoiceDFF = Field(default_factory=ReceivedInvoiceDFF)

    # Derived
    operation_type: OperationType = Field(default=OperationType.DOMESTIC)
