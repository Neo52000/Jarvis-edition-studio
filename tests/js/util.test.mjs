import test from 'node:test';
import assert from 'node:assert/strict';
import {h, safeFile, amount} from '../../web/util.js';

test('h escapes HTML metacharacters and nullish', () => {
  assert.equal(h('<img src=x onerror="a()">&\''), '&lt;img src=x onerror=&quot;a()&quot;&gt;&amp;&#39;');
  assert.equal(h(null), ''); assert.equal(h(undefined), ''); assert.equal(h(0), '0');
});
test('safeFile strips accents and unsafe chars', () => {
  assert.equal(safeFile('Le français sans fautes / au quotidien'), 'Le-francais-sans-fautes-au-quotidien');
  assert.equal(safeFile('../../etc'), '-etc'); assert.equal(safeFile('???'), '-');
  assert.equal(safeFile('x'.repeat(100)).length, 64);
});
test('amount formats euros', () => {
  assert.match(amount(1290), /12,90\s?€/);
  assert.match(amount(undefined), /0,00\s?€/);
});
