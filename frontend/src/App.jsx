import React, { useState } from 'react'
import Intro from './pages/Intro';
import { Routes, Route, Navigate } from 'react-router-dom';
import Chat from './pages/Chat';
import AuthPage from './pages/AuthPage';
import { useAuth } from './context/AuthContext';

const App = () => {

  const { isAuthenticated } = useAuth();
  return (
    <div>
      <Routes>
        <Route path="/" element={<Intro />} />

        <Route path='/chat/:sessionId?' element={<Chat />} />

        <Route
          path="/auth/login"
          element={
            isAuthenticated
              ? <Navigate to="/chat" replace />
              : <AuthPage />
          }
        />

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />

      </Routes>
    </div>
  )
}

export default App