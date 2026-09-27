import AuthWindow from '../components/auth/AuthWindow';

/**
 * Login — User Authentication Page (Batch 4.6 Correction).
 *
 * Renders the focused authentication window with 'Login' selected by default.
 * Provides selectable options for both Login and Sign Up.
 */
function Login() {
  return (
    <div className="page-enter auth-page">
      <AuthWindow initialMode="login" />
    </div>
  );
}

export default Login;
