# 📊 Dataset

## 1. Generalidades

- **Fuente:** `data/Datos generados con modelo.xlsx`
- **Formato:** Excel (OpenPyXL / pandas `read_excel`)
- **Registros:** 517 filas en `Hoja1` → **512 filas válidas** tras el preprocesamiento
- **Origen:** datos **sintéticos** generados con un modelo de datos (proyecto académico)

> 📝 El Excel contiene varias hojas. El backend solo usa `Hoja1` (la hoja por defecto de `pd.read_excel`).

## 2. Variables

### 2.1 Entradas (features)

| Variable | Tipo | Ejemplo |
|----------|------|---------|
| `Edad` | numérica | 51 |
| `Género` | categórica | Femenino |
| `IMC` | numérica | 27.4 |
| `Nivel de Visión` | categórica | Hipermetropía |
| `Condición Física` | categórica | Moderada |
| `Tiempo de Actividad Física` | numérica | 30 (min/semana) |
| `Condición Comórbida` | categórica | Diabetes Tipo 2 |
| `Preferencia de Accesibilidad` | categórica | Guías auditivas |
| `Entorno de Ejercicio` | categórica | Gimnasio |
| `Motivación` | categórica | Moderada |

### 2.2 Salidas (targets)

| Variable | Fase | Nº clases |
|----------|------|-----------|
| `Ejercicios Fase 1 de Calentamiento` | Calentamiento | 9 |
| `Ejercicios Fase 2 de Entrenamiento` | Entrenamiento | 9 |
| `Ejercicios Fase 3 de Enfriamiento` | Enfriamiento | 7 |

## 3. Catálogo de ejercicios (25 únicos)

### Calentamiento (9)

1. Balanceo de brazos
2. Balanceo de brazos cruzado
3. Círculos con los tobillos (sentado o de pie)
4. Elevación de rodillas alternadas
5. Marcha en el lugar con cuerda guía
6. Movimientos de brazos en forma de "alas"
7. Paso lateral con toque en piso
8. Respiraciones profundas con movilidad de brazos
9. Rotaciones articulares suaves

### Entrenamiento (9)

1. (Equilibrio y Coordinación) Caminar en línea recta guiada voz/cuerda
2. (Equilibrio y Coordinación) Postura de árbol adaptada
3. (Fuerza y Resistencia) Elevaciones de talones con apoyo
4. (Fuerza y Resistencia) Extensión de pierna sentado
5. (Fuerza y Resistencia) Flexiones en pared
6. (Fuerza y Resistencia) Press de hombros con botellas de agua
7. (Fuerza y Resistencia) Remo con banda elástica/toalla
8. (Fuerza y Resistencia) Sentadillas asistidas con silla/barra
9. (Fuerza y resistencia) Puente de glúteos

### Enfriamiento (7)

1. Estiramiento de brazos cruzados sobre el pecho
2. Estiramiento de cuello guiíado
3. Estiramiento de espalda baja
4. Estiramientos estáticos (cuádriceps)
5. Estiramientos estáticos (isquiotibiales)
6. Movilidad suave (balanceo de brazos)
7. Respiraciones profundas

## 4. Distribución de valores categóricos

| `Nivel de Visión` | N | `Condición Física` | N | `Condición Comórbida` | N |
|---|---|---|---|---|---|
| Miopía | 117 | Moderada | 204 | Diabetes Tipo 2 | 199 |
| Astigmatismo | 109 | Baja | 191 | Ninguna | 162 |
| Retinopatía | 76 | Alta | 117 | Artritis | 94 |
| Ceguera Total | 71 | | | Obesidad Severa | 57 |
| Hipermetropía | 52 | | | | |
| Baja Visión | 47 | | | | |
| Glaucoma | 40 | | | | |

| `Preferencia de Accesibilidad` | N | `Entorno de Ejercicio` | N | `Motivación` | N |
|---|---|---|---|---|---|
| Guías auditivas | 200 | Hogar | 260 | Moderada | 193 |
| Guías táctiles | 168 | Gimnasio | 156 | Alta | 168 |
| Supervisión humana | 144 | Exterior | 96 | Baja | 151 |

| `Género` | N |
|---|---|
| Femenino | 328 |
| Masculino | 184 |

## 5. Notas de calidad

- El dataset es **sintético**, por lo que la precisión del modelo debe interpretarse en ese contexto (proyecto de investigación).
- Algunas etiquetas tienen **errores tipográficos** heredados del Excel (p. ej. `"Estiramiento de cuello guiíado"`, `"(Fuerza y resistencia) Puente de glúteos"`). El sistema los trata como clases distintas.
- Existen **clases minoritarias** (con 1 ejemplo); el entrenamiento las reintroduce al conjunto de entrenamiento para evitar pérdida de representación.
