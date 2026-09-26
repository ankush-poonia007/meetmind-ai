import AuthWindow from '../components/auth/AuthWindow';

/**
 * Register — User Registration Page (Batch 4.6 Correction).
 *
 * Renders the focused authentication window with 'Sign Up' selected.
 * Provides selectable options for both Login and Sign Up.
 */
function Register() {
  return (
    <div className="page-enter auth-page">
      <AuthWindow initialMode="signup" />
    </div>
  );
}

export default Register;
