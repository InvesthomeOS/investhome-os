import type { ReactNode } from 'react';

import './mosaic.css';

export const metadata = {
  title: 'Mosaic Lite Preview · Investhome OS',
  description: 'Isolated Mosaic Lite UI evaluation — demo data only',
};

/**
 * Isolated Mosaic Lite evaluation shell.
 * Routes under /ui-preview/mosaic — does not replace production dashboards.
 */
export default function MosaicPreviewLayout({ children }: { children: ReactNode }) {
  return children;
}
