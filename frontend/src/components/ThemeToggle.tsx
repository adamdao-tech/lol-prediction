import { useTheme } from '../contexts/ThemeContext'

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      className="ml-2 px-2 py-1 rounded-md text-lg hover:bg-gray-700 transition-colors"
      aria-label="Toggle dark/light mode"
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  )
}
