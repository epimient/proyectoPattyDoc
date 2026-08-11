import cv2
import numpy as np
from pupil_apriltags import Detector
import math

# Inicialización
cap = cv2.VideoCapture(0)
detector = Detector(families='tag36h11')
tag_size = 0.05 
camera_params = [600.0, 600.0, 320.0, 240.0] 

ID_HOMBRO_IZQ = 0
ID_HOMBRO_DER = 1

# --- VARIABLES PARA EL TRACKEO DINÁMICO ---
y_inicial = None          # Altura de referencia al estar de pie
fase_ejercicio = "ESPERANDO" # Estados: ESPERANDO, BAJANDO, SUBIENDO
repeticiones = 0
profundidad_objetivo = 0.35  # Metros que debes bajar para que cuente (ajustable)
desplazamiento_y = 0.0
postura_correcta = True

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    results = detector.detect(gray, estimate_tag_pose=True, camera_params=camera_params, tag_size=tag_size)

    posiciones_3d = {}
    centros_2d = {}

    for r in results:
        t = r.pose_t
        if t is not None:
            posiciones_3d[r.tag_id] = np.array([t[0][0], t[1][0], t[2][0]])
            centros_2d[r.tag_id] = (int(r.center[0]), int(r.center[1]))
            
            # Dibujar contornos
            (ptA, ptB, ptC, ptD) = r.corners
            cv2.polylines(frame, [np.int32([ptA, ptB, ptC, ptD])], True, (255, 0, 0), 2)

    # Lógica biomecánica si ambos hombros son visibles
    if ID_HOMBRO_IZQ in posiciones_3d and ID_HOMBRO_DER in posiciones_3d:
        p_izq = posiciones_3d[ID_HOMBRO_IZQ]
        p_der = posiciones_3d[ID_HOMBRO_DER]
        
        # 1. Punto medio de los hombros (Torso superior)
        punto_medio_3d = (p_izq + p_der) / 2.0
        punto_medio_2d = (
            int((centros_2d[ID_HOMBRO_IZQ][0] + centros_2d[ID_HOMBRO_DER][0]) / 2),
            int((centros_2d[ID_HOMBRO_IZQ][1] + centros_2d[ID_HOMBRO_DER][1]) / 2)
        )
        cv2.circle(frame, punto_medio_2d, 8, (0, 255, 255), -1) # Dibujar el centro

        # 2. Evaluar nivelación de hombros (Tolerancia de 10 grados)
        vector_hombros = p_der - p_izq
        angulo_grados = math.degrees(math.atan2(vector_hombros[1], vector_hombros[0]))
        postura_correcta = abs(angulo_grados) < 10.0

        # 3. Máquina de estados para la Sentadilla
        if y_inicial is not None:
            # En OpenCV, el eje Y crece hacia ABAJO. 
            # Por lo tanto, (Y_actual - Y_inicial) nos da un valor positivo al agacharnos.
            desplazamiento_y = punto_medio_3d[1] - y_inicial
            
            if fase_ejercicio == "DE_PIE":
                if desplazamiento_y > 0.1: # Si bajaste 10cm, empiezas a hacer la sentadilla
                    fase_ejercicio = "BAJANDO"
            
            elif fase_ejercicio == "BAJANDO":
                if desplazamiento_y >= profundidad_objetivo: # Llegaste a la profundidad correcta
                    fase_ejercicio = "SQUAT_PROFUNDO"
            
            elif fase_ejercicio == "SQUAT_PROFUNDO":
                if desplazamiento_y < 0.15: # Estás subiendo y casi de pie
                    # Evaluamos si la repetición es válida
                    if postura_correcta:
                        repeticiones += 1
                        fase_ejercicio = "DE_PIE"
                    else:
                        # Si subió con la espalda chueca, no cuenta
                        fase_ejercicio = "DE_PIE"

        # --- PANTALLA Y DATOS ---
        color_estado = (0, 255, 0) if postura_correcta else (0, 0, 255)
        cv2.putText(frame, f"Fase: {fase_ejercicio}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, f"Descenso: {desplazamiento_y:.2f}m", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Repeticiones: {repeticiones}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"Postura: {'OK' if postura_correcta else 'MALA'}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_estado, 2)

    else:
        cv2.putText(frame, "HOMBROS NO VISIBLES", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Instrucciones en pantalla
    if y_inicial is None:
        cv2.putText(frame, "Ponte de pie recto y presiona 'c' para calibrar", (20, frame.shape[0] - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    cv2.imshow("Trackeo de Sentadilla", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'): # Tecla para calibrar la altura inicial
        if ID_HOMBRO_IZQ in posiciones_3d and ID_HOMBRO_DER in posiciones_3d:
            punto_medio_3d = (posiciones_3d[ID_HOMBRO_IZQ] + posiciones_3d[ID_HOMBRO_DER]) / 2.0
            y_inicial = punto_medio_3d[1]
            fase_ejercicio = "DE_PIE"
            print("¡Altura calibrada!")

cap.release()
cv2.destroyAllWindows()