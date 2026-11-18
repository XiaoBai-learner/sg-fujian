import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import SessionGate from './app/SessionGate'
import './app/styles.css'
import './app/reference.css'

createRoot(document.getElementById('root')!).render(<StrictMode><SessionGate /></StrictMode>)
