import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import '@wing/styles.css'
import '@wing/product/product.css'
import '@wing/product/workbench-frame.css'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
