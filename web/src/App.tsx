import { useEffect, useState } from "react";
import { checkHealth, fetchFeatures } from "./api";
import { PatientTable } from "./PatientTable";
import type { FeaturesMeta } from "./types";
import "./App.css";

export default function App() {
  const [meta, setMeta] = useState<FeaturesMeta | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const ok = await checkHealth();
      setApiOk(ok);
      if (!ok) {
        setError("API недоступен. Запустите backend на порту 8000 или docker compose up.");
        return;
      }
      try {
        setMeta(await fetchFeatures());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Ошибка загрузки");
      }
    })();
  }, []);

  return (
    <div className="app">
      <header>
        <h1>ПРОДЕТИ_РИСК</h1>
        <p className="subtitle">
          Прогноз послеоперационного делирия (ПОД) у детей — PoC на случайном лесе
        </p>
        {meta && (
          <p className="model-info">
            {meta.model_description}
            <span className="api-status" data-ok={apiOk}>
              API {apiOk ? "online" : "offline"}
            </span>
          </p>
        )}
      </header>

      <main>
        {error && <div className="banner error">{error}</div>}
        {meta ? (
          <PatientTable meta={meta} />
        ) : (
          !error && <div className="banner">Загрузка…</div>
        )}
      </main>

      <footer>
        PoC не заменяет клиническое решение. Пустые поля заполняются медианой при расчёте.
      </footer>
    </div>
  );
}
