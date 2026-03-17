"""Pydantic models for SII Issued Invoices (FacturasEmitidas)."""

from typing import Optional

from pydantic import BaseModel, Field

from .common import (
    ClaveRegimen,
    Contraparte,
    DetalleExenta,
    DetalleIVA,
    DetalleNoSujeta,
    FacturaRectificada,
    ImporteRectificacion,
    OperationType,
    PeriodoLiquidacion,
    TipoComunicacion,
    TipoFactura,
    TipoNoExenta,
    TipoRectificativa,
    Titular,
)


class NoExentaBlock(BaseModel):
    """Sujeta -> NoExenta block with VAT lines."""
    tipo_no_exenta: TipoNoExenta = Field(default=TipoNoExenta.S1)
    detalles_iva: list[DetalleIVA] = Field(..., min_length=1)


class ExentaBlock(BaseModel):
    """Sujeta -> Exenta block with exempt lines."""
    detalles: list[DetalleExenta] = Field(..., min_length=1)


class SujetaBlock(BaseModel):
    """DesgloseFactura -> Sujeta block."""
    no_exenta: Optional[NoExentaBlock] = None
    exenta: Optional[ExentaBlock] = None


class NoSujetaBlock(BaseModel):
    """DesgloseFactura -> NoSujeta block."""
    detalles: list[DetalleNoSujeta] = Field(..., min_length=1)


class DesgloseFacturaBlock(BaseModel):
    """Standard VAT breakdown (domestic/EU)."""
    sujeta: SujetaBlock
    no_sujeta: Optional[NoSujetaBlock] = None


class TipoOperacionBlock(BaseModel):
    """DesgloseTipoOperacion block (exports/intra-EU services)."""
    tipo_operacion: str = Field(
        default="entrega",
        description="'entrega' (goods) or 'servicio' (services)",
    )
    sujeta: SujetaBlock
    exenta_tipoop: Optional[ExentaBlock] = None


class TipoDesglose(BaseModel):
    """Top-level VAT breakdown: either DesgloseFactura or DesgloseTipoOperacion."""
    desglose_factura: Optional[DesgloseFacturaBlock] = None
    desglose_tipo_operacion: Optional[TipoOperacionBlock] = None


class IssuedInvoiceDFF(BaseModel):
    """Oracle DFF fields specific to issued invoices."""
    origen_factura: Optional[str] = Field(None, description="DSP/MAN/EDI")
    tipo_rectificativa: Optional[TipoRectificativa] = None
    facturas_rectificadas: Optional[list[FacturaRectificada]] = None
    importe_rectificacion: Optional[ImporteRectificacion] = None
    simplified_invoice: bool = Field(default=False, description="Art. 7.2/7.3")
    sin_identif_destinatario: bool = Field(default=False, description="Art. 6.1.d")
    macrodato: bool = Field(default=False, description=">100M operation")
    emitida_por_terceros: Optional[str] = Field(None, description="T or D")
    billing_agreement: Optional[str] = Field(None, max_length=15)
    recc: bool = Field(default=False, description="Cash basis (Clave 07)")


class IssuedInvoiceRequest(BaseModel):
    """Full request to generate an issued invoice (FacturasEmitidas) XML."""
    # Header
    titular: Titular
    tipo_comunicacion: TipoComunicacion = Field(default=TipoComunicacion.A0)
    periodo: PeriodoLiquidacion

    # Invoice identification
    num_serie: str = Field(..., description="Invoice number (NumSerieFacturaEmisor)")
    num_serie_resumen_fin: Optional[str] = Field(None, description="Last invoice of F4 summary")
    fecha_expedicion: str = Field(..., description="Issue date (dd-mm-yyyy)")

    # Invoice details
    tipo_factura: TipoFactura = Field(default=TipoFactura.F1)
    clave_regimen: ClaveRegimen = Field(default=ClaveRegimen.R01)
    clave_regimen_adicional_1: Optional[ClaveRegimen] = None
    clave_regimen_adicional_2: Optional[ClaveRegimen] = None
    importe_total: str = Field(..., description="Total invoice amount")
    descripcion_operacion: str = Field(..., description="Operation description")
    ref_externa: Optional[str] = Field(None, description="ERP internal reference")
    fecha_operacion: Optional[str] = Field(None, description="Transaction date if different")

    # Counterparty (customer)
    contraparte: Optional[Contraparte] = None
    entidad_sucedida_nif: Optional[str] = None

    # VAT breakdown
    tipo_desglose: TipoDesglose

    # Oracle DFF fields
    dff: IssuedInvoiceDFF = Field(default_factory=IssuedInvoiceDFF)

    # Derived
    operation_type: OperationType = Field(default=OperationType.DOMESTIC)
