/**
 * TypeScript Type Guard Templates
 *
 * Type guards provide runtime validation of API responses,
 * ensuring data matches expected TypeScript interfaces.
 *
 * Usage:
 *   if (isApiResponse(data)) {
 *     // data is now typed as ApiResponse
 *   }
 */

// =============================================================================
// Basic Type Guards
// =============================================================================

/**
 * Check if value is a non-null object
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * Check if value is a non-empty string
 */
export function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

/**
 * Check if value is a positive number
 */
export function isPositiveNumber(value: unknown): value is number {
  return typeof value === 'number' && value > 0 && !isNaN(value);
}

/**
 * Check if value is a valid date string (ISO format)
 */
export function isDateString(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const date = new Date(value);
  return !isNaN(date.getTime());
}

// =============================================================================
// API Response Type Guards
// =============================================================================

/**
 * Standard API response wrapper
 */
interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
  environment?: string;
}

/**
 * Type guard for standard API response
 */
export function isApiResponse<T>(
  value: unknown,
  dataGuard?: (data: unknown) => data is T
): value is ApiResponse<T> {
  if (!isObject(value)) return false;
  if (typeof value.success !== 'boolean') return false;

  // If success is true, validate data if guard provided
  if (value.success && dataGuard && value.data !== undefined) {
    return dataGuard(value.data);
  }

  // If success is false, check for error
  if (!value.success && value.error !== undefined) {
    if (!isObject(value.error)) return false;
    if (typeof value.error.message !== 'string') return false;
  }

  return true;
}

// =============================================================================
// Example: Operations Status Type Guards
// =============================================================================

interface JobDeployment {
  deploymentId: string;
  status: string;
  lastRunTime?: string;
  nextRunTime?: string;
}

interface JobCategory {
  categoryName: string;
  deployments: JobDeployment[];
}

interface OperationsStatus {
  environment: string;
  categories: JobCategory[];
  timestamp: string;
}

/**
 * Type guard for JobDeployment
 */
export function isJobDeployment(value: unknown): value is JobDeployment {
  if (!isObject(value)) return false;
  return (
    typeof value.deploymentId === 'string' &&
    typeof value.status === 'string'
  );
}

/**
 * Type guard for JobCategory
 */
export function isJobCategory(value: unknown): value is JobCategory {
  if (!isObject(value)) return false;
  if (typeof value.categoryName !== 'string') return false;
  if (!Array.isArray(value.deployments)) return false;
  return value.deployments.every(isJobDeployment);
}

/**
 * Type guard for OperationsStatus
 */
export function isOperationsStatus(value: unknown): value is OperationsStatus {
  if (!isObject(value)) return false;
  if (typeof value.environment !== 'string') return false;
  if (typeof value.timestamp !== 'string') return false;
  if (!Array.isArray(value.categories)) return false;
  return value.categories.every(isJobCategory);
}

// =============================================================================
// Factory for Creating Type Guards
// =============================================================================

/**
 * Create a type guard for an object with required fields
 */
export function createObjectGuard<T extends Record<string, unknown>>(
  requiredFields: (keyof T)[]
): (value: unknown) => value is T {
  return (value: unknown): value is T => {
    if (!isObject(value)) return false;
    return requiredFields.every(field => field in value);
  };
}

/**
 * Create a type guard for an array of items
 */
export function createArrayGuard<T>(
  itemGuard: (value: unknown) => value is T
): (value: unknown) => value is T[] {
  return (value: unknown): value is T[] => {
    if (!Array.isArray(value)) return false;
    return value.every(itemGuard);
  };
}

// =============================================================================
// Usage Examples
// =============================================================================

/*
// Example 1: Validate API response
const response = await fetch('/api/operations');
const data = await response.json();

if (isApiResponse(data, isOperationsStatus)) {
  // data.data is now typed as OperationsStatus
  console.log(data.data.categories);
}

// Example 2: Create custom type guard
interface User {
  id: string;
  name: string;
  email: string;
}

const isUser = createObjectGuard<User>(['id', 'name', 'email']);

if (isUser(userData)) {
  // userData is now typed as User
  console.log(userData.email);
}

// Example 3: Validate array of items
const isUserArray = createArrayGuard(isUser);

if (isUserArray(usersData)) {
  // usersData is now typed as User[]
  usersData.forEach(user => console.log(user.name));
}
*/
