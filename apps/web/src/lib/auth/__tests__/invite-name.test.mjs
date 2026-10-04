import assert from 'node:assert/strict';
import test from 'node:test';

function splitPersonName(fullName) {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  return { firstName: parts[0] ?? '', lastName: parts.slice(1).join(' ') };
}

function combinePersonName(firstName, lastName) {
  return [firstName.trim(), lastName.trim()].filter(Boolean).join(' ');
}

test('invite names combine without a schema change', () => {
  assert.equal(combinePersonName('Mustafa', 'Yılmaz'), 'Mustafa Yılmaz');
  assert.equal(combinePersonName('  Ada  ', '  Lovelace '), 'Ada Lovelace');
  const split = splitPersonName('Utku Aslantürk');
  assert.equal(split.firstName, 'Utku');
  assert.equal(split.lastName, 'Aslantürk');
});
