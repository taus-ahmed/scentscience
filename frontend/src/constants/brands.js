export const BRANDS = [
  'Acqua di Parma', 'Amouage', 'Burberry', 'Calvin Klein', 'Carolina Herrera',
  'Chanel', 'Creed', 'Dior', 'Dolce & Gabbana', 'Frederic Malle',
  'Giorgio Armani', 'Givenchy', 'Guerlain', 'Hermès', 'Initio',
  'Jean Paul Gaultier', 'Maison Margiela', 'Memo Paris', 'Nishane',
  'Paco Rabanne', 'Parfums de Marly', "Penhaligon's", 'Santa Maria Novella',
  'Serge Lutens', 'Thierry Mugler', 'Tom Ford', 'Viktor & Rolf', 'Versace',
  'Xerjoff', 'Yves Saint Laurent',
]

// Longest brand name first so "Tom Ford" matches before a hypothetical "Tom".
const BRANDS_BY_LENGTH = [...BRANDS].sort((a, b) => b.length - a.length)

/**
 * If `input` starts with a known brand name followed by more text, split it
 * into { brand, name }. Returns null if no known brand prefixes the input.
 */
export function splitBrandPrefix(input) {
  const trimmed = (input || '').trim()
  if (!trimmed) return null
  const lower = trimmed.toLowerCase()
  for (const brand of BRANDS_BY_LENGTH) {
    const brandLower = brand.toLowerCase()
    if (lower === brandLower) continue // whole input is just the brand, nothing to split
    if (lower.startsWith(brandLower + ' ')) {
      return { brand, name: trimmed.slice(brand.length).trim() }
    }
  }
  return null
}
