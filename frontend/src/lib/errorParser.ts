/**
 * Parse API error response into user-friendly message
 * Handles both simple string errors and Pydantic validation errors
 */
export function parseApiError(error: any, fallbackMessage = 'Wystąpił błąd'): string {
  if (!error?.response?.data) {
    return fallbackMessage;
  }

  const { detail } = error.response.data;

  // Simple string error
  if (typeof detail === 'string') {
    return detail;
  }

  // Pydantic validation errors (array of objects)
  if (Array.isArray(detail)) {
    // Extract all error messages
    const messages = detail
      .map((err: any) => {
        const field = err.loc?.[err.loc.length - 1] || 'pole';
        const msg = err.msg || 'nieprawidłowa wartość';
        return `${field}: ${msg}`;
      })
      .join(', ');
    return messages || fallbackMessage;
  }

  // Single Pydantic error object
  if (typeof detail === 'object' && detail.msg) {
    const field = detail.loc?.[detail.loc.length - 1] || '';
    return field ? `${field}: ${detail.msg}` : detail.msg;
  }

  return fallbackMessage;
}
