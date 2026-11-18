import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import SessionGate from './app/SessionGate'
import './app/styles.css'

createRoot(document.getElementById('root')!).render(<StrictMode><SessionGate /></StrictMode>)
