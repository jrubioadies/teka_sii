"""XML generator for SII Received Invoices (SuministroLRFacturasRecibidas)."""

from app.models.received import ReceivedInvoiceRequest

from .common import (
    build_cabecera,
    build_contraparte,
    build_id_block,
    build_periodo,
    build_rectificacion,
    esc,
    is_rectification,
    soap_envelope_close,
    soap_envelope_open,
    xml_header,
)


def _build_detalle_iva_recibida(det, indent: str) -> str:
    """Build a single <sii:DetalleIVA> for received invoices (CuotaSoportada)."""
    x = f"{indent}<sii:DetalleIVA>\n"
    x += f"{indent}   <sii:TipoImpositivo>{esc(det.tipo_impositivo)}</sii:TipoImpositivo>\n"
    x += f"{indent}   <sii:BaseImponible>{esc(det.base_imponible)}</sii:BaseImponible>\n"
    x += f"{indent}   <sii:CuotaSoportada>{esc(det.cuota)}</sii:CuotaSoportada>\n"
    if det.tipo_recargo_equivalencia:
        x += f"{indent}   <sii:TipoRecargoEquivalencia>{esc(det.tipo_recargo_equivalencia)}</sii:TipoRecargoEquivalencia>\n"
    if det.bien_inversion:
        x += f"{indent}   <sii:BienInversion>{esc(det.bien_inversion)}</sii:BienInversion>\n"
    x += f"{indent}</sii:DetalleIVA>\n"
    return x


def generate_received_xml(req: ReceivedInvoiceRequest) -> str:
    """Generate the full SOAP XML for SuministroLRFacturasRecibidas."""
    tipo = req.tipo_factura.value
    dff = req.dff
    is_domestic = req.operation_type.value == "domestic"

    x = xml_header()
    x += f"<!-- SII FacturasRecibidas | Op: {req.operation_type.value} | TipoFactura: {tipo} -->\n"
    x += soap_envelope_open()
    x += "      <siiLR:SuministroLRFacturasRecibidas>\n\n"

    # Cabecera
    x += build_cabecera(req.titular.nombre_razon, req.titular.nif, req.tipo_comunicacion.value)

    # Registro
    x += "         <siiLR:RegistroLRFacturasRecibidas>\n"
    x += build_periodo(req.periodo.ejercicio, req.periodo.periodo)

    # IDFactura — for received invoices, IDEmisorFactura is the supplier
    x += "            <siiLR:IDFactura>\n"
    x += "               <sii:IDEmisorFactura>\n"
    x += build_id_block(req.contraparte.identification, "                  ") + "\n"
    x += "               </sii:IDEmisorFactura>\n"
    x += f"               <sii:NumSerieFacturaEmisor>{esc(req.num_serie)}</sii:NumSerieFacturaEmisor>\n"
    if req.num_serie_resumen_fin:
        x += f"               <sii:NumSerieFacturaEmisorResumenFin>{esc(req.num_serie_resumen_fin)}</sii:NumSerieFacturaEmisorResumenFin>\n"
    x += f"               <sii:FechaExpedicionFacturaEmisor>{esc(req.fecha_expedicion)}</sii:FechaExpedicionFacturaEmisor>\n"
    x += "            </siiLR:IDFactura>\n\n"

    # FacturaRecibida
    x += "            <siiLR:FacturaRecibida>\n"
    x += f"               <sii:TipoFactura>{esc(tipo)}</sii:TipoFactura>\n"

    # Rectification
    if is_rectification(tipo) and dff.tipo_rectificativa:
        x += build_rectificacion(
            dff.tipo_rectificativa.value,
            dff.facturas_rectificadas,
            dff.importe_rectificacion,
            indent="               ",
        )

    # Clave regimen
    x += f"               <sii:ClaveRegimenEspecialOTrascendencia>{esc(req.clave_regimen.value)}</sii:ClaveRegimenEspecialOTrascendencia>\n"
    if req.clave_regimen_adicional_1:
        x += f"               <sii:ClaveRegimenEspecialOTrascendenciaAdicional1>{esc(req.clave_regimen_adicional_1.value)}</sii:ClaveRegimenEspecialOTrascendenciaAdicional1>\n"
    if req.clave_regimen_adicional_2:
        x += f"               <sii:ClaveRegimenEspecialOTrascendenciaAdicional2>{esc(req.clave_regimen_adicional_2.value)}</sii:ClaveRegimenEspecialOTrascendenciaAdicional2>\n"

    # Optional DFF flags
    if dff.billing_agreement:
        x += f"               <sii:NumRegistroAcuerdoFacturacion>{esc(dff.billing_agreement[:15])}</sii:NumRegistroAcuerdoFacturacion>\n"

    x += f"               <sii:ImporteTotal>{esc(req.importe_total)}</sii:ImporteTotal>\n"
    x += f"               <sii:DescripcionOperacion>{esc(req.descripcion_operacion)}</sii:DescripcionOperacion>\n"

    if req.ref_externa:
        x += f"               <sii:RefExterna>{esc(req.ref_externa)}</sii:RefExterna>\n"

    if dff.simplified_invoice:
        x += "               <sii:FacturaSimplificadaArticulos7.2_7.3>S</sii:FacturaSimplificadaArticulos7.2_7.3>\n"

    # Contraparte
    x += build_contraparte(
        req.contraparte.nombre_razon,
        req.contraparte.identification,
        indent="               ",
    )

    if req.fecha_operacion:
        x += f"               <sii:FechaOperacion>{esc(req.fecha_operacion)}</sii:FechaOperacion>\n"

    x += f"               <sii:FechaRegContable>{esc(req.fecha_reg_contable)}</sii:FechaRegContable>\n"
    x += f"               <sii:CuotaDeducible>{esc(req.cuota_deducible)}</sii:CuotaDeducible>\n"

    if dff.late_submission:
        x += "               <sii:RegPrevioGGEEoREDEMEoCompetencia>S</sii:RegPrevioGGEEoREDEMEoCompetencia>\n"

    # === DesgloseFactura ===
    x += "\n               <sii:DesgloseFactura>\n"

    # ISP block
    if req.desglose.inversion_sujeto_pasivo:
        x += "                  <sii:InversionSujetoPasivo>\n"
        for det in req.desglose.inversion_sujeto_pasivo.detalles:
            x += _build_detalle_iva_recibida(det, "                     ")
        x += "                  </sii:InversionSujetoPasivo>\n"

    # Standard DesgloseIVA
    x += "                  <sii:DesgloseIVA>\n"
    for det in req.desglose.desglose_iva.detalles:
        x += _build_detalle_iva_recibida(det, "                     ")
    x += "                  </sii:DesgloseIVA>\n"

    x += "               </sii:DesgloseFactura>\n"
    x += "            </siiLR:FacturaRecibida>\n"
    x += "         </siiLR:RegistroLRFacturasRecibidas>\n"
    x += "      </siiLR:SuministroLRFacturasRecibidas>\n"
    x += soap_envelope_close()

    return x
