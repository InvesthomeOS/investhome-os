import { CrmTagsWorkspace } from './_components/crm-tags-workspace';
import { makeTagsPreview } from './tags-demo-data';
import './tags.css';

/**
 * Canonical CRM Tags route.
 * Presentation uses typed local fixtures / local state until a tags API is wired.
 */
export default function CrmTagsPage() {
  const preview = makeTagsPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-tags-page">
      <CrmTagsWorkspace preview={preview} />
    </main>
  );
}
