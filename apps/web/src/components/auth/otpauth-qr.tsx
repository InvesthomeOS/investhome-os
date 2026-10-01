'use client';

import { useMemo } from 'react';
import { encode } from 'uqr';

export function OtpauthQr({ uri, label }: { uri: string; label: string }) {
  const encoded = useMemo(() => encode(uri), [uri]);
  const modules = encoded.data;
  const size = encoded.size;
  const cell = 4;
  const quiet = 4;
  const dim = (size + quiet * 2) * cell;

  return (
    <svg
      className="mfa-qr"
      data-testid="mfa-enroll-qr"
      width={dim}
      height={dim}
      viewBox={`0 0 ${dim} ${dim}`}
      role="img"
      aria-label={label}
    >
      <rect width={dim} height={dim} fill="#ffffff" />
      {modules.flatMap((row, y) =>
        row.flatMap((on, x) =>
          on
            ? [
                <rect
                  key={`${x}-${y}`}
                  x={(x + quiet) * cell}
                  y={(y + quiet) * cell}
                  width={cell}
                  height={cell}
                  fill="#111111"
                />,
              ]
            : [],
        ),
      )}
    </svg>
  );
}
