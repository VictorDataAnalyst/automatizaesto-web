-- =====================================================================
-- AgroQuality · 002 — Reporte "profesional" (formato tipo QIMA)
-- Cubre las 3 fases: A (fotos), B (ficha de pallet + notas), C (termografía).
-- SEGURO: solo agrega columnas/tablas nuevas. Idempotente.
-- =====================================================================

-- ---------- Fase A: galería del contenedor a nivel inspección ----------
alter table aq_inspeccion add column if not exists fotos jsonb;   -- [{tipo:'contenedor', ref}]

-- ---------- Fase B/C: notas y extras de cabecera ----------
alter table aq_inspeccion add column if not exists notas_calidad        text;
alter table aq_inspeccion add column if not exists notas_inspector      text;
alter table aq_inspeccion add column if not exists digitado_por         text;
alter table aq_inspeccion add column if not exists tecnologia_postcosecha text;
alter table aq_inspeccion add column if not exists tipo_atmosfera       text;
alter table aq_inspeccion add column if not exists tipo_bolsa           text;
alter table aq_inspeccion add column if not exists upc                  text;
alter table aq_inspeccion add column if not exists numero_reporte       text;

-- ---------- Fase B: ficha completa de pallet ----------
alter table aq_pallet add column if not exists variedad           text;
alter table aq_pallet add column if not exists fecha_embalaje      date;
alter table aq_pallet add column if not exists etiqueta            text;
alter table aq_pallet add column if not exists embalaje            text;
alter table aq_pallet add column if not exists firmeza_psi_min     numeric(6,2);
alter table aq_pallet add column if not exists firmeza_psi_max     numeric(6,2);
alter table aq_pallet add column if not exists plu_pct             numeric(6,2);
alter table aq_pallet add column if not exists golpe_vista         text;     -- good|fair|poor
alter table aq_pallet add column if not exists trazabilidad        boolean;
alter table aq_pallet add column if not exists pti                 boolean;
alter table aq_pallet add column if not exists base_pallet_danado  boolean;
alter table aq_pallet add column if not exists qc_embalaje         text;
-- Desglose de defectos por nombre con %: [{nombre, categoria:'calidad|condicion', pct}]
alter table aq_pallet add column if not exists defectos            jsonb;

-- ---------- Fase C: termografía por contenedor ----------
-- Lista de mediciones por contenedor: [{serial, trip_length_dias, temp_min, temp_max, temp_avg}]
alter table aq_inspeccion add column if not exists termografia jsonb;
