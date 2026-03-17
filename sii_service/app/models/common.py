"""Common Pydantic models shared between issued and received invoices."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TipoComunicacion(str, Enum):
    A0 = "A0"  # New registration
    A1 = "A1"  # Amendment


class TipoFactura(str, Enum):
    F1 = "F1"  # Complete invoice
    F2 = "F2"  # Simplified invoice
    F3 = "F3"  # Issued in place of simplified
    F4 = "F4"  # Summary entry
    F5 = "F5"  # Import (DUA)
    F6 = "F6"  # Other accounting document
    R1 = "R1"  # Rectification (art. 80.1,2,6)
    R2 = "R2"  # Rectification (art. 80.3)
    R3 = "R3"  # Rectification (art. 80.4)
    R4 = "R4"  # Other rectification
    R5 = "R5"  # Rectification simplified
    LC = "LC"  # Customs clearance


class ClaveRegimen(str, Enum):
    R01 = "01"  # General regime
    R02 = "02"  # Export
    R03 = "03"  # Special used/art/antiques
    R04 = "04"  # Golden investment
    R05 = "05"  # Travel agencies
    R06 = "06"  # VAT group (advanced)
    R07 = "07"  # Cash basis (RECC)
    R08 = "08"  # IGIC - Canary Islands
    R09 = "09"  # Travel/insurance
    R12 = "12"  # Business premises lease
    R13 = "13"  # Other lease
    R14 = "14"  # Recipient = taxpayer (public body)
    R15 = "15"  # Export (DF art.21)


class TipoRectificativa(str, Enum):
    S = "S"  # Replacement (Sustitucion)
    I = "I"  # Difference (Diferencias)


class IDType(str, Enum):
    T02 = "02"  # NIF-IVA (EU VAT no.)
    T03 = "03"  # Passport
    T04 = "04"  # Tax ID (other country)
    T05 = "05"  # Census certificate
    T06 = "06"  # Other
    T07 = "07"  # Not registered (AEAT)


class OperationType(str, Enum):
    DOMESTIC = "domestic"
    EU = "eu"
    EXPORT = "export"
    IMPORT = "import"
    ROW = "row"  # Rest of world / third country


class CausaExencion(str, Enum):
    E1 = "E1"  # Art. 20 LIVA (internal exempt)
    E2 = "E2"  # Art. 21 LIVA (export)
    E3 = "E3"  # Art. 22 LIVA (intra-EU delivery)
    E4 = "E4"  # Arts. 23-24 LIVA (diplomatic / org.)
    E5 = "E5"  # Art. 25 LIVA (territories)
    E6 = "E6"  # Other exempt (IGIC/IPSI/others)


class TipoNoExenta(str, Enum):
    S1 = "S1"  # Sujeta y no exenta (standard VAT)
    S2 = "S2"  # Sujeta y no exenta - ISP (reverse charge)
    S3 = "S3"  # S1 + S2 combined


class CausaNoSujeta(str, Enum):
    OT = "OT"  # Other (art. 7 LIVA / non-business)
    RL = "RL"  # Location rules (no subject in TAT)


# --- Shared sub-models ---


class Titular(BaseModel):
    """Submitter / company filing the SII report."""
    nombre_razon: str = Field(..., description="Company name (NombreRazon)")
    nif: str = Field(..., pattern=r"^[A-Z0-9]{8,9}$", description="Spanish NIF")


class IDOtro(BaseModel):
    """Non-domestic tax identification block."""
    codigo_pais: str = Field(..., min_length=2, max_length=2, description="ISO country code")
    id_type: IDType = Field(..., description="AEAT ID type code")
    id_value: str = Field(..., description="Tax ID / VAT number")


class CounterpartyID(BaseModel):
    """Identification for the counterparty (supplier or customer)."""
    nif: Optional[str] = Field(None, description="NIF (domestic ES suppliers/customers)")
    id_otro: Optional[IDOtro] = Field(None, description="IDOtro block (non-domestic)")


class Contraparte(BaseModel):
    """Counterparty (supplier or customer)."""
    nombre_razon: str = Field(..., description="Legal name")
    identification: CounterpartyID


class PeriodoLiquidacion(BaseModel):
    """Tax reporting period."""
    ejercicio: str = Field(..., pattern=r"^\d{4}$", description="Fiscal year (YYYY)")
    periodo: str = Field(
        ...,
        pattern=r"^(0[1-9]|1[0-2])$",
        description="Period (01-12)",
    )


class DetalleIVA(BaseModel):
    """Single VAT breakdown line."""
    tipo_impositivo: str = Field(..., description="VAT rate %")
    base_imponible: str = Field(..., description="Tax base amount")
    cuota: str = Field(..., description="VAT amount (repercutida or soportada)")
    tipo_recargo_equivalencia: Optional[str] = Field(None, description="Surcharge rate %")
    cuota_recargo_equivalencia: Optional[str] = Field(None, description="Surcharge amount")
    bien_inversion: Optional[str] = Field(None, description="Investment good (S/N)")


class FacturaRectificada(BaseModel):
    """Reference to the original invoice being rectified."""
    num_serie: str = Field(..., description="Original invoice number")
    fecha_expedicion: str = Field(..., description="Original invoice date (dd-mm-yyyy)")


class ImporteRectificacion(BaseModel):
    """Amounts for S-type (replacement) rectifications."""
    base_rectificada: str = Field(default="0.00")
    cuota_rectificada: str = Field(default="0.00")
    cuota_recargo_rectificado: str = Field(default="0.00")


class DetalleExenta(BaseModel):
    """Exempt VAT detail line."""
    causa_exencion: CausaExencion
    base_imponible: str = Field(..., description="Exempt base amount")


class DetalleNoSujeta(BaseModel):
    """Not-subject-to-VAT detail line."""
    causa: CausaNoSujeta = Field(default=CausaNoSujeta.OT)
    importe: str = Field(..., description="Amount")


class ValidationWarning(BaseModel):
    """A validation warning (non-blocking)."""
    code: str
    message: str


class SIIResponse(BaseModel):
    """Response from the XML generation endpoint."""
    xml: str
    warnings: list[ValidationWarning] = []
    operation_type: OperationType
    tipo_factura: TipoFactura
