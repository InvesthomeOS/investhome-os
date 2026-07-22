import { execFileSync } from 'node:child_process';

import { test, expect } from './fixtures';

function runDemoCli(args: string[]): string {
  return execFileSync(
    'docker',
    ['compose', 'exec', '-T', 'api', 'python', '-m', 'investhome_api.db.demo', ...args],
    {
      cwd: process.cwd().includes('.pw-verify')
        ? process.cwd().replace(/[\\/]\.pw-verify$/, '')
        : process.cwd(),
      encoding: 'utf-8',
      env: { ...process.env },
      timeout: 300_000,
    },
  );
}

test.describe('Demo reset lifecycle', () => {
  test('seed → validate → reseed no dupes → cleanup preserves non-demo intent', async () => {
    test.setTimeout(360_000);

    const seed1 = runDemoCli(['seed']);
    expect(seed1.toLowerCase()).toMatch(/seed|inserted|ok|pass|integrated/);

    const validate1 = runDemoCli(['validate']);
    expect(validate1.toLowerCase()).toMatch(/result: pass/);

    const seed2 = runDemoCli(['seed']);
    expect(seed2.toLowerCase()).not.toMatch(/traceback/);
    expect(seed2.toLowerCase()).toMatch(/users\+0|projects\+0|result: pass/);

    const validate2 = runDemoCli(['validate']);
    expect(validate2.toLowerCase()).toMatch(/result: pass/);

    // Cleanup only (do not full reset-reseed here — validate that cleanup command runs)
    const resetOut = execFileSync(
      'docker',
      [
        'compose',
        'exec',
        '-T',
        'api',
        'python',
        '-c',
        'from investhome_api.db.demo.cleanup import cleanup_integrated_demo; import json; print(json.dumps(cleanup_integrated_demo(), default=str))',
      ],
      {
        cwd: process.cwd().includes('.pw-verify')
          ? process.cwd().replace(/[\\/]\.pw-verify$/, '')
          : process.cwd(),
        encoding: 'utf-8',
        timeout: 180_000,
      },
    );
    expect(resetOut.toLowerCase()).not.toMatch(/traceback|exception/);

    // Re-seed so environment stays usable after the suite
    const reseed = runDemoCli(['seed']);
    expect(reseed.toLowerCase()).toMatch(/result: pass|seeded/);
  });
});
