import React from 'react'
import { Router, Route, Switch, Redirect } from 'wouter'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Conversations from './pages/Conversations'
import ConversationDetail from './pages/ConversationDetail'
import Quotations from './pages/Quotations'
import FaqManager from './pages/FaqManager'

function PrivateRoute({ component: Component }: { component: React.ComponentType }) {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4" />
          <p className="text-slate-600">Carregando...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Redirect to="/login" />
  }

  return <Component />
}

function AppRoutes() {
  return (
    <Router base="/portal">
      <Switch>
        <Route path="/login" component={Login} />
        <Route path="/dashboard">
          <PrivateRoute component={Dashboard} />
        </Route>
        <Route path="/conversations">
          <PrivateRoute component={Conversations} />
        </Route>
        <Route path="/conversations/:phone">
          {(params: { phone: string }) => (
            <PrivateRoute component={() => <ConversationDetail phone={decodeURIComponent(params.phone)} />} />
          )}
        </Route>
        <Route path="/quotations">
          <PrivateRoute component={Quotations} />
        </Route>
        <Route path="/faq">
          <PrivateRoute component={FaqManager} />
        </Route>
        <Route path="/">
          <Redirect to="/dashboard" />
        </Route>
      </Switch>
    </Router>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
