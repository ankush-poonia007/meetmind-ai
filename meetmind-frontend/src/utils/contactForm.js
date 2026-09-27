/**
 * MeetMind AI — Contact Form Logic & Mailto Construction (Batch 7.2)
 *
 * Implements:
 * - Field trimming and controlled state normalization.
 * - Validation rules:
 *   - Full Name: required, non-empty after trimming
 *   - Email Address: required, valid email format
 *   - Category: required, one of the 4 documented options
 *   - Subject: required, non-empty after trimming
 *   - Message: required, non-empty after trimming
 * - Mailto URI construction:
 *   - Recipient: pooniaankush007@gmail.com
 *   - Subject format: [${category}] ${subject}
 *   - Body structure:
 *     Name: ${fullName}
 *     Email: ${email}
 *     Category: ${category}
 *
 *     Message:
 *     ${message}
 *   - Proper URI encoding handling special characters, line breaks, and non-ASCII.
 */

export const CONTACT_RECIPIENT = 'pooniaankush007@gmail.com';

export const CONTACT_CATEGORIES = [
  'General Query',
  'Collaboration',
  'Bug Report',
  'Other',
];

// Standard RFC 5322 compatible email format regex
export const EMAIL_REGEX = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;

/**
 * Validates individual contact form fields and returns structured validation results.
 *
 * @param {object} formData
 * @param {string} [formData.fullName]
 * @param {string} [formData.email]
 * @param {string} [formData.category]
 * @param {string} [formData.subject]
 * @param {string} [formData.message]
 * @returns {{
 *   isValid: boolean,
 *   errors: {
 *     fullName?: string,
 *     email?: string,
 *     category?: string,
 *     subject?: string,
 *     message?: string,
 *   },
 *   values: {
 *     fullName: string,
 *     email: string,
 *     category: string,
 *     subject: string,
 *     message: string,
 *   }
 * }}
 */
export function validateContactForm(formData = {}) {
  const fullName = typeof formData.fullName === 'string' ? formData.fullName.trim() : '';
  const email = typeof formData.email === 'string' ? formData.email.trim() : '';
  const category = typeof formData.category === 'string' ? formData.category.trim() : '';
  const subject = typeof formData.subject === 'string' ? formData.subject.trim() : '';
  const message = typeof formData.message === 'string' ? formData.message.trim() : '';

  const errors = {};

  // Full Name
  if (!fullName) {
    errors.fullName = 'Full Name is required.';
  }

  // Email Address
  if (!email) {
    errors.email = 'Email Address is required.';
  } else if (!EMAIL_REGEX.test(email)) {
    errors.email = 'Please enter a valid email address.';
  }

  // Category
  if (!category) {
    errors.category = 'Category is required.';
  } else if (!CONTACT_CATEGORIES.includes(category)) {
    errors.category = 'Please select a valid category from the list.';
  }

  // Subject
  if (!subject) {
    errors.subject = 'Subject is required.';
  }

  // Message
  if (!message) {
    errors.message = 'Message is required.';
  }

  const isValid = Object.keys(errors).length === 0;

  return {
    isValid,
    errors,
    values: {
      fullName,
      email,
      category,
      subject,
      message,
    },
  };
}

/**
 * Constructs a valid, properly encoded mailto URI based on documented specifications.
 *
 * @param {object} values - Validated and trimmed contact form values
 * @param {string} values.fullName
 * @param {string} values.email
 * @param {string} values.category
 * @param {string} values.subject
 * @param {string} values.message
 * @param {string} [recipient=CONTACT_RECIPIENT]
 * @returns {{
 *   uri: string,
 *   recipient: string,
 *   subject: string,
 *   body: string
 * }}
 */
export function buildContactMailtoUri(values, recipient = CONTACT_RECIPIENT) {
  const fullName = (values?.fullName || '').trim();
  const email = (values?.email || '').trim();
  const category = (values?.category || '').trim();
  const subjectText = (values?.subject || '').trim();
  const messageText = (values?.message || '').trim();

  const formattedSubject = `[${category}] ${subjectText}`;

  const formattedBody = [
    `Name: ${fullName}`,
    `Email: ${email}`,
    `Category: ${category}`,
    '',
    'Message:',
    messageText,
  ].join('\n');

  const encodedSubject = encodeURIComponent(formattedSubject);
  const encodedBody = encodeURIComponent(formattedBody);

  const uri = `mailto:${recipient}?subject=${encodedSubject}&body=${encodedBody}`;

  return {
    uri,
    recipient,
    subject: formattedSubject,
    body: formattedBody,
  };
}

/**
 * Submits the contact form by validating inputs and triggering email client handler.
 *
 * @param {object} formData
 * @param {Function} [clientOpener] - Injected email client opener for testability (defaults to window.location.href setter)
 * @returns {{
 *   success: boolean,
 *   errors: object,
 *   mailtoResult: object | null,
 *   feedback: { message: string, isDeliveredClaim: boolean } | null
 * }}
 */
export function handleContactSubmit(formData, clientOpener) {
  const validation = validateContactForm(formData);

  if (!validation.isValid) {
    return {
      success: false,
      errors: validation.errors,
      mailtoResult: null,
      feedback: null,
    };
  }

  const mailtoResult = buildContactMailtoUri(validation.values);

  if (typeof clientOpener === 'function') {
    clientOpener(mailtoResult.uri);
  } else if (typeof window !== 'undefined') {
    window.location.href = mailtoResult.uri;
  }

  return {
    success: true,
    errors: {},
    mailtoResult,
    feedback: {
      message: 'Your default email client has been requested to open with your prepared message.',
      isDeliveredClaim: false,
    },
  };
}
