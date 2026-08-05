import { redirect } from 'next/navigation';

/** Alias → canonical Video Builder route */
export default function VideoStudioAliasRedirect() {
  redirect('/workspaces/creative-studio/video-builder');
}
