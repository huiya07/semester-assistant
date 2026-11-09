import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
// CDS 设计令牌（来自 open-claude-ui，MIT）先加载，index.css 再覆盖成本项目配色
import './styles/cds-theme.css'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
