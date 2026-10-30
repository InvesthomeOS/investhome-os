const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function parseRecipientField(value: string): { addresses: string[]; invalid: string[] } {
  const addresses: string[] = []
  const invalid: string[] = []
  for (const part of value.split(/[;,]/)) {
    const text = part.trim()
    if (!text) continue
    const normalized = text.toLowerCase()
    if (!EMAIL_RE.test(normalized)) {
      invalid.push(text)
      continue
    }
    if (!addresses.includes(normalized)) addresses.push(normalized)
  }
  return { addresses, invalid }
}

export function partitionRecipients(to: string[], cc: string[], bcc: string[]) {
  const recipients: string[] = []
  const copied: string[] = []
  const hidden: string[] = []
  for (const item of to) {
    if (!recipients.includes(item)) recipients.push(item)
  }
  for (const item of cc) {
    if (!recipients.includes(item) && !copied.includes(item)) copied.push(item)
  }
  const blocked = new Set([...recipients, ...copied])
  for (const item of bcc) {
    if (!blocked.has(item) && !hidden.includes(item)) hidden.push(item)
  }
  return { to: recipients, cc: copied, bcc: hidden }
}
