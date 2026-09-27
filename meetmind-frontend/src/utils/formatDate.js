/**
 * MeetMind AI — Date Formatting Utilities (Section 13)
 * Provides clean, safe date formatting helpers for Dashboard and Workspace views.
 */

const MONTH_NAMES_SHORT = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/**
 * Safely parses an input date string, timestamp, or Date instance into a Date object.
 * Returns null if the value is missing or invalid.
 *
 * @param {string | number | Date} value
 * @returns {Date | null}
 */
export function parseDate(value) {
  if (!value) return null;
  if (value instanceof Date) {
    return isNaN(value.getTime()) ? null : value;
  }
  const parsed = new Date(value);
  return isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * Formats a date into a short "MMM D" string (e.g., "Sep 25").
 *
 * @param {string | number | Date} value
 * @param {string} [fallback='']
 * @returns {string}
 */
export function formatShortDate(value, fallback = '') {
  const date = parseDate(value);
  if (!date) return fallback;
  const month = MONTH_NAMES_SHORT[date.getMonth()];
  const day = date.getDate();
  return `${month} ${day}`;
}

/**
 * Formats a date into a readable full date string (e.g., "Sep 25, 2026").
 *
 * @param {string | number | Date} value
 * @param {string} [fallback='']
 * @returns {string}
 */
export function formatFullDate(value, fallback = '') {
  const date = parseDate(value);
  if (!date) return fallback;
  const month = MONTH_NAMES_SHORT[date.getMonth()];
  const day = date.getDate();
  const year = date.getFullYear();
  return `${month} ${day}, ${year}`;
}

/**
 * Calculates the calendar days difference between a deadline date and reference date (defaulting to today).
 * Returns relative metadata including days difference, user-friendly label, and priority status.
 *
 * Priority Rules (Section 8 Line 570):
 * - red for today or tomorrow (daysDiff <= 1)
 * - amber for 2–3 days (daysDiff 2 to 3)
 * - green for later deadlines (daysDiff > 3)
 * - overdue deadlines (daysDiff < 0) are treated as high priority (red)
 *
 * @param {string | number | Date} deadlineValue
 * @param {Date} [referenceDate=new Date()]
 * @returns {{ daysDiff: number, label: string, priorityLevel: 'high' | 'medium' | 'low' }}
 */
export function getRelativeDeadlineInfo(deadlineValue, referenceDate = new Date()) {
  const deadline = parseDate(deadlineValue);
  if (!deadline) {
    return { daysDiff: 0, label: 'No date', priorityLevel: 'low' };
  }

  // Normalize both dates to midnight local time for pure calendar day comparison
  const refMidnight = new Date(referenceDate.getFullYear(), referenceDate.getMonth(), referenceDate.getDate());
  const dueMidnight = new Date(deadline.getFullYear(), deadline.getMonth(), deadline.getDate());

  const msPerDay = 1000 * 60 * 60 * 24;
  const daysDiff = Math.round((dueMidnight.getTime() - refMidnight.getTime()) / msPerDay);

  let label = '';
  let priorityLevel = 'low';

  if (daysDiff < 0) {
    label = 'Overdue';
    priorityLevel = 'high';
  } else if (daysDiff === 0) {
    label = 'Today';
    priorityLevel = 'high';
  } else if (daysDiff === 1) {
    label = 'Tomorrow';
    priorityLevel = 'high';
  } else if (daysDiff === 2) {
    label = 'In 2 days';
    priorityLevel = 'medium';
  } else if (daysDiff === 3) {
    label = 'In 3 days';
    priorityLevel = 'medium';
  } else {
    label = formatShortDate(deadline);
    priorityLevel = 'low';
  }

  return { daysDiff, label, priorityLevel };
}
