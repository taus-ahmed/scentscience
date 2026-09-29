// Unknown is noise on most rows, so it isn't shown.
const HIDDEN = new Set(['Unknown'])

// Returns the concentration to display, or null when it should be hidden.
export function displayConcentration(c) {
  return c && !HIDDEN.has(c) ? c : null
}
