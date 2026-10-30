import assert from 'node:assert/strict'
import test from 'node:test'

const { parseRecipientField, partitionRecipients } = await import('../email-recipients.ts')

test('normalizes and rejects recipient text', () => {
  const parsed = parseRecipientField(' Ada@Example.com ; not-an-email, ada@example.com ')
  assert.deepEqual(parsed.addresses, ['ada@example.com'])
  assert.deepEqual(parsed.invalid, ['not-an-email'])
})

test('keeps one address in the first recipient field', () => {
  const placed = partitionRecipients(
    ['ada@example.com'],
    ['ada@example.com', 'copy@example.com'],
    ['copy@example.com', 'hidden@example.com'],
  )
  assert.deepEqual(placed, {
    to: ['ada@example.com'],
    cc: ['copy@example.com'],
    bcc: ['hidden@example.com'],
  })
})

test('composer exposes CC and BCC without replacing reply', async () => {
  const { readFile } = await import('node:fs/promises')
  const composer = await readFile(
    new URL('../../../workspaces/crm/contact-card/email-send-composer.tsx', import.meta.url),
    'utf8',
  )
  const turkish = await readFile(new URL('../../../../messages/tr.json', import.meta.url), 'utf8')
  assert.match(composer, /data-testid="crm-email-cc-toggle"/)
  assert.match(composer, /data-testid="crm-email-bcc-toggle"/)
  assert.match(composer, /bcc: recipients\.bcc/)
  assert.match(composer, /mode === 'reply_all'/)
  assert.match(turkish, /"emailReplyAll": "Tümünü Yanıtla"/)
  assert.match(turkish, /"gmailAccountNotOwned":/)
  assert.match(composer, /gmail_account_not_owned/)
})
