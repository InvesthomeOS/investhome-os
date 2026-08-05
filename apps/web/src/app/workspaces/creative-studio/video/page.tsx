import { redirect } from 'next/navigation';

/** Alias → canonical Video Builder route */
export default function VideoAliasRedirect() {
  redirect('/workspaces/creative-studio/video-builder');
}
