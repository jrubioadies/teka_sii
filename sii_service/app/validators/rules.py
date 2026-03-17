"""Business validation rules for SII invoices (AEAT validation codes)."""

from app.models.common import ValidationWarning
from app.models.issued import IssuedInvoiceRequest
from app.models.received import ReceivedInvoiceRequest


RECTIFICATION_TYPES = {"R1", "R2", "R3", "R4", "R5"}


def validate_issued(req: IssuedInvoiceRequest) -> list[ValidationWarning]:
    """Validate an issued invoice request and return warnings."""
    warns: list[ValidationWarning] = []
    tipo = req.tipo_factura.value
    dff = req.dff

    # Rectification consistency
    is_rectif = tipo in RECTIFICATION_TYPES
    if is_rectif and not dff.tipo_rectificativa:
        warns.append(ValidationWarning(
            code="SII-E001",
            message=f"TipoFactura {tipo} is a rectification but TipoRectificativa is not set in DFF.",
        ))
    if not is_rectif and dff.tipo_rectificativa:
        warns.append(ValidationWarning(
            code="SII-E002",
            message="TipoRectificativa is set but TipoFactura is not a rectification type.",
        ))

    # F4 summary requires end invoice number
    if tipo == "F4" and not req.num_serie_resumen_fin:
        warns.append(ValidationWarning(
            code="SII-E003",
            message="TipoFactura F4 (summary) requires NumSerieFacturaEmisorResumenFin.",
        ))

    # F1 without contraparte
    if tipo == "F1" and not req.contraparte:
        warns.append(ValidationWarning(
            code="SII-E004",
            message="F1 invoice without Contraparte - AEAT may reject. Contraparte is mandatory for F1.",
        ))

    # Clave 06 + F2 not allowed (validation 1338)
    if req.clave_regimen.value == "06" and tipo == "F2":
        warns.append(ValidationWarning(
            code="SII-V1338",
            message="Clave 06 (VAT group) does not allow TipoFactura F2.",
        ))

    # Clave 07 (RECC) + NoSujeta typically not allowed
    td = req.tipo_desglose
    if req.clave_regimen.value == "07" and td.desglose_factura and td.desglose_factura.no_sujeta:
        warns.append(ValidationWarning(
            code="SII-E005",
            message="RECC (Clave 07): NoSujeta block is typically not allowed.",
        ))

    # TipoDesglose: at least one must be provided
    if not td.desglose_factura and not td.desglose_tipo_operacion:
        warns.append(ValidationWarning(
            code="SII-E006",
            message="TipoDesglose must contain either DesgloseFactura or DesgloseTipoOperacion.",
        ))

    return warns


def validate_received(req: ReceivedInvoiceRequest) -> list[ValidationWarning]:
    """Validate a received invoice request and return warnings."""
    warns: list[ValidationWarning] = []
    tipo = req.tipo_factura.value
    dff = req.dff

    # Rectification consistency
    is_rectif = tipo in RECTIFICATION_TYPES
    if is_rectif and not dff.tipo_rectificativa:
        warns.append(ValidationWarning(
            code="SII-E001",
            message=f"TipoFactura {tipo} is a rectification but TipoRectificativa is not set in DFF.",
        ))
    if not is_rectif and dff.tipo_rectificativa:
        warns.append(ValidationWarning(
            code="SII-E002",
            message="TipoRectificativa is set but TipoFactura is not a rectification type.",
        ))

    # F4 summary requires end invoice number
    if tipo == "F4" and not req.num_serie_resumen_fin:
        warns.append(ValidationWarning(
            code="SII-E003",
            message="TipoFactura F4 (summary) requires NumSerieFacturaEmisorResumenFin.",
        ))

    # Counterparty must have identification
    cid = req.contraparte.identification
    if not cid.nif and not cid.id_otro:
        warns.append(ValidationWarning(
            code="SII-E007",
            message="Contraparte must have either NIF or IDOtro identification.",
        ))

    # F5 (DUA import) should have operation_type import
    if tipo == "F5" and req.operation_type.value != "import":
        warns.append(ValidationWarning(
            code="SII-W001",
            message="TipoFactura F5 (DUA) is typically used with operation_type 'import'.",
        ))

    # ISP flag consistency with ISP lines
    if req.inversion_sujeto_pasivo and not req.desglose.inversion_sujeto_pasivo:
        warns.append(ValidationWarning(
            code="SII-E008",
            message="InversionSujetoPasivo is Y but no ISP VAT lines provided in desglose.",
        ))

    return warns
