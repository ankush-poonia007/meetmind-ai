import { useState, useMemo, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, AlertCircle, Check } from 'lucide-react';
import {
  validateEmail,
  validatePassword,
  validateName,
  validateMobileNumber,
} from '../../utils/authValidation';
import { useAuth } from '../../hooks/useAuth';

/**
 * AuthWindow — Focused Authentication Window Component (Batch 4.6 Correction).
 *
 * Provides a dedicated, focused authentication experience with two selectable options:
 * 1. Login (selected and displayed by default)
 * 2. Sign Up (replaces the Login form with the complete Registration form)
 *
 * Features:
 * - Tab-based switcher between Login and Sign Up within the same window.
 * - Occupies the full focused content area for the active form (never displays both).
 * - Complete validation, error presentation, and API integration for both flows.
 * - Seamless integration with existing authentication state and session persistence.
 */
function AuthWindow({
  initialMode = 'login',
  onModeChange,
  isModal = false,
  onClose,
  onSuccess,
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, register, loading } = useAuth();

  const getDestination = () => {
    const rawTarget =
      location.state?.from?.pathname ||
      (location.state?.from ? String(location.state.from) : null);
    const search = location.state?.from?.search || '';
    if (rawTarget && rawTarget.startsWith('/') && !rawTarget.startsWith('//')) {
      return rawTarget + search;
    }
    return '/workspace/dashboard';
  };

  const [activeTab, setActiveTab] = useState(
    initialMode === 'signup' || initialMode === 'register' ? 'signup' : 'login'
  );

  // Sync if initialMode changes externally
  useEffect(() => {
    const target = initialMode === 'signup' || initialMode === 'register' ? 'signup' : 'login';
    setActiveTab(target);
  }, [initialMode]);

  const handleTabSwitch = (tab) => {
    setActiveTab(tab);
    onModeChange?.(tab);
  };

  /* ══════════════════════════════════════════════════════════════════════════
     LOGIN FORM STATE & HANDLERS
     ══════════════════════════════════════════════════════════════════════════ */
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginErrors, setLoginErrors] = useState({});
  const [loginServerError, setLoginServerError] = useState(null);

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    if (loading) return; // Prevent duplicate submissions

    setLoginServerError(null);

    const fieldErrors = {};
    const emailResult = validateEmail(loginEmail);
    if (!emailResult.isValid) {
      fieldErrors.email = emailResult.message;
    }
    if (!loginPassword) {
      fieldErrors.password = 'Password is required.';
    }

    if (Object.keys(fieldErrors).length > 0) {
      setLoginErrors(fieldErrors);
      return;
    }

    setLoginErrors({});

    try {
      await login({
        email: loginEmail.trim(),
        password: loginPassword,
      });

      setLoginPassword('');
      const destination = getDestination();
      if (onSuccess) {
        onSuccess(destination);
      } else {
        navigate(destination, { replace: true });
      }
    } catch (err) {
      // Clear password field for security, preserve email
      setLoginPassword('');
      const apiMessage =
        err?.response?.data?.message || err?.message || 'Invalid email or password.';
      setLoginServerError(apiMessage);
    }
  };

  const handleLoginEmailChange = (e) => {
    const val = e.target.value;
    setLoginEmail(val);
    if (loginErrors.email) {
      const res = validateEmail(val);
      if (res.isValid) {
        setLoginErrors((prev) => ({ ...prev, email: undefined }));
      }
    }
    if (loginServerError) setLoginServerError(null);
  };

  const handleLoginPasswordChange = (e) => {
    const val = e.target.value;
    setLoginPassword(val);
    if (loginErrors.password && val) {
      setLoginErrors((prev) => ({ ...prev, password: undefined }));
    }
    if (loginServerError) setLoginServerError(null);
  };

  /* ══════════════════════════════════════════════════════════════════════════
     REGISTRATION FORM STATE & HANDLERS
     ══════════════════════════════════════════════════════════════════════════ */
  const [regData, setRegData] = useState({
    firstName: '',
    lastName: '',
    mobileNumber: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [regErrors, setRegErrors] = useState({});
  const [regServerError, setRegServerError] = useState(null);
  const [passwordTouched, setPasswordTouched] = useState(false);

  // Live password validation
  const passwordStatus = useMemo(
    () => validatePassword(regData.password),
    [regData.password]
  );

  // Live confirm password matching
  const passwordMatchStatus = useMemo(() => {
    if (!regData.confirmPassword) {
      return { checked: false, matches: false };
    }
    return {
      checked: true,
      matches: regData.password === regData.confirmPassword,
    };
  }, [regData.password, regData.confirmPassword]);

  const handleRegChange = (field) => (e) => {
    const value = e.target.value;
    setRegData((prev) => ({ ...prev, [field]: value }));

    if (field === 'password') {
      setPasswordTouched(true);
    }

    if (regErrors[field]) {
      setRegErrors((prev) => ({ ...prev, [field]: undefined }));
    }
    if (regServerError) {
      setRegServerError(null);
    }
  };

  const handleRegSubmit = async (e) => {
    e.preventDefault();
    if (loading) return; // Prevent duplicate submissions

    setRegServerError(null);

    const fieldErrors = {};

    const fnResult = validateName(regData.firstName, 'First name');
    if (!fnResult.isValid) fieldErrors.firstName = fnResult.message;

    const lnResult = validateName(regData.lastName, 'Last name');
    if (!lnResult.isValid) fieldErrors.lastName = lnResult.message;

    const mobileResult = validateMobileNumber(regData.mobileNumber);
    if (!mobileResult.isValid) fieldErrors.mobileNumber = mobileResult.message;

    const emailResult = validateEmail(regData.email);
    if (!emailResult.isValid) fieldErrors.email = emailResult.message;

    if (!passwordStatus.isValid) {
      fieldErrors.password =
        passwordStatus.message || 'Password does not meet complexity requirements.';
    }

    if (!regData.confirmPassword) {
      fieldErrors.confirmPassword = 'Confirm password is required.';
    } else if (regData.password !== regData.confirmPassword) {
      fieldErrors.confirmPassword = 'Passwords do not match.';
    }

    if (Object.keys(fieldErrors).length > 0) {
      setRegErrors(fieldErrors);
      setPasswordTouched(true);
      return;
    }

    setRegErrors({});

    try {
      const payload = {
        first_name: regData.firstName.trim(),
        last_name: regData.lastName.trim(),
        email: regData.email.trim(),
        password: regData.password,
        confirm_password: regData.confirmPassword,
      };

      if (regData.mobileNumber.trim()) {
        payload.mobile_number = regData.mobileNumber.trim();
      }

      await register(payload);

      const destination = getDestination();
      if (onSuccess) {
        onSuccess(destination);
      } else {
        navigate(destination, { replace: true });
      }
    } catch (err) {
      const apiMessage =
        err?.response?.data?.message ||
        err?.message ||
        'Registration failed. Please check your information.';
      setRegServerError(apiMessage);

      if (apiMessage.toLowerCase().includes('already exists') || err?.response?.status === 409) {
        setRegErrors((prev) => ({
          ...prev,
          email: 'An account with this email address already exists.',
        }));
      }
    }
  };

  return (
    <div className={`auth-card ${activeTab === 'signup' ? 'auth-card-wide' : ''}`}>
      {/* ── Brand & Window Header ───────────────────────────────────── */}
      <div className="auth-header">
        <div className="auth-brand-badge" aria-label="MeetMind">
          <svg
            width="18"
            height="18"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <rect width="32" height="32" rx="8" fill="var(--color-accent-primary)" />
            <path
              d="M6 8C6 6.895 6.895 6 8 6H16C17.105 6 18 6.895 18 8V16C18 17.105 17.105 18 16 18H10L6 22V8Z"
              fill="white"
              opacity="0.95"
            />
            <path
              d="M14 12C14 10.895 14.895 10 16 10H24C25.105 10 26 10.895 26 12V20C26 21.105 25.105 22 24 22H22L18 26V12Z"
              fill="white"
              opacity="0.7"
            />
          </svg>
          <span>MeetMind</span>
        </div>

        <h2 className="auth-title" id="auth-window-heading">
          {activeTab === 'login' ? 'Welcome back' : 'Create your account'}
        </h2>
        <p className="auth-subtitle">
          {activeTab === 'login'
            ? 'Enter your credentials to access your meeting assistant and workspace.'
            : 'Get started with AI-driven meeting understanding and task management.'}
        </p>
      </div>

      {/* ── Selectable Options: Login & Sign Up Tabs ─────────────────── */}
      <div className="auth-tabs" role="tablist" aria-label="Authentication Options">
        <button
          type="button"
          role="tab"
          id="auth-tab-login"
          aria-selected={activeTab === 'login'}
          aria-controls="auth-panel-login"
          className={`auth-tab ${activeTab === 'login' ? 'active' : ''}`}
          onClick={() => handleTabSwitch('login')}
        >
          Login
        </button>
        <button
          type="button"
          role="tab"
          id="auth-tab-signup"
          aria-selected={activeTab === 'signup'}
          aria-controls="auth-panel-signup"
          className={`auth-tab ${activeTab === 'signup' ? 'active' : ''}`}
          onClick={() => handleTabSwitch('signup')}
        >
          Sign Up
        </button>
      </div>

      {/* ── Focused Content Area: Only Active Form Rendered ─────────── */}
      {activeTab === 'login' ? (
        <div
          id="auth-panel-login"
          role="tabpanel"
          aria-labelledby="auth-tab-login"
          className="auth-panel"
        >
          {/* Server Error Alert */}
          {loginServerError && (
            <div className="auth-alert" role="alert" aria-live="assertive">
              <AlertCircle size={18} className="auth-alert-icon" aria-hidden="true" />
              <span>{loginServerError}</span>
            </div>
          )}

          <form onSubmit={handleLoginSubmit} className="auth-form" noValidate>
            {/* Email Field */}
            <div className="form-group">
              <label htmlFor="auth-login-email" className="form-label">
                Email address
              </label>
              <input
                id="auth-login-email"
                type="email"
                autoComplete="email"
                autoFocus
                disabled={loading}
                value={loginEmail}
                onChange={handleLoginEmailChange}
                placeholder="you@example.com"
                className={`form-input ${loginErrors.email ? 'has-error' : ''}`}
                aria-invalid={Boolean(loginErrors.email)}
                aria-describedby={loginErrors.email ? 'login-email-error' : undefined}
              />
              {loginErrors.email && (
                <span id="login-email-error" className="form-field-error" role="alert">
                  {loginErrors.email}
                </span>
              )}
            </div>

            {/* Password Field */}
            <div className="form-group">
              <label htmlFor="auth-login-password" className="form-label">
                Password
              </label>
              <div className="password-input-wrapper">
                <input
                  id="auth-login-password"
                  type={showLoginPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  disabled={loading}
                  value={loginPassword}
                  onChange={handleLoginPasswordChange}
                  placeholder="Enter your password"
                  className={`form-input ${loginErrors.password ? 'has-error' : ''}`}
                  aria-invalid={Boolean(loginErrors.password)}
                  aria-describedby={loginErrors.password ? 'login-password-error' : undefined}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowLoginPassword((prev) => !prev)}
                  aria-label={showLoginPassword ? 'Hide password' : 'Show password'}
                  title={showLoginPassword ? 'Hide password' : 'Show password'}
                  tabIndex={0}
                >
                  {showLoginPassword ? (
                    <EyeOff size={16} aria-hidden="true" />
                  ) : (
                    <Eye size={16} aria-hidden="true" />
                  )}
                </button>
              </div>
              {loginErrors.password && (
                <span id="login-password-error" className="form-field-error" role="alert">
                  {loginErrors.password}
                </span>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary auth-submit-btn"
              aria-busy={loading}
            >
              {loading ? (
                <>
                  <span className="auth-spinner" aria-hidden="true" />
                  <span>Signing in...</span>
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Footer Switching Prompt */}
          <div className="auth-footer">
            <p className="auth-switch-prompt">
              Don&apos;t have an account?{' '}
              <button
                type="button"
                className="auth-switch-btn"
                onClick={() => handleTabSwitch('signup')}
              >
                Sign Up
              </button>
            </p>
          </div>
        </div>
      ) : (
        <div
          id="auth-panel-signup"
          role="tabpanel"
          aria-labelledby="auth-tab-signup"
          className="auth-panel"
        >
          {/* Server Error Alert */}
          {regServerError && (
            <div className="auth-alert" role="alert" aria-live="assertive">
              <AlertCircle size={18} className="auth-alert-icon" aria-hidden="true" />
              <span>{regServerError}</span>
            </div>
          )}

          <form onSubmit={handleRegSubmit} className="auth-form" noValidate>
            {/* First & Last Name Row */}
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="auth-reg-first-name" className="form-label">
                  First name
                </label>
                <input
                  id="auth-reg-first-name"
                  type="text"
                  autoComplete="given-name"
                  autoFocus
                  disabled={loading}
                  value={regData.firstName}
                  onChange={handleRegChange('firstName')}
                  placeholder="Jane"
                  className={`form-input ${regErrors.firstName ? 'has-error' : ''}`}
                  aria-invalid={Boolean(regErrors.firstName)}
                  aria-describedby={regErrors.firstName ? 'reg-fn-error' : undefined}
                />
                {regErrors.firstName && (
                  <span id="reg-fn-error" className="form-field-error" role="alert">
                    {regErrors.firstName}
                  </span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="auth-reg-last-name" className="form-label">
                  Last name
                </label>
                <input
                  id="auth-reg-last-name"
                  type="text"
                  autoComplete="family-name"
                  disabled={loading}
                  value={regData.lastName}
                  onChange={handleRegChange('lastName')}
                  placeholder="Doe"
                  className={`form-input ${regErrors.lastName ? 'has-error' : ''}`}
                  aria-invalid={Boolean(regErrors.lastName)}
                  aria-describedby={regErrors.lastName ? 'reg-ln-error' : undefined}
                />
                {regErrors.lastName && (
                  <span id="reg-ln-error" className="form-field-error" role="alert">
                    {regErrors.lastName}
                  </span>
                )}
              </div>
            </div>

            {/* Email Address */}
            <div className="form-group">
              <label htmlFor="auth-reg-email" className="form-label">
                Email address
              </label>
              <input
                id="auth-reg-email"
                type="email"
                autoComplete="email"
                disabled={loading}
                value={regData.email}
                onChange={handleRegChange('email')}
                placeholder="jane.doe@example.com"
                className={`form-input ${regErrors.email ? 'has-error' : ''}`}
                aria-invalid={Boolean(regErrors.email)}
                aria-describedby={regErrors.email ? 'reg-email-error' : undefined}
              />
              {regErrors.email && (
                <span id="reg-email-error" className="form-field-error" role="alert">
                  {regErrors.email}
                </span>
              )}
            </div>

            {/* Optional Mobile Number */}
            <div className="form-group">
              <label htmlFor="auth-reg-mobile" className="form-label">
                <span>Mobile number</span>
                <span className="form-label-optional">Optional</span>
              </label>
              <input
                id="auth-reg-mobile"
                type="tel"
                autoComplete="tel"
                disabled={loading}
                value={regData.mobileNumber}
                onChange={handleRegChange('mobileNumber')}
                placeholder="+1 555-019-2834"
                className={`form-input ${regErrors.mobileNumber ? 'has-error' : ''}`}
                aria-invalid={Boolean(regErrors.mobileNumber)}
                aria-describedby={regErrors.mobileNumber ? 'reg-mobile-error' : undefined}
              />
              {regErrors.mobileNumber && (
                <span id="reg-mobile-error" className="form-field-error" role="alert">
                  {regErrors.mobileNumber}
                </span>
              )}
            </div>

            {/* Password with Live Strength & Checklist */}
            <div className="form-group">
              <label htmlFor="auth-reg-password" className="form-label">
                Password
              </label>
              <div className="password-input-wrapper">
                <input
                  id="auth-reg-password"
                  type={showRegPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  disabled={loading}
                  value={regData.password}
                  onChange={handleRegChange('password')}
                  placeholder="Create a strong password"
                  className={`form-input ${regErrors.password ? 'has-error' : ''}`}
                  aria-invalid={Boolean(regErrors.password)}
                  aria-describedby={regErrors.password ? 'reg-password-error' : undefined}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowRegPassword((prev) => !prev)}
                  aria-label={showRegPassword ? 'Hide password' : 'Show password'}
                  title={showRegPassword ? 'Hide password' : 'Show password'}
                  tabIndex={0}
                >
                  {showRegPassword ? (
                    <EyeOff size={16} aria-hidden="true" />
                  ) : (
                    <Eye size={16} aria-hidden="true" />
                  )}
                </button>
              </div>

              {/* Password Strength Meter */}
              {regData.password && (
                <div className="password-strength-container" aria-live="polite">
                  <div className="password-strength-header">
                    <span style={{ color: 'var(--color-text-muted)' }}>Strength:</span>
                    <span
                      className="strength-label"
                      style={{ color: passwordStatus.strengthColor }}
                    >
                      {passwordStatus.strengthLabel}
                    </span>
                  </div>
                  <div className="password-strength-bar" aria-hidden="true">
                    <div
                      className="strength-segment"
                      style={{
                        backgroundColor:
                          passwordStatus.score >= 1
                            ? passwordStatus.strengthColor
                            : 'var(--color-border)',
                      }}
                    />
                    <div
                      className="strength-segment"
                      style={{
                        backgroundColor:
                          passwordStatus.score >= 3
                            ? passwordStatus.strengthColor
                            : 'var(--color-border)',
                      }}
                    />
                    <div
                      className="strength-segment"
                      style={{
                        backgroundColor:
                          passwordStatus.score >= 4
                            ? passwordStatus.strengthColor
                            : 'var(--color-border)',
                      }}
                    />
                    <div
                      className="strength-segment"
                      style={{
                        backgroundColor: passwordStatus.isValid
                          ? passwordStatus.strengthColor
                          : 'var(--color-border)',
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Live Criteria Checklist */}
              {(passwordTouched || regData.password) && (
                <div className="password-criteria-list" aria-label="Password requirements">
                  <div className={`password-criteria-item ${passwordStatus.criteria.length ? 'met' : ''}`}>
                    <span className="criteria-dot" />
                    <span>8–14 characters</span>
                  </div>
                  <div className={`password-criteria-item ${passwordStatus.criteria.hasUpper ? 'met' : ''}`}>
                    <span className="criteria-dot" />
                    <span>Uppercase letter (A-Z)</span>
                  </div>
                  <div className={`password-criteria-item ${passwordStatus.criteria.hasLower ? 'met' : ''}`}>
                    <span className="criteria-dot" />
                    <span>Lowercase letter (a-z)</span>
                  </div>
                  <div className={`password-criteria-item ${passwordStatus.criteria.hasNumber ? 'met' : ''}`}>
                    <span className="criteria-dot" />
                    <span>Number (0-9)</span>
                  </div>
                  <div
                    className={`password-criteria-item ${passwordStatus.criteria.hasSpecial ? 'met' : ''}`}
                    style={{ gridColumn: 'span 2' }}
                  >
                    <span className="criteria-dot" />
                    <span>Special character (!@#$%^&*...)</span>
                  </div>
                </div>
              )}

              {regErrors.password && (
                <span id="reg-password-error" className="form-field-error" role="alert">
                  {regErrors.password}
                </span>
              )}
            </div>

            {/* Confirm Password */}
            <div className="form-group">
              <label htmlFor="auth-reg-confirm-password" className="form-label">
                <span>Confirm password</span>
                {passwordMatchStatus.checked && (
                  <span
                    style={{
                      fontSize: '12px',
                      fontWeight: 500,
                      color: passwordMatchStatus.matches
                        ? 'var(--color-status-low)'
                        : 'var(--color-status-high)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    {passwordMatchStatus.matches ? (
                      <>
                        <Check size={12} aria-hidden="true" />
                        <span>Passwords match</span>
                      </>
                    ) : (
                      <span>Does not match</span>
                    )}
                  </span>
                )}
              </label>
              <div className="password-input-wrapper">
                <input
                  id="auth-reg-confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  disabled={loading}
                  value={regData.confirmPassword}
                  onChange={handleRegChange('confirmPassword')}
                  placeholder="Repeat your password"
                  className={`form-input ${
                    regErrors.confirmPassword ||
                    (passwordMatchStatus.checked && !passwordMatchStatus.matches)
                      ? 'has-error'
                      : ''
                  }`}
                  aria-invalid={
                    Boolean(regErrors.confirmPassword) ||
                    (passwordMatchStatus.checked && !passwordMatchStatus.matches)
                  }
                  aria-describedby={
                    regErrors.confirmPassword ? 'reg-confirm-password-error' : undefined
                  }
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowConfirmPassword((prev) => !prev)}
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  title={showConfirmPassword ? 'Hide password' : 'Show password'}
                  tabIndex={0}
                >
                  {showConfirmPassword ? (
                    <EyeOff size={16} aria-hidden="true" />
                  ) : (
                    <Eye size={16} aria-hidden="true" />
                  )}
                </button>
              </div>
              {regErrors.confirmPassword && (
                <span id="reg-confirm-password-error" className="form-field-error" role="alert">
                  {regErrors.confirmPassword}
                </span>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary auth-submit-btn"
              aria-busy={loading}
            >
              {loading ? (
                <>
                  <span className="auth-spinner" aria-hidden="true" />
                  <span>Creating account...</span>
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          {/* Footer Switching Prompt */}
          <div className="auth-footer">
            <p className="auth-switch-prompt">
              Already have an account?{' '}
              <button
                type="button"
                className="auth-switch-btn"
                onClick={() => handleTabSwitch('login')}
              >
                Login
              </button>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default AuthWindow;
