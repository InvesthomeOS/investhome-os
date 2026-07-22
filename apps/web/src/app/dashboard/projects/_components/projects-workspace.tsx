'use client';

import { Suspense } from 'react';
import { useTranslations } from 'next-intl';

import { ProjectsG4Workspace } from './g4/g4-workspace';

import './g4/projects-g4.css';

export function ProjectsWorkspace() {
  const t = useTranslations('common');

  return (
    <Suspense
      fallback={
        <main className="proj-g4">
          <div className="proj-g4__empty">{t('loading')}</div>
        </main>
      }
    >
      <ProjectsG4Workspace />
    </Suspense>
  );
}
