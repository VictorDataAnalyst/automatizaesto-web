// Listas y valores por defecto portados de static/index.html (nuevoDraft).
import type { DraftInspeccion } from './draft';

export const PRODUCTORES = [
  '004-03006-03', '016-42980-01', '016-4726-01', '010-62372-01', '009-33744-02', '016-40726-01',
];

export const DEFECTOS_COMUNES = [
  'Black Spots', 'Lenticelosis', 'Internal Breakdown', 'Black Color', 'Misshapen',
  'Russet Severe', 'Russet Slight', 'Deformes', 'Cuerpos Extraños', 'Sucio',
  'Cicatrices Severas', 'Fruta Virada', 'Pudrición', 'Daño por frío',
];

export const MAX_FOTOS = 15;

export const OPTS = {
  tipo_producto: ['CONV', 'ORG'],
  tipo_carrier: ['Ocean', 'Air'],
  tipo_inspeccion: ['Normal Inspection', 'Re-inspection', 'Pre-shipment'],
  fumigacion: ['None', 'SO2', 'Otra'],
  golpe_vista: [
    { value: '', label: '—' },
    { value: 'good', label: 'Good' },
    { value: 'fair', label: 'Fair' },
    { value: 'poor', label: 'Poor' },
  ],
};

export function nuevoDraft(): DraftInspeccion {
  return {
    codigo: '', lote: '', container: '', compania: 'Marand Company Asia', exportador: 'Marand Company',
    consignatario: '', locacion: '', pais_origen: 'Peru', producto: 'Avocados', variedad: 'Hass',
    embalaje: 'Plastic Box 10Kg', tipo_producto: 'CONV', tipo_inspeccion: 'Normal Inspection',
    barco: '', tipo_carrier: 'Ocean', frigorifico: '', inspector: '', cajas: '', total_pallets: '',
    hora_frigorifico: '', fumigacion: 'None', num_factura: '', fecha_arribo: '', fecha_frigorifico: '',
    fecha_embalaje: '', notas_calidad: '', notas_inspector: '', digitado_por: '',
    numero_reporte: '', tecnologia_postcosecha: '', tipo_atmosfera: '', tipo_bolsa: '', upc: '',
    termografia: [], fotos: [], pallets: [],
  };
}

export function nuevoPallet() {
  return {
    codigo: '', calibre: '', productor: PRODUCTORES[0], pct_calidad: '', pct_condicion: '',
    defecto_principal: '', variedad: '', fecha_embalaje: '', etiqueta: '', embalaje: '',
    firmeza_psi_min: '', firmeza_psi_max: '', brix_prom: '', plu_pct: '', golpe_vista: '',
    qc_embalaje: '', clase: '', cajas_muestra: '', temp_prom: '', peso_neto_prom: '10',
    tamano_muestra: '', trazabilidad: false, pti: false, base_pallet_danado: false,
    defectos: [], fotos: [], _open: false,
  };
}
