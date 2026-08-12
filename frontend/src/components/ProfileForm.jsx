import { useState } from 'react'
import { api } from '../api.js'
import { speak } from '../voice.js'

const OPTIONS = {
  Género: ['Femenino', 'Masculino'],
  'Nivel de Visión': ['Astigmatismo', 'Baja Visión', 'Ceguera Total', 'Glaucoma', 'Hipermetropía', 'Miopía', 'Retinopatía'],
  'Condición Física': ['Alta', 'Baja', 'Moderada'],
  'Condición Comórbida': ['Artritis', 'Diabetes Tipo 2', 'Ninguna', 'Obesidad Severa'],
  'Preferencia de Accesibilidad': ['Guías auditivas', 'Guías táctiles', 'Supervisión humana'],
  'Entorno de Ejercicio': ['Exterior', 'Gimnasio', 'Hogar'],
  Motivación: ['Alta', 'Baja', 'Moderada'],
}

const DEFAULTS = {
  Edad: 45,
  Género: 'Femenino',
  IMC: 27.0,
  'Nivel de Visión': 'Miopía',
  'Condición Física': 'Moderada',
  'Tiempo de Actividad Física': 30,
  'Condición Comórbida': 'Diabetes Tipo 2',
  'Preferencia de Accesibilidad': 'Guías auditivas',
  'Entorno de Ejercicio': 'Hogar',
  Motivación: 'Moderada',
}

const NUMERIC = {
  Edad: { min: 10, max: 120, step: 1, label: 'Edad' },
  IMC: { min: 10, max: 70, step: 0.1, label: 'Índice de masa corporal (IMC)' },
  'Tiempo de Actividad Física': { min: 0, max: 500, step: 1, label: 'Minutos de actividad física a la semana' },
}

const GROUPS = [
  { eyebrow: 'Tu ficha', fields: ['Edad', 'Género', 'IMC'] },
  { eyebrow: 'Tu visión y tu salud', fields: ['Nivel de Visión', 'Condición Física', 'Condición Comórbida'] },
  { eyebrow: 'Tu entorno', fields: ['Entorno de Ejercicio', 'Tiempo de Actividad Física'] },
  { eyebrow: 'Cómo te guías', fields: ['Preferencia de Accesibilidad', 'Motivación'] },
]

export default function ProfileForm({ onGenerated }) {
  const [form, setForm] = useState(() => ({ ...DEFAULTS }))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const setField = (field, value) => {
    setForm((f) => ({ ...f, [field]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const plan = await api.generatePlan(form)
      speak('Plan generado. Cuéntaselo a alguien de tu confianza para empezar, o revisa las fases en pantalla.')
      onGenerated(plan)
    } catch (err) {
      setError(String(err.message || err))
      speak('No se pudo generar tu plan. Revisa los datos e inténtalo de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <h1 className="hero-title">
          Tu plan de ejercicio,
          <br />
          hecho <em>para ti</em>
        </h1>
        <p className="hero-lede">
          Cuéntanos quién eres y te preparamos tres ejercicios seguros y adaptados a tu
          condición. Te guiamos con la voz paso a paso.
        </p>
      </section>

      <form className="form" onSubmit={handleSubmit}>
        {GROUPS.map((group) => (
          <fieldset className="form-group" key={group.eyebrow}>
            <legend className="form-eyebrow">{group.eyebrow}</legend>
            <div className="form-fields">
              {group.fields.map((field) =>
                NUMERIC[field] ? (
                  <label className="field" key={field}>
                    <span className="field-label">{NUMERIC[field].label}</span>
                    <input
                      className="field-input"
                      type="number"
                      min={NUMERIC[field].min}
                      max={NUMERIC[field].max}
                      step={NUMERIC[field].step}
                      value={form[field]}
                      onChange={(ev) => setField(field, ev.target.value === '' ? '' : Number(ev.target.value))}
                      required
                    />
                  </label>
                ) : (
                  <label className="field" key={field}>
                    <span className="field-label">{field}</span>
                    <select
                      className="field-input"
                      value={form[field]}
                      onChange={(ev) => setField(field, ev.target.value)}
                    >
                      {OPTIONS[field].map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  </label>
                ),
              )}
            </div>
          </fieldset>
        ))}

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <button className="btn btn--primary btn--block" type="submit" disabled={loading}>
          {loading ? 'Generando…' : 'Generar mi plan'}
        </button>
      </form>
    </main>
  )
}
