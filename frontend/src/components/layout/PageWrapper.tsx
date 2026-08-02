import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import Sidebar from './Sidebar'
import Header from './Header'

export default function PageWrapper({ children }: { children: React.ReactNode }) {
  const { token, user, loadUser } = useAuthStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    if (token && !user) {
      loadUser()
    }
  }, [token, user, loadUser])

  // Close the mobile drawer on navigation so it never covers the new page.
  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  // Lock body scroll while the mobile drawer is open.
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [menuOpen])

  return (
    <div className="min-h-screen">
      {/* Ambient gradient mesh behind everything */}
      <div className="app-mesh" />

      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />

      {/* Content is only offset by the sidebar from lg up — below that the
          sidebar is an overlay drawer, so the content must span full width. */}
      <div className="lg:pl-[17rem]">
        <Header onMenuClick={() => setMenuOpen(true)} />
        <main className="p-4 sm:p-6 max-w-[1600px] mx-auto animate-fade-up">{children}</main>
      </div>
    </div>
  )
}
