import type { FeaturesMeta, PatientRow, PredictResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export async function fetchFeatures(): Promise<FeaturesMeta> {
  const res = await fetch(`${API_BASE}/api/features`);
  if (!res.ok) throw new Error("Не удалось загрузить схему признаков");
  return res.json();
}

export async function predictPatients(
  patients: PatientRow[]
): Promise<PredictResponse> {
  const body = {
    patients: patients.map((row) => {
      const parsed: Record<string, number | null> = {};
      for (const [key, raw] of Object.entries(row)) {
        if (key.startsWith("_")) continue;
        if (raw === "" || raw === undefined) {
          parsed[key] = null;
        } else {
          const n = Number(raw);
          parsed[key] = Number.isFinite(n) ? n : null;
        }
      }
      return parsed;
    }),
  };

  const res = await fetch(`${API_BASE}/api/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Ошибка прогноза");
  }
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
