import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import MatchDetail from './pages/MatchDetail'

function AdminStub() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Admin</h1>
      <p className="text-gray-600">Admin panel — coming soon. Use the API directly at <code className="bg-gray-100 px-1 rounded">/api/admin/*</code></p>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/matches/:id" element={<MatchDetail />} />
            <Route path="/admin" element={<AdminStub />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
