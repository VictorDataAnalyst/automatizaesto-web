export type Score = 'good' | 'fair' | 'poor';

export interface Pallet {
  codigo?: string;
  productor?: string;
  calibre?: number;
  temp_prom?: number;
  peso_neto_prom?: number;
  pct_calidad?: number;
  pct_condicion?: number;
  pct_total?: number;
  pallet_score?: Score;
  defecto_principal?: string;
}

export interface Inspeccion {
  id: string;
  codigo?: string;
  lote?: string;
  barco?: string;
  consignatario?: string;
  locacion?: string;
  fecha_frigorifico?: string;
  cajas?: number;
  producto?: string;
  variedad?: string;
  inspector?: string;
  score_global?: Score;
  pallets?: Pallet[];
}

export interface Filtros {
  d1: string;
  d2: string;
  score: '' | Score;
  consig: string;
}
