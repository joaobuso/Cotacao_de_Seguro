import React from 'react'
import type { ReactNode } from 'react'
import Sidebar from './Sidebar'

interface Props {
  title: string
  subtitle?: string
  children: ReactNode
}

export default function Layout({ title, subtitle, children }: Props) {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <header className="bg-white border-b border-slate-200 px-8 py-5">
          <h2 className="text-2xl font-bold text-slate-900">{title}</h2>
          {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
        </header>
        <div className="p-8">{children}</div>
      </main>
    </div>
  )
}
