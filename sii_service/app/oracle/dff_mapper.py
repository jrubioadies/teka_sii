"""Maps Oracle ERP Cloud DFF (Descriptive Flexfield) data to SII request models.

This module transforms the flat Oracle ERP DFF field structure into the
hierarchical Pydantic models expected by the XML generators. It handles:

- Supplier/customer master data -> Contraparte identification
- DFF context values -> Operation type detection
- Invoice header DFFs -> TipoFactura, ClaveRegimen, rectification details
- Line-level tax data -> VAT breakdown structures
"""

from app.models.common import (
    ClaveRegimen,
    Contraparte,
    CounterpartyID,
    DetalleIVA,
    FacturaRectificada,
    IDOtro,
    IDType,
    ImporteRectificacion,
    OperationType,
    PeriodoLiquidacion,
    TipoComunicacion,
    TipoFactura,
    TipoNoExenta,
    TipoRectificativa,
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
from app.models.received import (
    DesgloseFacturaRecibida,
    DesgloseIVARecibida,
    ISPBlock,
    ReceivedInvoiceDFF,
    ReceivedInvoiceRequest,
)


# EU country codes for auto-detection
EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "SE",
}


def detect_operation_type(country_code: str, tipo_factura: str = "F1") -> OperationType:
    """Detect operation type from the counterparty's country code."""
    if country_code == "ES":
        return OperationType.DOMESTIC
    if tipo_factura == "F5":
        return OperationType.IMPORT
    if country_code in EU_COUNTRIES:
        return OperationType.EU
    return OperationType.ROW


def build_counterparty_id(
    country_code: str,
    tax_id: str,
    operation_type: OperationType,
    id_type_override: str | None = None,
) -> CounterpartyID:
    """Build the appropriate CounterpartyID based on operation type."""
    if operation_type == OperationType.DOMESTIC:
        return CounterpartyID(nif=tax_id)

    # Non-domestic: use IDOtro
    if id_type_override:
        id_type = IDType(id_type_override)
    elif operation_type == OperationType.EU:
        id_type = IDType.T02  # NIF-IVA
    else:
        id_type = IDType.T04  # Foreign tax ID

    return CounterpartyID(
        id_otro=IDOtro(
            codigo_pais=country_code,
            id_type=id_type,
            id_value=tax_id,
        )
    )


def map_oracle_issued_invoice(oracle_data: dict) -> IssuedInvoiceRequest:
    """Map Oracle ERP flat data dictionary to an IssuedInvoiceRequest.

    Expected oracle_data keys:
        # Company / submitter
        company_name, company_nif,
        # Invoice header
        invoice_number, invoice_date, fiscal_year, fiscal_period,
        tipo_comunicacion (A0/A1),
        # Customer
        customer_name, customer_country, customer_tax_id, customer_id_type,
        # Invoice details
        tipo_factura, clave_regimen, importe_total, descripcion,
        ref_externa, fecha_operacion,
        # DFF fields
        dff_origen_factura, dff_tipo_rectificativa,
        dff_rect_num, dff_rect_date,
        dff_base_rectificada, dff_cuota_rectificada, dff_recargo_rectificado,
        dff_simplified, dff_sin_identif, dff_macrodato,
        dff_emitida_terceros, dff_billing_agreement, dff_recc,
        # VAT lines (list of dicts)
        vat_lines: [{rate, base, cuota, recargo_rate, recargo_cuota}]
    """
    d = oracle_data

    tipo_factura = d.get("tipo_factura", "F1")
    customer_country = d.get("customer_country", "ES")
    op_type = detect_operation_type(customer_country, tipo_factura)

    # Counterparty
    contraparte = None
    if d.get("customer_name"):
        cid = build_counterparty_id(
            customer_country,
            d.get("customer_tax_id", ""),
            op_type,
            d.get("customer_id_type"),
        )
        contraparte = Contraparte(
            nombre_razon=d["customer_name"],
            identification=cid,
        )

    # DFF
    rectif_type = d.get("dff_tipo_rectificativa")
    facturas_rect = None
    if d.get("dff_rect_num"):
        facturas_rect = [FacturaRectificada(
            num_serie=d["dff_rect_num"],
            fecha_expedicion=d.get("dff_rect_date", ""),
        )]

    importe_rect = None
    if rectif_type == "S":
        importe_rect = ImporteRectificacion(
            base_rectificada=d.get("dff_base_rectificada", "0.00"),
            cuota_rectificada=d.get("dff_cuota_rectificada", "0.00"),
            cuota_recargo_rectificado=d.get("dff_recargo_rectificado", "0.00"),
        )

    dff = IssuedInvoiceDFF(
        origen_factura=d.get("dff_origen_factura"),
        tipo_rectificativa=TipoRectificativa(rectif_type) if rectif_type else None,
        facturas_rectificadas=facturas_rect,
        importe_rectificacion=importe_rect,
        simplified_invoice=d.get("dff_simplified", False),
        sin_identif_destinatario=d.get("dff_sin_identif", False),
        macrodato=d.get("dff_macrodato", False),
        emitida_por_terceros=d.get("dff_emitida_terceros"),
        billing_agreement=d.get("dff_billing_agreement"),
        recc=d.get("dff_recc", False),
    )

    # VAT lines -> TipoDesglose
    vat_lines_data = d.get("vat_lines", [])
    detalles = [
        DetalleIVA(
            tipo_impositivo=str(vl["rate"]),
            base_imponible=str(vl["base"]),
            cuota=str(vl["cuota"]),
            tipo_recargo_equivalencia=str(vl["recargo_rate"]) if vl.get("recargo_rate") else None,
            cuota_recargo_equivalencia=str(vl["recargo_cuota"]) if vl.get("recargo_cuota") else None,
        )
        for vl in vat_lines_data
    ]

    if not detalles:
        detalles = [DetalleIVA(tipo_impositivo="21", base_imponible="0.00", cuota="0.00")]

    tipo_desglose = TipoDesglose(
        desglose_factura=DesgloseFacturaBlock(
            sujeta=SujetaBlock(
                no_exenta=NoExentaBlock(
                    tipo_no_exenta=TipoNoExenta.S1,
                    detalles_iva=detalles,
                )
            )
        )
    )

    return IssuedInvoiceRequest(
        titular=Titular(
            nombre_razon=d.get("company_name", ""),
            nif=d.get("company_nif", ""),
        ),
        tipo_comunicacion=TipoComunicacion(d.get("tipo_comunicacion", "A0")),
        periodo=PeriodoLiquidacion(
            ejercicio=d.get("fiscal_year", "2025"),
            periodo=d.get("fiscal_period", "01"),
        ),
        num_serie=d.get("invoice_number", ""),
        fecha_expedicion=d.get("invoice_date", ""),
        tipo_factura=TipoFactura(tipo_factura),
        clave_regimen=ClaveRegimen(d.get("clave_regimen", "01")),
        importe_total=str(d.get("importe_total", "0.00")),
        descripcion_operacion=d.get("descripcion", ""),
        ref_externa=d.get("ref_externa"),
        fecha_operacion=d.get("fecha_operacion"),
        contraparte=contraparte,
        tipo_desglose=tipo_desglose,
        dff=dff,
        operation_type=op_type,
    )


def map_oracle_received_invoice(oracle_data: dict) -> ReceivedInvoiceRequest:
    """Map Oracle ERP flat data dictionary to a ReceivedInvoiceRequest.

    Expected oracle_data keys:
        # Company / submitter
        company_name, company_nif,
        # Invoice header
        invoice_number, invoice_date, fiscal_year, fiscal_period,
        fecha_reg_contable, tipo_comunicacion,
        # Supplier
        supplier_name, supplier_country, supplier_tax_id, supplier_id_type,
        # Invoice details
        tipo_factura, clave_regimen, importe_total, descripcion,
        cuota_deducible, ref_externa, fecha_operacion,
        inversion_sujeto_pasivo (bool),
        # DFF fields
        dff_origen_factura, dff_tipo_rectificativa,
        dff_rect_num, dff_rect_date,
        dff_base_rectificada, dff_cuota_rectificada, dff_recargo_rectificado,
        dff_late_submission, dff_simplified, dff_billing_agreement,
        dff_third_party, dff_context_value,
        # VAT lines
        vat_lines: [{rate, base, cuota, recargo_rate, bien_inversion}]
        # ISP lines (optional)
        isp_lines: [{rate, base, cuota, bien_inversion}]
    """
    d = oracle_data

    tipo_factura = d.get("tipo_factura", "F1")
    supplier_country = d.get("supplier_country", "ES")
    op_type = detect_operation_type(supplier_country, tipo_factura)

    # Counterparty (supplier)
    cid = build_counterparty_id(
        supplier_country,
        d.get("supplier_tax_id", ""),
        op_type,
        d.get("supplier_id_type"),
    )
    contraparte = Contraparte(
        nombre_razon=d.get("supplier_name", ""),
        identification=cid,
    )

    # DFF
    rectif_type = d.get("dff_tipo_rectificativa")
    facturas_rect = None
    if d.get("dff_rect_num"):
        facturas_rect = [FacturaRectificada(
            num_serie=d["dff_rect_num"],
            fecha_expedicion=d.get("dff_rect_date", ""),
        )]

    importe_rect = None
    if rectif_type == "S":
        importe_rect = ImporteRectificacion(
            base_rectificada=d.get("dff_base_rectificada", "0.00"),
            cuota_rectificada=d.get("dff_cuota_rectificada", "0.00"),
            cuota_recargo_rectificado=d.get("dff_recargo_rectificado", "0.00"),
        )

    dff = ReceivedInvoiceDFF(
        origen_factura=d.get("dff_origen_factura"),
        tipo_rectificativa=TipoRectificativa(rectif_type) if rectif_type else None,
        facturas_rectificadas=facturas_rect,
        importe_rectificacion=importe_rect,
        late_submission=d.get("dff_late_submission", False),
        simplified_invoice=d.get("dff_simplified", False),
        billing_agreement=d.get("dff_billing_agreement"),
        third_party_invoice=d.get("dff_third_party", False),
        context_value=d.get("dff_context_value"),
    )

    # VAT lines
    vat_lines_data = d.get("vat_lines", [])
    detalles = [
        DetalleIVA(
            tipo_impositivo=str(vl["rate"]),
            base_imponible=str(vl["base"]),
            cuota=str(vl["cuota"]),
            tipo_recargo_equivalencia=str(vl["recargo_rate"]) if vl.get("recargo_rate") else None,
            bien_inversion=vl.get("bien_inversion"),
        )
        for vl in vat_lines_data
    ]
    if not detalles:
        detalles = [DetalleIVA(tipo_impositivo="21", base_imponible="0.00", cuota="0.00")]

    # ISP lines
    isp_block = None
    isp_lines_data = d.get("isp_lines", [])
    if isp_lines_data:
        isp_detalles = [
            DetalleIVA(
                tipo_impositivo=str(il["rate"]),
                base_imponible=str(il["base"]),
                cuota=str(il["cuota"]),
                bien_inversion=il.get("bien_inversion"),
            )
            for il in isp_lines_data
        ]
        isp_block = ISPBlock(detalles=isp_detalles)

    desglose = DesgloseFacturaRecibida(
        desglose_iva=DesgloseIVARecibida(detalles=detalles),
        inversion_sujeto_pasivo=isp_block,
    )

    return ReceivedInvoiceRequest(
        titular=Titular(
            nombre_razon=d.get("company_name", ""),
            nif=d.get("company_nif", ""),
        ),
        tipo_comunicacion=TipoComunicacion(d.get("tipo_comunicacion", "A0")),
        periodo=PeriodoLiquidacion(
            ejercicio=d.get("fiscal_year", "2025"),
            periodo=d.get("fiscal_period", "01"),
        ),
        num_serie=d.get("invoice_number", ""),
        fecha_expedicion=d.get("invoice_date", ""),
        tipo_factura=TipoFactura(tipo_factura),
        clave_regimen=ClaveRegimen(d.get("clave_regimen", "01")),
        importe_total=str(d.get("importe_total", "0.00")),
        descripcion_operacion=d.get("descripcion", ""),
        ref_externa=d.get("ref_externa"),
        cuota_deducible=str(d.get("cuota_deducible", "0.00")),
        fecha_reg_contable=d.get("fecha_reg_contable", ""),
        fecha_operacion=d.get("fecha_operacion"),
        contraparte=contraparte,
        inversion_sujeto_pasivo=d.get("inversion_sujeto_pasivo", False),
        desglose=desglose,
        dff=dff,
        operation_type=op_type,
    )
