/**
 * City recommendation engine.
 *
 * Maps a fragrance's family_features + climate scores to the 25-city global pool,
 * returning the top 15 ranked results each with best wearing months and a
 * city-specific reason string.
 */

// ── Archetype groups (maps ML family names → 4 broad wear archetypes) ────────
const ARCHETYPE_FAMILIES = {
  heavy:  ['oriental', 'gourmand', 'spicy', 'resinous', 'animalic'],
  woody:  ['woody', 'chypre', 'fougere', 'earthy', 'musky', 'smoky'],
  floral: ['floral', 'powdery'],
  light:  ['citrus', 'fresh', 'aquatic', 'green'],
}

/** Returns one of 'heavy' | 'woody' | 'floral' | 'light' based on summed family scores. */
function getArchetype(familyFeatures) {
  if (!familyFeatures || !Object.keys(familyFeatures).length) return 'woody'
  const scores = {}
  for (const [arch, fams] of Object.entries(ARCHETYPE_FAMILIES)) {
    scores[arch] = fams.reduce((s, f) => s + (familyFeatures[f] || 0), 0)
  }
  return Object.entries(scores).sort((a, b) => b[1] - a[1])[0][0]
}

// ── City database ─────────────────────────────────────────────────────────────
//
// affinity: { light, floral, woody, heavy } — 1 (neutral) → 3 (ideal match)
// months:   best calendar months PER archetype to wear this fragrance type in that city
// reason:   one-line explanation PER archetype (shown in the UI card)
//
const CITY_DB = [
  {
    id: 'dubai', city: 'Dubai', country: 'UAE', climate: 'arid',
    affinity: { light: 1, floral: 1, woody: 2, heavy: 3 },
    months: {
      light:  ['Oct', 'Nov', 'Feb', 'Mar'],
      floral: ['Nov', 'Feb', 'Mar'],
      woody:  ['Nov', 'Dec', 'Jan', 'Feb'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
    },
    reason: {
      light:  'Gulf winter keeps citrus bright — avoid scorching summer months',
      floral: 'Mild winter sun carries florals without the punishing summer heat',
      woody:  'Dry desert air lets amber and cedar radiate without turning sharp',
      heavy:  'Cool evenings and low humidity unlock every layer of deep spice and oud',
    },
  },
  {
    id: 'tokyo', city: 'Tokyo', country: 'Japan', climate: 'temperate',
    affinity: { light: 2, floral: 3, woody: 2, heavy: 1 },
    months: {
      light:  ['Apr', 'May', 'Sep', 'Oct'],
      floral: ['Mar', 'Apr', 'May'],
      woody:  ['Oct', 'Nov', 'Dec'],
      heavy:  ['Nov', 'Dec', 'Jan'],
    },
    reason: {
      light:  'Mild humid spring extends sillage of fresh and citrus fragrances beautifully',
      floral: 'Cherry blossom season (Mar–Apr) is the perfect backdrop for spring florals',
      woody:  'Crisp autumn air in Ginza makes cedar and dry woods sing',
      heavy:  'Cool winters let deep orientals develop on skin without cloying',
    },
  },
  {
    id: 'paris', city: 'Paris', country: 'France', climate: 'temperate',
    affinity: { light: 1, floral: 3, woody: 2, heavy: 2 },
    months: {
      light:  ['May', 'Jun', 'Sep'],
      floral: ['Apr', 'May', 'Jun'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Feb'],
    },
    reason: {
      light:  'Long June evenings on a terrace — effortless citrus in the city of perfumery',
      floral: 'The Seine in bloom (Apr–Jun) is tailor-made for structured French florals',
      woody:  'Cool misty evenings amplify leather and vetiver in classic chypres',
      heavy:  'Parisian autumn fog concentrates ambered orientals into something theatrical',
    },
  },
  {
    id: 'newyork', city: 'New York', country: 'USA', climate: 'temperate',
    affinity: { light: 2, floral: 1, woody: 2, heavy: 2 },
    months: {
      light:  ['May', 'Jun', 'Sep'],
      floral: ['Apr', 'May'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Feb'],
    },
    reason: {
      light:  'Central Park in early fall — bright airy fragrances carry perfectly in the breeze',
      floral: 'Spring blossoms along the High Line invite soft, romantic florals',
      woody:  'Crisp Manhattan autumn amplifies cedar, vetiver, and leather perfectly',
      heavy:  'NY winter cold concentrates sillage — orientals project powerfully indoors',
    },
  },
  {
    id: 'london', city: 'London', country: 'UK', climate: 'temperate',
    affinity: { light: 1, floral: 2, woody: 3, heavy: 2 },
    months: {
      light:  ['Jun', 'Jul', 'Aug'],
      floral: ['May', 'Jun', 'Sep'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan'],
    },
    reason: {
      light:  'Rare British summer sunshine — enjoy something light and zesty while it lasts',
      floral: 'Chelsea in June and garden parties in September suit soft English florals',
      woody:  'Damp autumn air extends vetiver, oakmoss, and leather in classic chypres',
      heavy:  'Grey winter afternoons make brooding orientals and incense scents magnetic',
    },
  },
  {
    id: 'barcelona', city: 'Barcelona', country: 'Spain', climate: 'temperate',
    affinity: { light: 3, floral: 3, woody: 1, heavy: 1 },
    months: {
      light:  ['May', 'Jun', 'Jul', 'Aug', 'Sep'],
      floral: ['Apr', 'May', 'Jun', 'Sep'],
      woody:  ['Oct', 'Nov'],
      heavy:  ['Nov', 'Dec'],
    },
    reason: {
      light:  'Mediterranean warmth makes citrus and aquatic notes bloom all summer long',
      floral: 'Spring in the Gothic Quarter — florals feel effortlessly right here',
      woody:  'Mild Catalan autumn suits woody transitions from sun-kissed summer skin',
      heavy:  'Cooler November evenings invite richer sillage on the Ramblas',
    },
  },
  {
    id: 'mumbai', city: 'Mumbai', country: 'India', climate: 'tropical',
    affinity: { light: 1, floral: 2, woody: 2, heavy: 3 },
    months: {
      light:  ['Nov', 'Dec', 'Jan', 'Feb'],
      floral: ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
      woody:  ['Nov', 'Dec', 'Jan', 'Feb'],
      heavy:  ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
    },
    reason: {
      light:  'Post-monsoon cool (Nov–Feb) keeps citrus bright in the city air',
      floral: 'Winter jasmine and marigold markets pair perfectly with white florals',
      woody:  'Sandalwood and patchouli resonate deeply with the city\'s own aromatic palette',
      heavy:  'Dry-season warmth lets incense, oud, and spice unfurl with full complexity',
    },
  },
  {
    id: 'sydney', city: 'Sydney', country: 'Australia', climate: 'temperate',
    affinity: { light: 3, floral: 2, woody: 1, heavy: 1 },
    months: {
      light:  ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
      floral: ['Sep', 'Oct', 'Nov'],
      woody:  ['Apr', 'May', 'Jun'],
      heavy:  ['May', 'Jun', 'Jul'],
    },
    reason: {
      light:  'Southern summer (Dec–Feb) — fresh and aquatic notes shine at Bondi Beach',
      floral: 'Australian spring (Sep–Nov) bursts with wildflowers and wattle blossoms',
      woody:  'Crisp harbour autumn (Apr–Jun) is ideal for cedar and sandalwood depth',
      heavy:  'Mild Sydney winter lets heavier sillage develop without the cold sting',
    },
  },
  {
    id: 'istanbul', city: 'Istanbul', country: 'Turkey', climate: 'temperate',
    affinity: { light: 1, floral: 2, woody: 2, heavy: 3 },
    months: {
      light:  ['May', 'Jun', 'Sep'],
      floral: ['Apr', 'May', 'Sep'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
    },
    reason: {
      light:  'Early summer sun on the Bosphorus — bright citrus feels completely effortless',
      floral: 'Tulip festival (April) and rose oil heritage suit florals perfectly',
      woody:  'Autumn mist over the Golden Horn suits leather and smoky resinous woods',
      heavy:  'Ottoman winters and bazaar incense call for rich, complex orientals',
    },
  },
  {
    id: 'marrakech', city: 'Marrakech', country: 'Morocco', climate: 'arid',
    affinity: { light: 1, floral: 2, woody: 2, heavy: 3 },
    months: {
      light:  ['Mar', 'Apr', 'Oct', 'Nov'],
      floral: ['Mar', 'Apr', 'May', 'Oct'],
      woody:  ['Oct', 'Nov', 'Dec', 'Feb', 'Mar'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
    },
    reason: {
      light:  'Cool spring and autumn mornings keep lighter accords alive in the medina',
      floral: 'Rose festivals and orange-blossom water make florals feel ancestral here',
      woody:  'Arid Atlas air amplifies cedar, argan-oud, and amber beautifully',
      heavy:  'Souk spices and rosewater heritage — the spiritual home of oriental perfumery',
    },
  },
  {
    id: 'vienna', city: 'Vienna', country: 'Austria', climate: 'cold',
    affinity: { light: 1, floral: 1, woody: 2, heavy: 3 },
    months: {
      light:  ['May', 'Jun', 'Sep'],
      floral: ['Apr', 'May', 'Jun'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
    },
    reason: {
      light:  'Summer evenings on the Danube call for something light and sparkling',
      floral: 'Lilac season in the Stadtpark suits powdery florals with Viennese elegance',
      woody:  'Autumn along the Ringstrasse — vetiver and leather echo the architecture',
      heavy:  'Viennese winters were made for dark, ambered orientals in opera coats',
    },
  },
  {
    id: 'singapore', city: 'Singapore', country: 'Singapore', climate: 'tropical',
    affinity: { light: 2, floral: 2, woody: 1, heavy: 1 },
    months: {
      light:  ['Nov', 'Dec', 'Jan', 'Feb'],
      floral: ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
      woody:  ['Nov', 'Dec', 'Jan', 'Feb'],
      heavy:  ['Dec', 'Jan', 'Feb'],
    },
    reason: {
      light:  'Inter-monsoon months (Nov–Jan) are the least humid — fresh notes stay true',
      floral: 'Lush tropical gardens and Night Safari air provide an exotic floral backdrop',
      woody:  'Air-conditioned spaces let sandalwood and cedar radiate in the city-state',
      heavy:  'Cool-season evenings are when heavier accords finally breathe freely here',
    },
  },
  {
    id: 'losangeles', city: 'Los Angeles', country: 'USA', climate: 'temperate',
    affinity: { light: 3, floral: 2, woody: 1, heavy: 1 },
    months: {
      light:  ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'],
      floral: ['Mar', 'Apr', 'May', 'Sep', 'Oct'],
      woody:  ['Nov', 'Dec', 'Jan'],
      heavy:  ['Nov', 'Dec', 'Jan', 'Feb'],
    },
    reason: {
      light:  'Endless Californian sunshine — bright citrus and aquatic notes soar all year',
      floral: 'Jacaranda season (Apr–May) fills LA streets with purple — wear something floral',
      woody:  'Cool Pacific canyon nights in winter bring out depth in sandalwood and cedar',
      heavy:  'Canyon evenings in December let richer profiles develop without summer intensity',
    },
  },
  {
    id: 'rome', city: 'Rome', country: 'Italy', climate: 'temperate',
    affinity: { light: 2, floral: 3, woody: 1, heavy: 1 },
    months: {
      light:  ['May', 'Jun', 'Sep', 'Oct'],
      floral: ['Apr', 'May', 'Jun', 'Sep'],
      woody:  ['Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec'],
    },
    reason: {
      light:  'Mediterranean warmth May–June carries citrus and aquatic notes effortlessly',
      floral: 'Wisteria over the Spanish Steps in spring — florals belong in the Eternal City',
      woody:  'Autumn cobblestones and ochre facades suit dry woody fragrances perfectly',
      heavy:  'Roman winters call for something dramatic — orientals echo the baroque grandeur',
    },
  },
  {
    id: 'saopaulo', city: 'São Paulo', country: 'Brazil', climate: 'tropical',
    affinity: { light: 2, floral: 2, woody: 1, heavy: 2 },
    months: {
      light:  ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'],
      floral: ['Apr', 'May', 'Jun', 'Aug', 'Sep'],
      woody:  ['May', 'Jun', 'Jul', 'Aug'],
      heavy:  ['May', 'Jun', 'Jul', 'Aug'],
    },
    reason: {
      light:  'Southern autumn/winter (Apr–Sep) at altitude keeps fresh fragrances vivid',
      floral: 'São Paulo winter (Jun–Aug) is mild and dry — open floral hearts project well',
      woody:  'Dry season brings out Brazilian rosewood and cedar character beautifully',
      heavy:  'Cool paulista winters concentrate sillage in the concrete jungle perfectly',
    },
  },
  {
    id: 'seoul', city: 'Seoul', country: 'South Korea', climate: 'cold',
    affinity: { light: 1, floral: 2, woody: 2, heavy: 3 },
    months: {
      light:  ['Apr', 'May', 'Sep', 'Oct'],
      floral: ['Apr', 'May'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
    },
    reason: {
      light:  'Late April through May is ideal — mild temps keep light notes from evaporating',
      floral: 'Cherry blossoms along the Han River (April) are made for spring florals',
      woody:  'Crisp autumn air in Bukchon Hanok Village amplifies cedar and pine depth',
      heavy:  'Korean winters are bracingly cold — orientals and incense project magnificently',
    },
  },
  {
    id: 'amsterdam', city: 'Amsterdam', country: 'Netherlands', climate: 'temperate',
    affinity: { light: 1, floral: 3, woody: 2, heavy: 2 },
    months: {
      light:  ['May', 'Jun', 'Jul', 'Aug'],
      floral: ['Apr', 'May', 'Jun'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb'],
    },
    reason: {
      light:  'Long summer evenings on the canal — light aquatics feel perfectly at home',
      floral: 'Keukenhof tulip season (Apr–May) — florals are a pilgrimage here',
      woody:  'Autumn along the Prinsengracht suits dry, earthy woody fragrances beautifully',
      heavy:  'Canal mist in winter concentrates heavy perfumes into something almost spiritual',
    },
  },
  {
    id: 'cairo', city: 'Cairo', country: 'Egypt', climate: 'arid',
    affinity: { light: 1, floral: 1, woody: 2, heavy: 3 },
    months: {
      light:  ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
      floral: ['Feb', 'Mar', 'Nov'],
      woody:  ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
      heavy:  ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
    },
    reason: {
      light:  'Cool Nile-side winters (Nov–Mar) let citrus and fresh notes project cleanly',
      floral: 'Egyptian jasmine and rose oil heritage makes florals feel deeply authentic here',
      woody:  'Kyphi-scented history makes Cairo the natural home of dark woody blends',
      heavy:  'Desert air at the foot of the pyramids — the ancestral home of incense and resin',
    },
  },
  {
    id: 'buenosaires', city: 'Buenos Aires', country: 'Argentina', climate: 'temperate',
    affinity: { light: 2, floral: 3, woody: 2, heavy: 1 },
    months: {
      light:  ['Nov', 'Dec', 'Jan', 'Feb', 'Sep', 'Oct'],
      floral: ['Sep', 'Oct', 'Nov', 'Dec'],
      woody:  ['Apr', 'May', 'Jun', 'Jul'],
      heavy:  ['May', 'Jun', 'Jul', 'Aug'],
    },
    reason: {
      light:  'Buenos Aires summer (Dec–Feb) is warm and lively — light fragrances effervesce',
      floral: 'Jacaranda trees in bloom (Sept–Nov) along the Palermo avenues — wear florals',
      woody:  'Porteño autumn (Apr–Jun) suits sophisticated woody and leather profiles',
      heavy:  'Tango evenings in Buenos Aires winter — dark orientals suit the mood perfectly',
    },
  },
  {
    id: 'mexicocity', city: 'Mexico City', country: 'Mexico', climate: 'temperate',
    affinity: { light: 2, floral: 2, woody: 2, heavy: 1 },
    months: {
      light:  ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr'],
      floral: ['Feb', 'Mar', 'Apr', 'Oct', 'Nov'],
      woody:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb'],
      heavy:  ['Nov', 'Dec', 'Jan', 'Feb'],
    },
    reason: {
      light:  'Dry season (Nov–Apr) at altitude — fresh fragrances stay crisp and vivid',
      floral: 'Día de los Muertos (Oct–Nov) fills the city with marigolds and copal blooms',
      woody:  'Cool highland evenings suit earthy, smoky mezcal-adjacent woody accords',
      heavy:  'Temperate highland winters let rich orientals and resins project beautifully',
    },
  },
  {
    id: 'zurich', city: 'Zurich', country: 'Switzerland', climate: 'cold',
    affinity: { light: 1, floral: 1, woody: 3, heavy: 2 },
    months: {
      light:  ['May', 'Jun', 'Jul', 'Aug'],
      floral: ['May', 'Jun', 'Jul'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb'],
    },
    reason: {
      light:  'Alpine summer light makes citrus and green fragrances feel crisp and elevated',
      floral: 'Lake Zurich in bloom (Jun–Jul) is a setting for refined, structured florals',
      woody:  'Clean Alpine autumn air — dry and precise — is ideal for elegant woody fragrances',
      heavy:  'Swiss winter precision suits complex, long-lasting oriental compositions',
    },
  },
  {
    id: 'capetown', city: 'Cape Town', country: 'South Africa', climate: 'temperate',
    affinity: { light: 3, floral: 2, woody: 1, heavy: 1 },
    months: {
      light:  ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
      floral: ['Sep', 'Oct', 'Nov', 'Dec'],
      woody:  ['Apr', 'May', 'Jun'],
      heavy:  ['May', 'Jun', 'Jul'],
    },
    reason: {
      light:  'Warm Atlantic breeze on Clifton Beach (Dec–Feb) — fresh fragrances soar',
      floral: 'Namaqualand wildflowers and fynbos blooming in spring (Sep–Nov) — wear florals',
      woody:  'Autumn beneath Table Mountain (Apr–Jun) suits earthy, botanical accords',
      heavy:  'Cape winter evenings are mild enough to let heavy fragrances develop slowly',
    },
  },
  {
    id: 'bangkok', city: 'Bangkok', country: 'Thailand', climate: 'tropical',
    affinity: { light: 1, floral: 2, woody: 1, heavy: 2 },
    months: {
      light:  ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
      floral: ['Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
      woody:  ['Nov', 'Dec', 'Jan', 'Feb'],
      heavy:  ['Nov', 'Dec', 'Jan', 'Feb'],
    },
    reason: {
      light:  'Cooler months (Nov–Feb) keep fresh and citrus notes from vanishing in the heat',
      floral: 'Fresh jasmine garlands and lotus offerings make florals deeply resonant here',
      woody:  'Teak temples and sandalwood incense set the perfect stage for woody fragrances',
      heavy:  'Cool season temple air and jasmine offerings make orientals feel profoundly at home',
    },
  },
  {
    id: 'milan', city: 'Milan', country: 'Italy', climate: 'temperate',
    affinity: { light: 1, floral: 2, woody: 3, heavy: 2 },
    months: {
      light:  ['May', 'Jun', 'Sep'],
      floral: ['Apr', 'May', 'Jun'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb'],
    },
    reason: {
      light:  'Early September warmth in the Brera district suits bright, easy-wearing citrus',
      floral: 'Navigli canals in spring are the perfect stage for structured Italian florals',
      woody:  'Fashion Week (Sep) — cedarwood, leather, and musks feel right in the Quadrilatero',
      heavy:  'Milanese winter fog concentrates heavy fragrances into theatrical sillage trails',
    },
  },
  {
    id: 'moscow', city: 'Moscow', country: 'Russia', climate: 'cold',
    affinity: { light: 1, floral: 1, woody: 2, heavy: 3 },
    months: {
      light:  ['Jun', 'Jul'],
      floral: ['May', 'Jun'],
      woody:  ['Sep', 'Oct', 'Nov'],
      heavy:  ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
    },
    reason: {
      light:  'Brief luminous Russian summer (Jun–Jul) — light fragrances feel like a celebration',
      floral: 'White nights of late spring (May–Jun) create a magical backdrop for bright florals',
      woody:  'Birch forest autumn (Sep–Oct) is the natural home of birch tar and vetiver',
      heavy:  'Russian winters demand grandeur — longevity is unmatched in the deep cold',
    },
  },
]

// ── Scoring + diversity ───────────────────────────────────────────────────────

const MAX_PER_CLIMATE = 5  // prevents all-European or all-arid results

/**
 * Returns the top 15 city recommendations for a given predictions object.
 * Each result: { id, city, country, bestMonths: string[], reason: string }
 */
export function getCityRecommendations(predictions) {
  if (!predictions) return []

  const arch = getArchetype(predictions.family_features)

  const climateScores = {
    tropical:  predictions.climate_tropical  ?? 5,
    arid:      predictions.climate_arid      ?? 5,
    temperate: predictions.climate_temperate ?? 5,
    cold:      predictions.climate_cold      ?? 5,
  }

  const scored = CITY_DB.map(c => {
    const climateScore   = (climateScores[c.climate] ?? 5) / 10        // 0.0–1.0
    const affinityScore  = (c.affinity[arch] ?? 1) / 3                 // 0.33–1.0
    const total          = climateScore * 0.42 + affinityScore * 0.58

    return {
      id:         c.id,
      city:       c.city,
      country:    c.country,
      climate:    c.climate,
      score:      total,
      bestMonths: c.months[arch] ?? c.months.heavy,
      reason:     c.reason[arch] ?? c.reason.heavy,
    }
  }).sort((a, b) => b.score - a.score)

  // Enforce geographic diversity — cap per climate zone
  const climateCounts = {}
  const result = []

  for (const city of scored) {
    const n = climateCounts[city.climate] ?? 0
    if (n < MAX_PER_CLIMATE) {
      result.push(city)
      climateCounts[city.climate] = n + 1
      if (result.length === 15) break
    }
  }

  // Fill remaining if diversity cap left gaps (shouldn't happen with 25-city pool)
  if (result.length < 15) {
    const seen = new Set(result.map(c => c.id))
    for (const city of scored) {
      if (!seen.has(city.id)) {
        result.push(city)
        if (result.length === 15) break
      }
    }
  }

  return result
}

/** Exposed for testing / debugging. */
export { getArchetype }
