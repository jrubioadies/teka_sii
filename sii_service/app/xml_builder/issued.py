"""XML generator for SII Issued Invoices (SuministroLRFacturasEmitidas)."""

from app.models.issued import IssuedInvoiceRequest

from .common import (
    build_cabecera,
    build_contraparte,
    build_periodo,
    build_rectificacion,
    esc,
    is_rectification,
    soap_envelope_close,
    soap_envelope_open,
    xml_header,
)


def _build_detalle_iva_emitida(det, indent: str) -> str:
    """Build a single <sii:DetalleIVA> for issued invoices (CuotaRepercutida)."""
    x = f"{indent}<sii:DetalleIVA>\n"
    x += f"{indent}   <sii:TipoImpositivo>{esc(det.tipo_impositivo)}</sii:TipoImpositivo>\n"
    x += f"{indent}   <sii:BaseImponible>{esc(det.base_imponible)}</sii:BaseImponible>\n"
    x += f"{indent}   <sii:CuotaRepercutida>{esc(det.cuota)}</sii:CuotaRepercutida>\n"
    if det.tipo_recargo_equivalencia:
        x += f"{indent}   <sii:TipoRecargoEquivalencia>{esc(det.tipo_recargo_equivalencia)}</sii:TipoRecargoEquivalencia>\n"
        x += f"{indent}   <sii:CuotaRecargoEquivalencia>{esc(det.cuota_recargo_equivalencia or '0.00')}</sii:CuotaRecargoEquivalencia>\n"
    x += f"{indent}</sii:DetalleIVA>\n"
    return x


def _build_sujeta(sujeta, indent: str) -> str:
    """Build the <sii:Sujeta> block."""
    x = f"{indent}<sii:Sujeta>\n"

    if sujeta.no_exenta:
        ne = sujeta.no_exenta
        x += f"{indent}   <sii:NoExenta>\n"
        x += f"{indent}      <sii:TipoNoExenta>{esc(ne.tipo_no_exenta.value)}</sii:TipoNoExenta>\n"
        x += f"{indent}      <sii:DesgloseIVA>\n"
        for det in ne.detalles_iva:
            x += _build_detalle_iva_emitida(det, indent + "         ")
        x += f"{indent}      </sii:DesgloseIVA>\n"
        x += f"{indent}   </sii:NoExenta>\n"

    if sujeta.exenta:
        x += f"{indent}   <sii:Exenta>\n"
        for det in sujeta.exenta.detalles:
            x += f"{indent}      <sii:DetalleExenta>\n"
            x += f"{indent}         <sii:CausaExencion>{esc(det.causa_exencion.value)}</sii:CausaExencion>\n"
            x += f"{indent}         <sii:BaseImponible>{esc(det.base_imponible)}</sii:BaseImponible>\n"
            x += f"{indent}      </sii:DetalleExenta>\n"
        x += f"{indent}   </sii:Exenta>\n"

    x += f"{indent}</sii:Sujeta>\n"
    return x


def generate_issued_xml(req: IssuedInvoiceRequest) -> str:
    """Generate the full SOAP XML for SuministroLRFacturasEmitidas."""
    tipo = req.tipo_factura.value
    dff = req.dff

    x = xml_header()
    x += f"<!-- SII FacturasEmitidas | Op: {req.operation_type.value} | TipoFactura: {tipo} -->\n"
    x += soap_envelope_open()
    x += "      <siiLR:SuministroLRFacturasEmitidas>\n\n"

    # Cabecera
    x += build_cabecera(req.titular.nombre_razon, req.titular.nif, req.tipo_comunicacion.value)

    # Registro
    x += "         <siiLR:RegistroLRFacturasEmitidas>\n"
    x += build_periodo(req.periodo.ejercicio, req.periodo.periodo)

    # IDFactura — for issued invoices, IDEmisorFactura uses the titular's NIF
    x += "            <siiLR:IDFactura>\n"
    x += "               <sii:IDEmisorFactura>\n"
    x += f"                  <sii:NIF>{esc(req.titular.nif)}</sii:NIF>\n"
    x += "               </sii:IDEmisorFactura>\n"
    x += f"               <sii:NumSerieFacturaEmisor>{esc(req.num_serie)}</sii:NumSerieFacturaEmisor>\n"
    if req.num_serie_resumen_fin:
        x += f"               <sii:NumSerieFacturaEmisorResumenFin>{esc(req.num_serie_resumen_fin)}</sii:NumSerieFacturaEmisorResumenFin>\n"
    x += f"               <sii:FechaExpedicionFacturaEmisor>{esc(req.fecha_expedicion)}</sii:FechaExpedicionFacturaEmisor>\n"
    x += "            </siiLR:IDFactura>\n\n"

    # FacturaExpedida
    x += "            <siiLR:FacturaExpedida>\n"
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
    if dff.simplified_invoice:
        x += "               <sii:FacturaSimplificadaArticulos7.2_7.3>S</sii:FacturaSimplificadaArticulos7.2_7.3>\n"
    if dff.sin_identif_destinatario:
        x += "               <sii:FacturaSinIdentifDestinatarioArticulo6.1.d>S</sii:FacturaSinIdentifDestinatarioArticulo6.1.d>\n"
    if dff.macrodato:
        x += "               <sii:Macrodato>S</sii:Macrodato>\n"
    if dff.billing_agreement:
        x += f"               <sii:NumRegistroAcuerdoFacturacion>{esc(dff.billing_agreement[:15])}</sii:NumRegistroAcuerdoFacturacion>\n"
    if dff.emitida_por_terceros:
        x += f"               <sii:EmitidaPorTercerosODestinatario>{esc(dff.emitida_por_terceros)}</sii:EmitidaPorTercerosODestinatario>\n"

    x += f"               <sii:ImporteTotal>{esc(req.importe_total)}</sii:ImporteTotal>\n"
    x += f"               <sii:DescripcionOperacion>{esc(req.descripcion_operacion)}</sii:DescripcionOperacion>\n"

    # Contraparte
    if req.contraparte:
        x += build_contraparte(
            req.contraparte.nombre_razon,
            req.contraparte.identification,
            indent="               ",
        )

    if req.fecha_operacion:
        x += f"               <sii:FechaOperacion>{esc(req.fecha_operacion)}</sii:FechaOperacion>\n"
    if req.ref_externa:
        x += f"               <sii:RefExterna>{esc(req.ref_externa)}</sii:RefExterna>\n"

    # EntidadSucedida
    if req.entidad_sucedida_nif:
        x += "               <sii:EntidadSucedida>\n"
        x += "                  <sii:NombreRazon></sii:NombreRazon>\n"
        x += f"                  <sii:NIF>{esc(req.entidad_sucedida_nif)}</sii:NIF>\n"
        x += "               </sii:EntidadSucedida>\n"

    # === TipoDesglose ===
    x += "\n               <sii:TipoDesglose>\n"
    td = req.tipo_desglose

    if td.desglose_factura:
        df = td.desglose_factura
        x += "                  <sii:DesgloseFactura>\n"
        x += _build_sujeta(df.sujeta, "                     ")

        if df.no_sujeta:
            x += "                     <sii:NoSujeta>\n"
            for ns in df.no_sujeta.detalles:
                x += "                        <sii:DetalleNoSujeta>\n"
                x += f"                           <sii:Causa>{esc(ns.causa.value)}</sii:Causa>\n"
                x += f"                           <sii:Importe>{esc(ns.importe)}</sii:Importe>\n"
                x += "                        </sii:DetalleNoSujeta>\n"
            x += "                     </sii:NoSujeta>\n"

        x += "                  </sii:DesgloseFactura>\n"

    elif td.desglose_tipo_operacion:
        to = td.desglose_tipo_operacion
        tag = "PrestacionDeServicios" if to.tipo_operacion == "servicio" else "Entrega"
        x += "                  <sii:DesgloseTipoOperacion>\n"
        x += f"                     <sii:{tag}>\n"
        x += _build_sujeta(to.sujeta, "                        ")

        if to.exenta_tipoop:
            x += "                        <sii:Exenta>\n"
            for det in to.exenta_tipoop.detalles:
                x += "                           <sii:DetalleExenta>\n"
                x += f"                              <sii:CausaExencion>{esc(det.causa_exencion.value)}</sii:CausaExencion>\n"
                x += f"                              <sii:BaseImponible>{esc(det.base_imponible)}</sii:BaseImponible>\n"
                x += "                           </sii:DetalleExenta>\n"
            x += "                        </sii:Exenta>\n"

        x += f"                     </sii:{tag}>\n"
        x += "                  </sii:DesgloseTipoOperacion>\n"

    x += "               </sii:TipoDesglose>\n"
    x += "            </siiLR:FacturaExpedida>\n"
    x += "         </siiLR:RegistroLRFacturasEmitidas>\n"
    x += "      </siiLR:SuministroLRFacturasEmitidas>\n"
    x += soap_envelope_close()

    return x
