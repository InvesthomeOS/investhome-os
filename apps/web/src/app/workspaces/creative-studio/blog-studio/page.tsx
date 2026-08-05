import { redirect } from 'next/navigation';

/** Alias → canonical Blog Builder route */
export default function BlogBuilderAliasRedirect() {
  redirect('/workspaces/creative-studio/blog-builder');
}
