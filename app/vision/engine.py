import math


class SquatStateMachine:
    """Máquina de estados de sentadilla conducida por plantilla.

    Fases: ESPERANDO -> (calibración) -> DE_PIE -> BAJANDO -> SQUAT_PROFUNDO -> DE_PIE
    """

    def __init__(self, template: dict):
        self.template = template
        self.fase = "ESPERANDO"
        self.y_inicial = None
        self.repeticiones = 0

    @property
    def calibrado(self) -> bool:
        return self.y_inicial is not None

    def calibrate(self, y: float):
        self.y_inicial = y
        self.fase = "DE_PIE"
        self.repeticiones = 0

    def update(self, y_actual: float, postura_correcta: bool) -> dict:
        """Procesa un frame y devuelve el estado actual."""
        if not self.calibrado:
            return {
                "fase": self.fase,
                "desplazamiento_y": 0.0,
                "repeticiones": 0,
                "rep_valid": False,
            }

        desplazamiento_y = y_actual - self.y_inicial
        rep_valid = False
        tpl = self.template

        if self.fase == "DE_PIE":
            if desplazamiento_y > tpl["descenso_inicio_m"]:
                self.fase = "BAJANDO"
        elif self.fase == "BAJANDO":
            if desplazamiento_y >= tpl["profundidad_objetivo_m"]:
                self.fase = "SQUAT_PROFUNDO"
        elif self.fase == "SQUAT_PROFUNDO":
            if desplazamiento_y < tpl["subida_completa_m"]:
                if postura_correcta:
                    self.repeticiones += 1
                    rep_valid = True
                self.fase = "DE_PIE"

        return {
            "fase": self.fase,
            "desplazamiento_y": round(desplazamiento_y, 3),
            "repeticiones": self.repeticiones,
            "rep_valid": rep_valid,
        }


def shoulder_angle(p_izq, p_der) -> float:
    """Ángulo de nivelación de hombros en grados (0 = nivelados)."""
    vector = p_der - p_izq
    return math.degrees(math.atan2(vector[1], vector[0]))
