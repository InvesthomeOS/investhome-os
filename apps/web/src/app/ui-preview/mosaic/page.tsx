import type { Route } from 'next';
import { redirect } from 'next/navigation';

export default function MosaicPreviewIndexPage() {
  redirect('/ui-preview/mosaic/dashboard' as Route);
}
