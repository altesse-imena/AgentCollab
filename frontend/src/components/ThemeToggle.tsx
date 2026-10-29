import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../lib/useTheme'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const next = theme === 'dark' ? 'Light' : 'Dark'
  return (
    <button
      type="button"
      onClick={toggle}
      className="pill-outline px-3 py-2 text-sm"
      aria-label={`Switch to ${next.toLowerCase()} theme`}
    >
      {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      <span className="hidden sm:inline">{next}</span>
    </button>
  )
}
