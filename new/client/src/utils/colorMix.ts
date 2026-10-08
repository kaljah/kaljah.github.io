/**
 * `color` at the opacity of a two-digit hex alpha (the "20" in "#rrggbb20").
 * Works for hex colors and for var(--color-*) tokens, which string concatenation cannot.
 */
export const tint = (color: string, alphaHex: string): string =>
  `color-mix(in srgb, ${color} ${((parseInt(alphaHex, 16) / 255) * 100).toFixed(3)}%, transparent)`;
