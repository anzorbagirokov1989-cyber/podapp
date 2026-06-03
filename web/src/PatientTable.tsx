import { useCallback, useEffect, useState } from "react";
import { predictPatients } from "./api";
import { FieldSelect } from "./FieldSelect";
import type { FieldDef, FeaturesMeta, PatientRow, PredictionResult } from "./types";

function emptyRow(keys: string[]): PatientRow {
  return Object.fromEntries(keys.map((k) => [k, ""]));
}

function newId() {
  return crypto.randomUUID();
}

function rowHasData(row: PatientRow, keys: string[]): boolean {
  return keys.some((k) => {
    const v = row[k];
    return v !== "" && v !== undefined && v !== null;
  });
}

type RowState = PatientRow & { _id: string };

type Props = {
  meta: FeaturesMeta;
};

export function PatientTable({ meta }: Props) {
  const keys = meta.feature_keys;
  const [rows, setRows] = useState<RowState[]>([
    { ...emptyRow(keys), _id: newId() },
  ]);
  const [predictions, setPredictions] = useState<Record<string, PredictionResult>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateCell = useCallback(
    (id: string, key: string, value: string) => {
      setRows((prev) =>
        prev.map((r) => (r._id === id ? { ...r, [key]: value } : r))
      );
    },
    []
  );

  const addRow = () => {
    setRows((prev) => [...prev, { ...emptyRow(keys), _id: newId() }]);
  };

  const removeRow = (id: string) => {
    setRows((prev) => (prev.length <= 1 ? prev : prev.filter((r) => r._id !== id)));
    setPredictions((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const runPredict = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = rows.map(({ _id, ...rest }) => rest);
      const res = await predictPatients(payload);
      const map: Record<string, PredictionResult> = {};
      rows.forEach((r, i) => {
        if (rowHasData(r, keys)) {
          map[r._id] = res.predictions[i];
        }
      });
      setPredictions(map);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка прогноза");
    } finally {
      setLoading(false);
    }
  }, [rows, keys]);

  useEffect(() => {
    const t = setTimeout(() => {
      if (!rows.some((r) => rowHasData(r, keys))) {
        setPredictions({});
        return;
      }
      runPredict();
    }, 600);
    return () => clearTimeout(t);
  }, [rows, keys, runPredict]);

  const renderInput = (field: FieldDef, row: RowState) => {
    const value = row[field.key] ?? "";
    if (field.type === "select" && field.options) {
      return (
        <FieldSelect
          value={value}
          options={field.options}
          title={field.column}
          onChange={(v) => updateCell(row._id, field.key, v)}
        />
      );
    }
    return (
      <input
        className="field-input"
        type="number"
        value={value}
        min={field.min}
        max={field.max}
        step={field.step ?? 1}
        placeholder="—"
        title={field.column}
        onChange={(e) => updateCell(row._id, field.key, e.target.value)}
      />
    );
  };

  const predCell = (row: RowState) => {
    if (!rowHasData(row, keys)) {
      return <div className="delirium-slot delirium-slot--empty" />;
    }

    const p = predictions[row._id];
    const cls = p
      ? p.label === 1
        ? "delirium yes"
        : "delirium no"
      : "delirium pending";
    return (
      <div className="delirium-slot">
        <div className={cls}>
          <strong>{p ? p.label_text : "—"}</strong>
          <span className="prob">
            {p ? `${(p.probability * 100).toFixed(1)}%` : "\u00A0"}
          </span>
          <span className="risk">{p ? p.risk_level : "\u00A0"}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="table-section">
      <div className="toolbar">
        <button type="button" className="btn-primary" onClick={addRow}>
          + Пациент
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={runPredict}
          disabled={loading}
        >
          <span className="btn-label">
            {loading ? "Расчёт…" : "Рассчитать прогноз"}
          </span>
        </button>
        {loading && <span className="loading-dot" aria-hidden />}
        {error && <span className="toolbar-error">{error}</span>}
      </div>

      <div className="table-wrap">
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th className="sticky-col">#</th>
                {meta.fields.map((f) => (
                  <th key={f.key} title={f.column}>
                    {f.label}
                  </th>
                ))}
                <th className="delirium-col sticky-delirium-th">Делирий</th>
                <th className="actions-col-tr" /> 
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={row._id}>
                  <td className="sticky-col">{idx + 1}</td>
                  {meta.fields.map((f) => (
                    <td key={f.key}>{renderInput(f, row)}</td>
                  ))}
                  <td className="delirium-col sticky-delirium">
                    {predCell(row)}
                  </td>
                  <td className="actions-col">
                    <button
                      type="button"
                      className="btn-remove"
                      onClick={() => removeRow(row._id)}
                      disabled={rows.length <= 1}
                      aria-label="Удалить строку"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
