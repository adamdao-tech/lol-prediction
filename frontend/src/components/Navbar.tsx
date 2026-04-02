import { Link, useLocation, useNavigate } from 'react-router-dom'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()

  const navLinks = [
    { to: '/', label: 'Dashboard' },
    { to: '/admin', label: 'Admin' },
  ]

  const handleLogout = () => {
    localStorage.removeItem('lol_username')
    localStorage.removeItem('lol_password')
    navigate('/login')
  }

  return (
    <nav className="bg-gray-900 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-8">
        <Link to="/" className="text-xl font-bold text-yellow-400 hover:text-yellow-300 transition-colors">
          ⚔️ LoL Predictor
        </Link>
        <div className="flex gap-4">
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`text-sm font-medium transition-colors px-3 py-1 rounded ${
                location.pathname === link.to
                  ? 'bg-yellow-400 text-gray-900'
                  : 'text-gray-300 hover:text-white hover:bg-gray-700'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
        <button
          onClick={handleLogout}
          className="ml-auto text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700 px-3 py-1 rounded transition-colors"
        >
          Odhlásit
        </button>
      </div>
    </nav>
  )
}
