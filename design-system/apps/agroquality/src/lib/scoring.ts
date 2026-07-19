import type { Inspeccion, Score, Filtros } from '../types';

// Portado 1:1 del front actual (static/index.html).
export const SCORE_LABEL: Record<Score, string> = { good: 'Good', fair: 'Fair', poor: 'Poor' };

export function scoreDe(p: number): Score {
  if (p < 12) return 'good';
  if (p <= 25) return 'fair';
  return 'poor';
}

export interface Resumen {
  n: number;
  cont: Record<Score, number>;
  scoreGlobal: Score;
  calProm: number;
  condProm: number;
  totProm: number;
  tempProm: number | null;
  pesoProm: number;
}

export function resumen(ins: Inspeccion): Resumen {
  const ps = ins.pallets ?? [];
  const n = ps.length || 1;
  const cont: Record<Score, number> = { good: 0, fair: 0, poor: 0 };
  let cal = 0, cond = 0, temp = 0, tempN = 0, peso = 0;
  ps.forEach((p) => {
    if (p.pallet_score) cont[p.pallet_score] = (cont[p.pallet_score] ?? 0) + 1;
    cal += Number(p.pct_calidad) || 0;
    cond += Number(p.pct_condicion) || 0;
    if (p.temp_prom) { temp += Number(p.temp_prom); tempN++; }
    peso += Number(p.peso_neto_prom) || 0;
  });
  const totProm = +((cal + cond) / n).toFixed(2);
  return {
    n,
    cont,
    scoreGlobal: scoreDe(totProm),
    calProm: +(cal / n).toFixed(2),
    condProm: +(cond / n).toFixed(2),
    totProm,
    tempProm: tempN ? +(temp / tempN).toFixed(1) : null,
    pesoProm: +(peso / n).toFixed(1),
  };
}

export function pctScore(c: Record<Score, number>): Record<Score, number> {
  // Redondeo por mayor resto: good+fair+poor SIEMPRE suma 100 (nunca 101).
  const tot = (c.good ?? 0) + (c.fair ?? 0) + (c.poor ?? 0);
  if (!tot) return { good: 0, fair: 0, poor: 0 };
  const raw: Record<Score, number> = {
    good: ((c.good ?? 0) / tot) * 100,
    fair: ((c.fair ?? 0) / tot) * 100,
    poor: ((c.poor ?? 0) / tot) * 100,
  };
  const r: Record<Score, number> = {
    good: Math.floor(raw.good),
    fair: Math.floor(raw.fair),
    poor: Math.floor(raw.poor),
  };
  const resto = 100 - (r.good + r.fair + r.poor);
  const ord = (['good', 'fair', 'poor'] as Score[]).sort((a, b) => (raw[b] % 1) - (raw[a] % 1));
  for (let i = 0; i < resto; i++) r[ord[i % 3]]++;
  return r;
}

export function fmtFecha(s?: string): string {
  if (!s) return '—';
  const [y, m, d] = s.split('-');
  return `${d}/${m}/${y}`;
}

function inRango(f: string | undefined, d1: string, d2: string): boolean {
  if (!f) return false;
  if (d1 && f < d1) return false;
  if (d2 && f > d2) return false;
  return true;
}

export function filtradas(data: Inspeccion[], fil: Filtros): Inspeccion[] {
  return data.filter((i) => {
    if ((fil.d1 || fil.d2) && !inRango(i.fecha_frigorifico, fil.d1, fil.d2)) return false;
    if (fil.consig && i.consignatario !== fil.consig) return false;
    if (fil.score && resumen(i).scoreGlobal !== fil.score) return false;
    return true;
  });
}
