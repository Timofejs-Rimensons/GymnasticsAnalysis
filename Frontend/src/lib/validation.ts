/**
 * Validation utilities for database operations
 */

// UUID validation regex
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Validates if a string is a valid UUID format
 */
export function isValidUUID(value: string | undefined | null): boolean {
  if (!value || typeof value !== "string") {
    return false;
  }
  return UUID_REGEX.test(value);
}

/**
 * Validates and returns UUID or throws error
 */
export function validateUUID(value: string | undefined | null, fieldName = "ID"): string {
  if (!isValidUUID(value)) {
    throw new Error(`Invalid ${fieldName} format: must be a valid UUID`);
  }
  return value as string;
}

/**
 * Validates email format
 */
export function isValidEmail(email: string | undefined | null): boolean {
  if (!email || typeof email !== "string") {
    return false;
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}
