import copy
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import to_categorical

from app.core.config import MODEL_PATH, PREPROCESSORS_PATH
from app.models.artifacts import load_artifacts, save_artifacts
from app.models.neural import build_model
from app.models.preprocessing import (
    FEATURE_COLUMNS,
    NUMERIC_COLUMNS,
    TARGET_COLUMNS,
    PHASE_NAMES,
)
from app.schemas.plan import FeedbackRequest, PlanResponse, UserProfile


class PlanService:
    def __init__(self, model_path=MODEL_PATH, preprocessors_path=PREPROCESSORS_PATH, backup_dir=None):
        self.model_path = Path(model_path)
        self.preprocessors_path = Path(preprocessors_path)
        self.backup_dir = Path(backup_dir) if backup_dir is not None else self.model_path.parent / "backups"
        artifacts = load_artifacts(preprocessors_path)
        self.df_encoded = artifacts["df_encoded"]
        self.feature_columns = artifacts["feature_columns"]
        self.target_columns = artifacts["target_columns"]
        self.categorical_columns = artifacts["categorical_columns"]
        self.le_dict = artifacts["le_dict"]
        self.target_encoders = artifacts["target_encoders"]
        self.scaler = artifacts["scaler"]
        self.num_classes = artifacts["num_classes"]
        self.categorical_defaults = artifacts["categorical_defaults"]
        self.model = load_model(model_path)
        self._feedback_lock = threading.Lock()

    def _encode_features(self, raw: dict) -> pd.DataFrame:
        input_df = pd.DataFrame([raw], columns=FEATURE_COLUMNS)
        for col in self.categorical_columns:
            val = str(input_df[col].iloc[0])
            le = self.le_dict[col]
            if val not in le.classes_:
                val = self.categorical_defaults.get(col, le.classes_[0])
            input_df[col] = le.transform([val])[0]
        numeric = pd.DataFrame([{c: raw[c] for c in NUMERIC_COLUMNS}], columns=NUMERIC_COLUMNS)
        input_df[NUMERIC_COLUMNS] = self.scaler.transform(numeric[NUMERIC_COLUMNS])
        return input_df

    def generate_plan(self, profile: UserProfile) -> PlanResponse:
        if self.model is None:
            raise RuntimeError("Modelo no disponible")
        input_df = self._encode_features(profile.to_features())
        predictions = self.model.predict(input_df, verbose=0)
        values = [
            self.target_encoders[col].inverse_transform([np.argmax(predictions[i])])[0]
            for i, col in enumerate(self.target_columns)
        ]
        return PlanResponse(
            calentamiento=values[0],
            entrenamiento=values[1],
            enfriamiento=values[2],
        )

    def list_exercises(self) -> dict:
        return {
            PHASE_NAMES[i]: sorted(self.target_encoders[col].classes_.tolist())
            for i, col in enumerate(self.target_columns)
        }

    def apply_feedback(self, request: FeedbackRequest) -> dict:
        if request.suitable:
            return {
                "status": "ok",
                "retrained": False,
                "message": "Plan adecuado, no se requiere reentrenamiento",
            }
        if self.model is None:
            raise RuntimeError("Modelo no disponible")

        with self._feedback_lock:
            return self._retrain_from_feedback(request)

    def _retrain_from_feedback(self, request: FeedbackRequest) -> dict:
        df = self.df_encoded.copy()
        le_dict = copy.deepcopy(self.le_dict)
        target_encoders = copy.deepcopy(self.target_encoders)
        num_classes = dict(self.num_classes)
        new_row = pd.DataFrame([request.input_data.to_features()])

        for col in self.categorical_columns:
            val = str(new_row[col].iloc[0])
            le = le_dict[col]
            if val not in le.classes_:
                le.classes_ = np.append(le.classes_, val)
            new_row[col] = le.transform([val])[0]

        numeric = pd.DataFrame(
            [{c: request.input_data.to_features()[c] for c in NUMERIC_COLUMNS}],
            columns=NUMERIC_COLUMNS,
        )
        new_row[NUMERIC_COLUMNS] = self.scaler.transform(numeric[NUMERIC_COLUMNS])

        corrected = {
            "Calentamiento": request.corrected_exercises.calentamiento,
            "Entrenamiento": request.corrected_exercises.entrenamiento,
            "Enfriamiento": request.corrected_exercises.enfriamiento,
        }
        for col, fase in zip(self.target_columns, PHASE_NAMES):
            val = corrected[fase]
            le = target_encoders[col]
            if val not in le.classes_:
                le.classes_ = np.append(le.classes_, val)
                num_classes[col] = len(le.classes_)
            new_row[col] = le.transform([val])[0]

        df = pd.concat([df, new_row], ignore_index=True)
        X = df[FEATURE_COLUMNS]
        y1 = to_categorical(df[self.target_columns[0]], num_classes=num_classes[self.target_columns[0]])
        y2 = to_categorical(df[self.target_columns[1]], num_classes=num_classes[self.target_columns[1]])
        y3 = to_categorical(df[self.target_columns[2]], num_classes=num_classes[self.target_columns[2]])

        model = build_model(len(FEATURE_COLUMNS), [
            num_classes[self.target_columns[0]],
            num_classes[self.target_columns[1]],
            num_classes[self.target_columns[2]],
        ])
        model.fit(X, [y1, y2, y3], epochs=10, batch_size=32, verbose=0)

        payload = {
            "df_encoded": df,
            "feature_columns": FEATURE_COLUMNS,
            "target_columns": TARGET_COLUMNS,
            "categorical_columns": self.categorical_columns,
            "le_dict": le_dict,
            "target_encoders": target_encoders,
            "scaler": self.scaler,
            "num_classes": num_classes,
            "categorical_defaults": self.categorical_defaults,
        }
        backup_dir = self._backup_artifacts()
        try:
            model.save(self.model_path)
            save_artifacts(payload, self.preprocessors_path)
        except Exception:
            self._restore_artifacts(backup_dir)
            raise

        self.model = model
        self.df_encoded = df
        self.le_dict = le_dict
        self.target_encoders = target_encoders
        self.num_classes = num_classes
        return {
            "status": "ok",
            "retrained": True,
            "message": "Modelo reentrenado y guardado",
        }

    def _artifact_paths(self) -> tuple[Path, Path]:
        return self.model_path, self.preprocessors_path

    def _backup_artifacts(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_dir = self.backup_dir / stamp
        backup_dir.mkdir(parents=True, exist_ok=False)
        for artifact_path in self._artifact_paths():
            if not artifact_path.exists():
                raise RuntimeError(f"No se encontró el artefacto para backup: {artifact_path}")
            shutil.copy2(artifact_path, backup_dir / artifact_path.name)
        return backup_dir

    def _restore_artifacts(self, backup_dir: Path):
        for artifact_path in self._artifact_paths():
            backup_path = backup_dir / artifact_path.name
            if backup_path.exists():
                shutil.copy2(backup_path, artifact_path)

    def health(self) -> dict:
        return {
            "model_loaded": self.model is not None,
            "model_path": str(self.model_path),
            "preprocessors_path": str(self.preprocessors_path),
            "num_classes": self.num_classes,
        }

    def _build_model(self, input_dim: int):
        return build_model(input_dim, [
            self.num_classes[self.target_columns[0]],
            self.num_classes[self.target_columns[1]],
            self.num_classes[self.target_columns[2]],
        ])


_service = None


def get_service() -> PlanService:
    global _service
    if _service is None:
        _service = PlanService()
    return _service
