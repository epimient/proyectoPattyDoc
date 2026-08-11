import joblib

from app.core.config import PREPROCESSORS_PATH
from app.models.preprocessing import (
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    CATEGORICAL_COLUMNS,
)


def build_artifacts(df, le_dict, target_encoders, scaler, num_classes, categorical_defaults):
    return {
        "df_encoded": df,
        "feature_columns": FEATURE_COLUMNS,
        "target_columns": TARGET_COLUMNS,
        "categorical_columns": CATEGORICAL_COLUMNS,
        "le_dict": le_dict,
        "target_encoders": target_encoders,
        "scaler": scaler,
        "num_classes": num_classes,
        "categorical_defaults": categorical_defaults,
    }


def save_artifacts(payload, path=PREPROCESSORS_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, path)
    print(f"Preprocesadores guardados en {path}")


def load_artifacts(path=PREPROCESSORS_PATH):
    return joblib.load(path)
