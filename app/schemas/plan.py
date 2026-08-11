from pydantic import BaseModel, ConfigDict, Field


class UserProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    edad: int = Field(ge=10, le=120, alias="Edad")
    genero: str = Field(alias="Género")
    imc: float = Field(ge=10, le=70, alias="IMC")
    nivel_vision: str = Field(alias="Nivel de Visión")
    condicion_fisica: str = Field(alias="Condición Física")
    tiempo_actividad_fisica: float = Field(ge=0, le=500, alias="Tiempo de Actividad Física")
    condicion_comorbida: str = Field(alias="Condición Comórbida")
    preferencia_accesibilidad: str = Field(alias="Preferencia de Accesibilidad")
    entorno_ejercicio: str = Field(alias="Entorno de Ejercicio")
    motivacion: str = Field(alias="Motivación")

    def to_features(self) -> dict:
        return {
            "Edad": self.edad,
            "Género": self.genero,
            "IMC": self.imc,
            "Nivel de Visión": self.nivel_vision,
            "Condición Física": self.condicion_fisica,
            "Tiempo de Actividad Física": self.tiempo_actividad_fisica,
            "Condición Comórbida": self.condicion_comorbida,
            "Preferencia de Accesibilidad": self.preferencia_accesibilidad,
            "Entorno de Ejercicio": self.entorno_ejercicio,
            "Motivación": self.motivacion,
        }


class PlanResponse(BaseModel):
    calentamiento: str
    entrenamiento: str
    enfriamiento: str


class CorrectedExercises(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    calentamiento: str = Field(alias="Calentamiento")
    entrenamiento: str = Field(alias="Entrenamiento")
    enfriamiento: str = Field(alias="Enfriamiento")


class FeedbackRequest(BaseModel):
    input_data: UserProfile
    corrected_exercises: CorrectedExercises
    suitable: bool


class FeedbackResponse(BaseModel):
    status: str
    retrained: bool
    message: str
