export type FieldOption = { value: number; label: string };

export type FieldDef = {
  key: string;
  column: string;
  label: string;
  type: "number" | "select";
  min?: number;
  max?: number;
  step?: number;
  options?: FieldOption[];
};

export type FeaturesMeta = {
  model_name: string;
  model_description: string;
  threshold: number;
  feature_keys: string[];
  fields: FieldDef[];
};

export type PatientRow = Record<string, string>;

export type PredictionResult = {
  probability: number;
  label: number;
  label_text: string;
  risk_level: string;
};

export type PredictResponse = {
  predictions: PredictionResult[];
  threshold: number;
  model_name: string;
};
