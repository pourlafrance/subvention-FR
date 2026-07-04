const nf = new Intl.NumberFormat('fr-FR')

export function formatInt(n) {
  if (n == null) return '—'
  return nf.format(Math.round(n))
}

export function formatEur(n) {
  if (n == null) return '—'
  const abs = Math.abs(n)
  if (abs >= 1e9) return (n / 1e9).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' Md€'
  if (abs >= 1e6) return (n / 1e6).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' M€'
  if (abs >= 1e3) return (n / 1e3).toLocaleString('fr-FR', { maximumFractionDigits: 0 }) + ' k€'
  return nf.format(Math.round(n)) + ' €'
}

export function formatEurFull(n) {
  if (n == null) return '—'
  return nf.format(Math.round(n)) + ' €'
}

export function formatPct(x) {
  if (x == null) return '—'
  return (x * 100).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) + ' %'
}

export const TYPE_LABELS = {
  association: 'Association',
  entreprise: 'Entreprise',
  exploitation: 'Exploitation agricole',
}
