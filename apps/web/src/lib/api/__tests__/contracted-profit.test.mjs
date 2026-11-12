import assert from 'node:assert/strict';
import test from 'node:test';

import { contractedProfitInput } from '../contracted-profit.mjs';

test('blank contracted profit is not stored as zero', () => {
  assert.equal(contractedProfitInput(''), null);
  assert.equal(contractedProfitInput('   '), null);
  assert.equal(contractedProfitInput('0'), '0');
  assert.equal(contractedProfitInput('250.50'), '250.50');
  assert.throws(() => contractedProfitInput('abc'), /invalid_contracted_profit/);
});
