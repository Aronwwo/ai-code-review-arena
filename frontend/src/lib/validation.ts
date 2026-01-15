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

/**
 * Validate username format
 * Requirements: 3-30 chars, letters/numbers/._-
 */
export function validateUsername(username: string): { valid: boolean; error?: string } {
  const trimmed = username.trim();
  if (trimmed.length < 3 || trimmed.length > 30) {
    return { valid: false, error: 'minimum 3 i maksymalnie 30 znaków' };
  }
  if (!/^[a-zA-Z0-9._-]+$/.test(trimmed)) {
    return { valid: false, error: 'dozwolone litery, cyfry i znaki . _ -' };
  }
  return { valid: true };
}