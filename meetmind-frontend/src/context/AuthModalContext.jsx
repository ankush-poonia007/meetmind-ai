import { createContext, useContext, useState, useCallback } from 'react';

const AuthModalContext = createContext(null);

/**
 * AuthModalProvider — Context provider for the dedicated authentication window (Batch 4.6).
 *
 * Manages modal visibility and mode ('login' | 'signup') across the application.
 * Allows any entry point (Sidebar, Hero, CTA) to open the focused authentication window.
 */
export function AuthModalProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const [mode, setMode] = useState('login'); // 'login' | 'signup'

  const openAuthModal = useCallback((initialMode = 'login') => {
    const targetMode =
      initialMode === 'signup' || initialMode === 'register' ? 'signup' : 'login';
    setMode(targetMode);
    setIsOpen(true);
  }, []);

  const closeAuthModal = useCallback(() => {
    setIsOpen(false);
  }, []);

  return (
    <AuthModalContext.Provider
      value={{
        isOpen,
        mode,
        setMode,
        openAuthModal,
        closeAuthModal,
      }}
    >
      {children}
    </AuthModalContext.Provider>
  );
}

/**
 * Hook to access the authentication modal controller.
 */
export function useAuthModal() {
  const context = useContext(AuthModalContext);
  if (!context) {
    throw new Error('useAuthModal must be used within an AuthModalProvider');
  }
  return context;
}

export default AuthModalContext;
