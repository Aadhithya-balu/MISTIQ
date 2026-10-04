import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/index.css'
import { StudentProvider } from './context/StudentContext'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><BrowserRouter><StudentProvider><App /></StudentProvider></BrowserRouter></React.StrictMode>,
)
