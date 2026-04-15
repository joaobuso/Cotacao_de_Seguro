import React from 'react'
import { useLocation, Link } from 'wouter'
import { useAuth } from '../contexts/AuthContext'
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  HelpCircle,
  LogOut,
  Shield,
  User
} from 'lucide-react'

const navItems = [
  { path: '/portal/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/portal/conversations', label: 'Conversas', icon: MessageSquare },
  { path: '/portal/quotations', label: 'Cotações', icon: FileText },
  { path: '/portal/faq', label: 'FAQ / Temas', icon: HelpCircle },
]

export default function Sidebar() {
  const [location] = useLocation()
  const { user, logout } = useAuth()

  return (
    <aside className="w-64 bg-slate-900 text-white min-h-screen flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-green-500 rounded-lg flex items-center justify-center text-xl font-bold">
            ES
          </div>
          <div>
            <h1 className="text-lg font-bold">Equinos Seguros</h1>
            <p className="text-xs text-slate-400">Portal do Agente</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = location.startsWith(item.path)
          const Icon = item.icon
          return (
            <Link key={item.path} href={item.path}>
              <div
                className={`flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-all ${
                  isActive
                    ? 'bg-primary-600 text-white shadow-lg'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon size={20} />
                <span className="font-medium">{item.label}</span>
              </div>
            </Link>
          )
        })}
      </nav>

      {/* User Info */}
      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center gap-3 mb-3 px-2">
          <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center">
            <User size={16} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.name || 'Agente'}</p>
            <p className="text-xs text-slate-400 truncate">{user?.email}</p>
          </div>
          {user?.role === 'admin' && (
            <Shield size={14} className="text-yellow-400 flex-shrink-0" />
          )}
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-4 py-2 text-sm text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-all"
        >
          <LogOut size={16} />
          <span>Sair</span>
        </button>
      </div>
    </aside>
  )
}
