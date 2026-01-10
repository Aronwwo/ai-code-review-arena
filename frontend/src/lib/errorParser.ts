/**
 * Parse API error response into user-friendly message
 * Handles both simple string errors and Pydantic validation errors
 */
type ApiErrorResponse = {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
};

type ValidationErrorItem = {
  loc?: Array<string | number>;
  msg?: string;
};

export function parseApiError(error: unknown, fallbackMessage = 'Wystąpił błąd'): string {
  const apiError = error as ApiErrorResponse;
  if (!apiError?.response?.data) {
    return fallbackMessage;
  }

  const { detail } = apiError.response.data;

  // Simple string error
  if (typeof detail === 'string') {
    return detail;
  }

  // Pydantic validation errors (array of objects)
  if (Array.isArray(detail)) {
    // Extract all error messages
    const messages = detail
      .map((err: ValidationErrorItem) => {
        const field = err.loc?.[err.loc.length - 1] || 'pole';
        const msg = err.msg || 'nieprawidłowa wartość';
        return `${field}: ${msg}`;
      })
      .join(', ');
    return messages || fallbackMessage;
  }

  // Single Pydantic error object
  if (typeof detail === 'object' && detail !== null && 'msg' in detail) {
    const typedDetail = detail as ValidationErrorItem;
    const field = typedDetail.loc?.[typedDetail.loc.length - 1] || '';
    return field ? `${field}: ${typedDetail.msg}` : typedDetail.msg || fallbackMessage;
  }

  return fallbackMessage;
}
