import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X } from 'lucide-react';
import { useAuthModal } from '../../context/AuthModalContext';
import AuthWindow from './AuthWindow';

/**
 * AuthModal — Dedicated Authentication Window Modal Dialog (Batch 4.6 Correction).
 *
 * Opens when an unauthenticated user attempts to enter the Workspace.
 * Presents a focused window with selectable Login and Sign Up options.
 */
function AuthModal() {
  const { isOpen, mode, setMode, closeAuthModal } = useAuthModal();
  const navigate = useNavigate();

  // Handle escape key & background scroll lock
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        closeAuthModal();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [isOpen, closeAuthModal]);

  if (!isOpen) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      closeAuthModal();
    }
  };

  const handleSuccess = (destination) => {
    closeAuthModal();
    const target = destination || '/workspace/dashboard';
    navigate(target, { replace: true });
  };

  return (
    <div
      className="auth-modal-backdrop"
      onClick={handleBackdropClick}
      role="presentation"
    >
      <div
        className="auth-modal-container"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-window-heading"
      >
        <button
          type="button"
          className="auth-modal-close-btn"
          onClick={closeAuthModal}
          aria-label="Close authentication window"
          title="Close (Esc)"
        >
          <X size={18} aria-hidden="true" />
        </button>

        <AuthWindow
          initialMode={mode}
          onModeChange={setMode}
          isModal={true}
          onClose={closeAuthModal}
          onSuccess={handleSuccess}
        />
      </div>
    </div>
  );
}

export default AuthModal;
