import { useState } from 'react'
import ProfileForm from './components/ProfileForm.jsx'
import PlanSummary from './components/PlanSummary.jsx'
import SessionView from './components/SessionView.jsx'

export default function App() {
  const [screen, setScreen] = useState('profile')
  const [plan, setPlan] = useState(null)
  const [sessionPlan, setSessionPlan] = useState(null)

  return (
    <div className="app">
      <header className="wordmark">
        <span className="wordmark-mark" aria-hidden="true">
          ◉
        </span>
        <span className="wordmark-name">PATTYDOC</span>
        <span className="wordmark-tag">tu plan de ejercicio, hecho para ti</span>
      </header>

      {screen === 'profile' && (
        <ProfileForm onGenerated={(p) => { setPlan(p); setSessionPlan(null); setScreen('plan') }} />
      )}

      {screen === 'plan' && (
        <PlanSummary
          plan={plan}
          onBack={() => setScreen('profile')}
          onStart={(selectedPlan) => { setSessionPlan(selectedPlan); setScreen('session') }}
        />
      )}

      {screen === 'session' && (
        <SessionView plan={sessionPlan || plan} onExit={() => setScreen('plan')} />
      )}
    </div>
  )
}
