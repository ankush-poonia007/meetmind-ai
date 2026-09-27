/**
 * MeetMind AI — Batch 7.2: Contact Form & Mailto Behavior Test Suite
 *
 * Validates:
 * 1. Client-side field validation rules (presence, email format, categories, whitespace).
 * 2. Proper mailto URI encoding, recipient address, subject format, and structured message body.
 * 3. Submission flow: email client invocation without real delivery claims.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  CONTACT_RECIPIENT,
  CONTACT_CATEGORIES,
  validateContactForm,
  buildContactMailtoUri,
  handleContactSubmit,
} from '../utils/contactForm.js';

/* ── 1. Validation Tests ─────────────────────────────────────────────────── */

test('Validation: 1. Empty form submission is rejected', () => {
  const result = validateContactForm({});
  assert.equal(result.isValid, false);
  assert.equal(Boolean(result.errors.fullName), true);
  assert.equal(Boolean(result.errors.email), true);
  assert.equal(Boolean(result.errors.category), true);
  assert.equal(Boolean(result.errors.subject), true);
  assert.equal(Boolean(result.errors.message), true);
});

test('Validation: 2. Missing name is rejected', () => {
  const result = validateContactForm({
    fullName: '',
    email: 'test@example.com',
    category: 'General Query',
    subject: 'Question',
    message: 'Hello world',
  });
  assert.equal(result.isValid, false);
  assert.equal(result.errors.fullName, 'Full Name is required.');
  assert.equal(result.errors.email, undefined);
});

test('Validation: 3. Missing email is rejected', () => {
  const result = validateContactForm({
    fullName: 'Jane Doe',
    email: '',
    category: 'General Query',
    subject: 'Question',
    message: 'Hello world',
  });
  assert.equal(result.isValid, false);
  assert.equal(result.errors.email, 'Email Address is required.');
});

test('Validation: 4. Invalid email format is rejected', () => {
  const invalidEmails = [
    'plainaddress',
    'missing@domain',
    '@missinguser.com',
    'spaces in@email.com',
    'missingtld@.com',
  ];

  for (const email of invalidEmails) {
    const result = validateContactForm({
      fullName: 'Jane Doe',
      email,
      category: 'General Query',
      subject: 'Question',
      message: 'Hello world',
    });
    assert.equal(result.isValid, false, `Expected ${email} to be rejected`);
    assert.equal(result.errors.email, 'Please enter a valid email address.');
  }
});

test('Validation: 5. Missing or invalid category is rejected', () => {
  const missingResult = validateContactForm({
    fullName: 'Jane Doe',
    email: 'jane@example.com',
    category: '',
    subject: 'Question',
    message: 'Hello world',
  });
  assert.equal(missingResult.isValid, false);
  assert.equal(missingResult.errors.category, 'Category is required.');

  const invalidResult = validateContactForm({
    fullName: 'Jane Doe',
    email: 'jane@example.com',
    category: 'Undocumented Category',
    subject: 'Question',
    message: 'Hello world',
  });
  assert.equal(invalidResult.isValid, false);
  assert.equal(invalidResult.errors.category, 'Please select a valid category from the list.');
});

test('Validation: 6. Missing subject is rejected', () => {
  const result = validateContactForm({
    fullName: 'Jane Doe',
    email: 'jane@example.com',
    category: 'Collaboration',
    subject: '',
    message: 'Hello world',
  });
  assert.equal(result.isValid, false);
  assert.equal(result.errors.subject, 'Subject is required.');
});

test('Validation: 7. Missing message is rejected', () => {
  const result = validateContactForm({
    fullName: 'Jane Doe',
    email: 'jane@example.com',
    category: 'Collaboration',
    subject: 'Let us chat',
    message: '',
  });
  assert.equal(result.isValid, false);
  assert.equal(result.errors.message, 'Message is required.');
});

test('Validation: 8. Whitespace-only values are rejected', () => {
  const result = validateContactForm({
    fullName: '   ',
    email: '  jane@example.com  ',
    category: '   ',
    subject: '\t\n  ',
    message: '   \n\n  ',
  });
  assert.equal(result.isValid, false);
  assert.equal(result.errors.fullName, 'Full Name is required.');
  assert.equal(result.errors.category, 'Category is required.');
  assert.equal(result.errors.subject, 'Subject is required.');
  assert.equal(result.errors.message, 'Message is required.');
});

test('Validation: 9. Valid form data passes validation', () => {
  for (const cat of CONTACT_CATEGORIES) {
    const result = validateContactForm({
      fullName: 'Alex Morgan',
      email: 'alex.morgan+test@company.co.uk',
      category: cat,
      subject: `Project Inquiry regarding ${cat}`,
      message: 'We would love to discuss integrating MeetMind with our team workflow.',
    });
    assert.equal(result.isValid, true);
    assert.deepEqual(result.errors, {});
    assert.equal(result.values.fullName, 'Alex Morgan');
    assert.equal(result.values.category, cat);
  }
});

test('Validation: 10. Valid field values remain intact after validation errors', () => {
  const input = {
    fullName: '   Alex Morgan   ',
    email: 'alex@example.com',
    category: 'Bug Report',
    subject: '', // Missing
    message: '   Found an edge case in transcript parsing.   ',
  };
  const result = validateContactForm(input);
  assert.equal(result.isValid, false);
  assert.equal(result.values.fullName, 'Alex Morgan');
  assert.equal(result.values.email, 'alex@example.com');
  assert.equal(result.values.category, 'Bug Report');
  assert.equal(result.values.message, 'Found an edge case in transcript parsing.');
});

/* ── 2. Mailto Construction Tests ────────────────────────────────────────── */

test('Mailto: 1. Correct recipient pooniaankush007@gmail.com', () => {
  const data = {
    fullName: 'Alex Morgan',
    email: 'alex@example.com',
    category: 'General Query',
    subject: 'Hello',
    message: 'Quick test',
  };
  const result = buildContactMailtoUri(data);
  assert.equal(result.recipient, 'pooniaankush007@gmail.com');
  assert.equal(result.uri.startsWith('mailto:pooniaankush007@gmail.com?'), true);
});

test('Mailto: 2. Correct subject format [${category}] ${subject}', () => {
  const data = {
    fullName: 'Alex Morgan',
    email: 'alex@example.com',
    category: 'Collaboration',
    subject: 'MeetMind AI Integration Partnership',
    message: 'Message text',
  };
  const result = buildContactMailtoUri(data);
  assert.equal(result.subject, '[Collaboration] MeetMind AI Integration Partnership');
  assert.equal(result.uri.includes(encodeURIComponent('[Collaboration] MeetMind AI Integration Partnership')), true);
});

test('Mailto: 3. Correct message body structure', () => {
  const data = {
    fullName: 'Sarah Connor',
    email: 'sarah@resistance.org',
    category: 'Bug Report',
    subject: 'Audio ingestion stall',
    message: 'Transcript parser timed out on 2-hour recording.',
  };
  const result = buildContactMailtoUri(data);
  const expectedBody = [
    'Name: Sarah Connor',
    'Email: sarah@resistance.org',
    'Category: Bug Report',
    '',
    'Message:',
    'Transcript parser timed out on 2-hour recording.',
  ].join('\n');

  assert.equal(result.body, expectedBody);
  assert.equal(result.uri.includes(encodeURIComponent(expectedBody)), true);
});

test('Mailto: 4. Proper encoding of special characters (&, ?, =, %, #, +)', () => {
  const data = {
    fullName: 'Dr. Jekyll & Mr. Hyde',
    email: 'jekyll+hyde@lab.org',
    category: 'Other',
    subject: '100% discount? Question #4 & follow-up = urgent',
    message: 'Cost is $50 & 50% = 100% / #test?foo=bar&baz=1',
  };
  const result = buildContactMailtoUri(data);

  // Raw URI must NOT contain unencoded '&' inside the query parameter values (except the delimiter between subject and body)
  const urlParts = result.uri.split('?')[1].split('&body=');
  assert.equal(urlParts.length, 2, 'Must have exactly one &body= delimiter separating subject and body');

  const subjectParam = urlParts[0].replace('subject=', '');
  const bodyParam = urlParts[1];

  assert.equal(decodeURIComponent(subjectParam), '[Other] 100% discount? Question #4 & follow-up = urgent');
  assert.equal(decodeURIComponent(bodyParam), [
    'Name: Dr. Jekyll & Mr. Hyde',
    'Email: jekyll+hyde@lab.org',
    'Category: Other',
    '',
    'Message:',
    'Cost is $50 & 50% = 100% / #test?foo=bar&baz=1',
  ].join('\n'));
});

test('Mailto: 5. Correct handling of line breaks', () => {
  const multiLineMessage = 'Paragraph 1\n\nParagraph 2\nLine 3';
  const data = {
    fullName: 'Jane Doe',
    email: 'jane@example.com',
    category: 'General Query',
    subject: 'Multi-line query',
    message: multiLineMessage,
  };
  const result = buildContactMailtoUri(data);
  assert.equal(result.body.includes(multiLineMessage), true);
  assert.equal(result.uri.includes(encodeURIComponent('\n')), true);
});

test('Mailto: 6. Correct handling of non-ASCII characters (emojis, accents, CJK)', () => {
  const data = {
    fullName: 'René François 🚀',
    email: 'rene@societe.fr',
    category: 'Collaboration',
    subject: 'Bonjour MeetMind! 🌟 こんにちは',
    message: 'Merci beaucoup pour l’outil. 素晴らしい! 💡',
  };
  const result = buildContactMailtoUri(data);
  assert.equal(result.uri.includes(encodeURIComponent('René François 🚀')), true);
  assert.equal(result.uri.includes(encodeURIComponent('こんにちは')), true);
  assert.equal(result.uri.includes(encodeURIComponent('素晴らしい! 💡')), true);
});

test('Mailto: 7. No malformed URI construction', () => {
  const data = {
    fullName: 'Alex Morgan',
    email: 'alex@example.com',
    category: 'General Query',
    subject: 'Standard subject',
    message: 'Standard message',
  };
  const result = buildContactMailtoUri(data);
  assert.match(result.uri, /^mailto:pooniaankush007@gmail\.com\?subject=[^&]+&body=.+$/);
});

/* ── 3. Submission Behavior Tests ────────────────────────────────────────── */

test('Submission: 1. Invalid submissions do not invoke email client', () => {
  let invokedUri = null;
  const opener = (uri) => {
    invokedUri = uri;
  };

  const invalidData = {
    fullName: '',
    email: 'invalid-email',
    category: '',
    subject: '',
    message: '',
  };

  const outcome = handleContactSubmit(invalidData, opener);
  assert.equal(outcome.success, false);
  assert.equal(invokedUri, null, 'Email client must NOT be invoked when validation fails');
  assert.equal(outcome.feedback, null);
  assert.equal(Object.keys(outcome.errors).length > 0, true);
});

test('Submission: 2 & 3. Valid submissions construct correct URI and invoke client', () => {
  let invokedUri = null;
  const opener = (uri) => {
    invokedUri = uri;
  };

  const validData = {
    fullName: '  Sarah Jenkins  ',
    email: 'sarah@enterprise.com',
    category: 'Collaboration',
    subject: '  Enterprise Pilot Request  ',
    message: '  We would like to pilot MeetMind across 50 project managers.  ',
  };

  const outcome = handleContactSubmit(validData, opener);
  assert.equal(outcome.success, true);
  assert.notEqual(invokedUri, null);
  assert.equal(invokedUri.startsWith('mailto:pooniaankush007@gmail.com?'), true);
  assert.equal(invokedUri, outcome.mailtoResult.uri);
});

test('Submission: 4. Feedback does not claim email delivery', () => {
  const opener = () => {};
  const validData = {
    fullName: 'Alex Morgan',
    email: 'alex@example.com',
    category: 'General Query',
    subject: 'Testing Feedback',
    message: 'Feedback test message',
  };

  const outcome = handleContactSubmit(validData, opener);
  assert.equal(outcome.success, true);
  assert.equal(outcome.feedback.isDeliveredClaim, false);
  // Ensure the wording does NOT say "email sent", "email delivered", or "message sent successfully"
  const messageLower = outcome.feedback.message.toLowerCase();
  assert.equal(messageLower.includes('email sent'), false);
  assert.equal(messageLower.includes('delivered'), false);
  assert.equal(messageLower.includes('requested to open'), true);
});

test('Submission: 5. Form values are preserved when validation fails or succeeds', () => {
  const formData = {
    fullName: 'Alex Morgan',
    email: 'invalid-email', // error
    category: 'Bug Report',
    subject: 'Broken parser',
    message: 'Long text here',
  };

  const validation = validateContactForm(formData);
  assert.equal(validation.isValid, false);
  // Form data is intact
  assert.equal(formData.fullName, 'Alex Morgan');
  assert.equal(formData.email, 'invalid-email');
  assert.equal(formData.category, 'Bug Report');
  assert.equal(formData.subject, 'Broken parser');
  assert.equal(formData.message, 'Long text here');
});
