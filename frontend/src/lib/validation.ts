/**
 * Validation utilities for form inputs
 */

/**
 * Validate password strength
 * Requirements: min 8 chars, uppercase, lowercase, digit
 */
export function validatePassword(pwd: string): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (pwd.length < 8) errors.push('minimum 8 znaków');
  if (!/[A-Z]/.test(pwd)) errors.push('wielka litera');
  if (!/[a-z]/.test(pwd)) errors.push('mała litera');
  if (!/\d/.test(pwd)) errors.push('cyfra');
  return { valid: errors.length === 0, errors };
}

/**
 * Validate email format
 * Basic regex pattern
 */
export function validateEmail(email: string): boolean {
  const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return pattern.test(email);
}
