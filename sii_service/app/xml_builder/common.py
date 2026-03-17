"""Shared XML building utilities for SII SOAP envelopes."""

from xml.sax.saxutils import escape

from app.models.common import CounterpartyID

NS_SII = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii/fact/ws/SuministroInformacion.xsd"
NS_SIILR = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii/fact/ws/SuministroLR.xsd"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS_SOAPENV = "http://schemas.xmlsoap.org/soap/envelope/"

SII_VERSION = "1.1"


def esc(value: str) -> str:
    """Escape XML special characters."""
    return escape(str(value))


def xml_header() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n'


def soap_envelope_open() -> str:
    return (
        "<soapenv:Envelope\n"
        f'   xmlns:sii="{NS_SII}"\n'
        f'   xmlns:siiLR="{NS_SIILR}"\n'
        f'   xmlns:xsi="{NS_XSI}"\n'
        f'   xmlns:soapenv="{NS_SOAPENV}">\n'
        "   <soapenv:Header/>\n"
        "   <soapenv:Body>\n"
    )


def soap_envelope_close() -> str:
    return "   </soapenv:Body>\n</soapenv:Envelope>"


def build_cabecera(nombre: str, nif: str, tipo_com: str) -> str:
    return (
        "         <sii:Cabecera>\n"
        f"            <sii:IDVersionSii>{SII_VERSION}</sii:IDVersionSii>\n"
        "            <sii:Titular>\n"
        f"               <sii:NombreRazon>{esc(nombre)}</sii:NombreRazon>\n"
        f"               <sii:NIF>{esc(nif)}</sii:NIF>\n"
        "            </sii:Titular>\n"
        f"            <sii:TipoComunicacion>{esc(tipo_com)}</sii:TipoComunicacion>\n"
        "         </sii:Cabecera>\n\n"
    )


def build_periodo(ejercicio: str, periodo: str) -> str:
    return (
        "            <sii:PeriodoLiquidacion>\n"
        f"               <sii:Ejercicio>{esc(ejercicio)}</sii:Ejercicio>\n"
        f"               <sii:Periodo>{esc(periodo)}</sii:Periodo>\n"
        "            </sii:PeriodoLiquidacion>\n\n"
    )


def build_id_block(counterparty_id: CounterpartyID, indent: str = "               ") -> str:
    """Build the NIF or IDOtro identification block."""
    if counterparty_id.nif:
        return f"{indent}<sii:NIF>{esc(counterparty_id.nif)}</sii:NIF>"

    if counterparty_id.id_otro:
        o = counterparty_id.id_otro
        return (
            f"{indent}<sii:IDOtro>\n"
            f"{indent}   <sii:CodigoPais>{esc(o.codigo_pais)}</sii:CodigoPais>\n"
            f"{indent}   <sii:IDType>{esc(o.id_type.value)}</sii:IDType>\n"
            f"{indent}   <sii:ID>{esc(o.id_value)}</sii:ID>\n"
            f"{indent}</sii:IDOtro>"
        )

    return f"{indent}<!-- ERROR: no identification provided -->"


def build_contraparte(nombre: str, counterparty_id: CounterpartyID, indent: str = "               ") -> str:
    id_block = build_id_block(counterparty_id, indent + "   ")
    return (
        f"{indent}<sii:Contraparte>\n"
        f"{indent}   <sii:NombreRazon>{esc(nombre)}</sii:NombreRazon>\n"
        f"{id_block}\n"
        f"{indent}</sii:Contraparte>\n"
    )


def build_rectificacion(
    tipo_rectificativa: str,
    facturas_rectificadas: list | None,
    importe_rectificacion=None,
    indent: str = "               ",
) -> str:
    x = f"{indent}<sii:TipoRectificativa>{esc(tipo_rectificativa)}</sii:TipoRectificativa>\n"

    if facturas_rectificadas:
        x += f"{indent}<sii:FacturasRectificadas>\n"
        for fr in facturas_rectificadas:
            x += (
                f"{indent}   <sii:IDFacturaRectificada>\n"
                f"{indent}      <sii:NumSerieFacturaEmisor>{esc(fr.num_serie)}</sii:NumSerieFacturaEmisor>\n"
                f"{indent}      <sii:FechaExpedicionFacturaEmisor>{esc(fr.fecha_expedicion)}</sii:FechaExpedicionFacturaEmisor>\n"
                f"{indent}   </sii:IDFacturaRectificada>\n"
            )
        x += f"{indent}</sii:FacturasRectificadas>\n"

    if importe_rectificacion and tipo_rectificativa == "S":
        ir = importe_rectificacion
        x += (
            f"{indent}<sii:ImporteRectificacion>\n"
            f"{indent}   <sii:BaseRectificada>{esc(ir.base_rectificada)}</sii:BaseRectificada>\n"
            f"{indent}   <sii:CuotaRectificada>{esc(ir.cuota_rectificada)}</sii:CuotaRectificada>\n"
            f"{indent}   <sii:CuotaRecargoRectificado>{esc(ir.cuota_recargo_rectificado)}</sii:CuotaRecargoRectificado>\n"
            f"{indent}</sii:ImporteRectificacion>\n"
        )

    return x


def is_rectification(tipo_factura: str) -> bool:
    return tipo_factura in ("R1", "R2", "R3", "R4", "R5")
