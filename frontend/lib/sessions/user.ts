/**
 * User ID management for per-browser sessions.
 * Stores a UUID in localStorage to identify anonymous users.
 */

const USER_ID_KEY = "genshin:userId";

/**
 * Get or create a user ID for the current browser session.
 * Uses crypto.randomUUID() for UUID generation.
 */
export function getOrCreateUserId(): string {
  if (typeof window === "undefined") {
    // SSR fallback - return empty, will be set on client
    return "";
  }

  let userId = localStorage.getItem(USER_ID_KEY);
  if (!userId) {
    userId = crypto.randomUUID();
    localStorage.setItem(USER_ID_KEY, userId);
  }
  return userId;
}

/**
 * Clear the user ID (for testing/reset purposes).
 */
export function clearUserId(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(USER_ID_KEY);
  }
}

/**
 * Check if user ID exists in storage.
 */
export function hasUserId(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return localStorage.getItem(USER_ID_KEY) !== null;
}
