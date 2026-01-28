/**
 * User ID management for per-browser sessions.
 * STUB: Currently returns a placeholder. Will be wired to localStorage later.
 */

const PLACEHOLDER_USER_ID = "demo-user-12345";

/**
 * Get or create a user ID for the current browser session.
 * 
 * Future implementation:
 * - Check localStorage for existing user ID
 * - If not found, generate a new UUID and store it
 * - Return the user ID
 */
export function getOrCreateUserId(): string {
  // STUB: Return placeholder for now
  // Future: read from localStorage, generate if missing
  return PLACEHOLDER_USER_ID;
}

/**
 * Clear the user ID (for testing/reset purposes).
 */
export function clearUserId(): void {
  // STUB: Not implemented
  throw new Error("clearUserId: Not implemented");
}

/**
 * Check if user ID exists in storage.
 */
export function hasUserId(): boolean {
  // STUB: Return true for now
  return true;
}
