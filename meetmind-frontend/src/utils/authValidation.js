/**
 * MeetMind AI — Authentication Validation Utilities (Batch 4.6)
 *
 * Implements client-side validation rules strictly aligned with backend
 * password complexity, email format, and field length constraints.
 */

export const EMAIL_REGEX = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;

/**
 * Validates email format.
 *
 * @param {string} email
 * @returns {{ isValid: boolean, message: string }}
 */
export function validateEmail(email) {
  const trimmed = (email || '').trim();
  if (!trimmed) {
    return { isValid: false, message: 'Email address is required.' };
  }
  if (trimmed.length < 3 || trimmed.length > 255) {
    return { isValid: false, message: 'Email must be between 3 and 255 characters.' };
  }
  if (!EMAIL_REGEX.test(trimmed)) {
    return { isValid: false, message: 'Please enter a valid email address.' };
  }
  return { isValid: true, message: '' };
}

/**
 * Validates individual password criteria based on backend rules:
 * - 8–14 characters
 * - At least one uppercase letter (A-Z)
 * - At least one lowercase letter (a-z)
 * - At least one number (0-9)
 * - At least one special character (!@#$%^&*(),.?":{}|<>)
 *
 * @param {string} password
 * @returns {{
 *   criteria: {
 *     length: boolean,
 *     hasUpper: boolean,
 *     hasLower: boolean,
 *     hasNumber: boolean,
 *     hasSpecial: boolean
 *   },
 *   isValid: boolean,
 *   score: number,
 *   strengthLabel: string,
 *   strengthColor: string,
 *   message: string
 * }}
 */
export function validatePassword(password) {
  const val = password || '';
  const criteria = {
    length: val.length >= 8 && val.length <= 14,
    hasUpper: /[A-Z]/.test(val),
    hasLower: /[a-z]/.test(val),
    hasNumber: /[0-9]/.test(val),
    hasSpecial: /[!@#$%^&*(),.?":{}|<>]/.test(val),
  };

  const score = Object.values(criteria).filter(Boolean).length;
  const isValid = score === 5;

  let strengthLabel = 'Too weak';
  let strengthColor = 'var(--color-status-high)'; // Red

  if (val.length === 0) {
    strengthLabel = 'Empty';
    strengthColor = 'var(--color-border)';
  } else if (score <= 2) {
    strengthLabel = 'Weak';
    strengthColor = 'var(--color-status-high)'; // Red
  } else if (score === 3 || score === 4) {
    strengthLabel = 'Fair';
    strengthColor = 'var(--color-status-medium)'; // Amber
  } else if (isValid) {
    strengthLabel = 'Strong';
    strengthColor = 'var(--color-status-low)'; // Green
  }

  let message = '';
  if (!isValid && val.length > 0) {
    if (!criteria.length) {
      message = 'Password must be 8–14 characters long.';
    } else if (!criteria.hasUpper) {
      message = 'Password must include at least one uppercase letter.';
    } else if (!criteria.hasLower) {
      message = 'Password must include at least one lowercase letter.';
    } else if (!criteria.hasNumber) {
      message = 'Password must include at least one number.';
    } else if (!criteria.hasSpecial) {
      message = 'Password must include at least one special character (!@#$%^&*...).';
    }
  }

  return {
    criteria,
    isValid,
    score,
    strengthLabel,
    strengthColor,
    message,
  };
}

/**
 * Validates name fields (first name / last name).
 *
 * @param {string} name
 * @param {string} fieldName - Label for error messages ('First name' or 'Last name')
 * @returns {{ isValid: boolean, message: string }}
 */
export function validateName(name, fieldName = 'Name') {
  const trimmed = (name || '').trim();
  if (!trimmed) {
    return { isValid: false, message: `${fieldName} is required.` };
  }
  if (trimmed.length > 100) {
    return { isValid: false, message: `${fieldName} cannot exceed 100 characters.` };
  }
  return { isValid: true, message: '' };
}

/**
 * Validates optional mobile number.
 *
 * @param {string} mobile
 * @returns {{ isValid: boolean, message: string }}
 */
export function validateMobileNumber(mobile) {
  const trimmed = (mobile || '').trim();
  if (!trimmed) {
    return { isValid: true, message: '' }; // Optional
  }
  if (trimmed.length > 25) {
    return { isValid: false, message: 'Mobile number cannot exceed 25 characters.' };
  }
  // Permissive international/local phone characters: digits, spaces, hyphens, plus, parens
  if (!/^[+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]*$/.test(trimmed)) {
    return { isValid: false, message: 'Please enter a valid phone number.' };
  }
  return { isValid: true, message: '' };
}
