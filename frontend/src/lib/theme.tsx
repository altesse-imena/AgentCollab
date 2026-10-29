import { type ReactNode, useCallback, useState } from 'react'
import { type Theme, ThemeContext } from './useTheme'

// index.html applies the saved theme before the first paint; this keeps React in sync with it
const STORAGE_KEY = 'agentcollab-theme'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.classList.contains('dark') ? 'dark' : 'light',
  )

  const toggle = useCallback(() => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    const root = document.documentElement
    root.classList.add('theme-transition')
    root.classList.toggle('dark', next === 'dark')
    setTimeout(() => root.classList.remove('theme-transition'), 400)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // storage can be blocked (private mode); the theme still applies for this visit
    }
    setTheme(next)
  }, [theme])

  return <ThemeContext value={{ theme, toggle }}>{children}</ThemeContext>
}
