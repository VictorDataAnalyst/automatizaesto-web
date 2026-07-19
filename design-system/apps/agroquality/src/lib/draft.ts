// Tipos del borrador de captura (Nueva inspección). Los campos numéricos se
// manejan como string en el formulario y se convierten al guardar.
export interface Foto {
  tipo: 'pallet' | 'muestra' | 'contenedor';
  ref: string;
  url?: string;
}

export interface Defecto {
  nombre: string;
  categoria: 'condicion' | 'calidad';
  pct: string;
}

export interface Termo {
  serial: string;
  trip_length_dias: string;
  temp_min: string;
  temp_max: string;
  temp_avg: string;
}

export interface DraftPallet {
  codigo: string;
  calibre: string;
  productor: string;
  pct_calidad: string;
  pct_condicion: string;
  defecto_principal: string;
  variedad: string;
  fecha_embalaje: string;
  etiqueta: string;
  embalaje: string;
  firmeza_psi_min: string;
  firmeza_psi_max: string;
  brix_prom: string;
  plu_pct: string;
  golpe_vista: string;
  qc_embalaje: string;
  clase: string;
  cajas_muestra: string;
  temp_prom: string;
  peso_neto_prom: string;
  tamano_muestra: string;
  trazabilidad: boolean;
  pti: boolean;
  base_pallet_danado: boolean;
  defectos: Defecto[];
  fotos: Foto[];
  _open: boolean;
}

export interface DraftInspeccion {
  codigo: string;
  lote: string;
  container: string;
  compania: string;
  exportador: string;
  consignatario: string;
  locacion: string;
  pais_origen: string;
  producto: string;
  variedad: string;
  embalaje: string;
  tipo_producto: string;
  tipo_inspeccion: string;
  barco: string;
  tipo_carrier: string;
  frigorifico: string;
  inspector: string;
  cajas: string;
  total_pallets: string;
  hora_frigorifico: string;
  fumigacion: string;
  num_factura: string;
  fecha_arribo: string;
  fecha_frigorifico: string;
  fecha_embalaje: string;
  notas_calidad: string;
  notas_inspector: string;
  digitado_por: string;
  numero_reporte: string;
  tecnologia_postcosecha: string;
  tipo_atmosfera: string;
  tipo_bolsa: string;
  upc: string;
  termografia: Termo[];
  fotos: Foto[];
  pallets: DraftPallet[];
}
