'use client';

import type { ReactNode } from 'react';

/** Shared documentation chrome for design-system showcase sections. */
export function ComponentDoc({
  name,
  importPath,
  props,
  usage,
  doExample,
  dontExample,
  migrationStatus,
  children,
}: {
  name: string;
  importPath: string;
  props?: string;
  usage?: string;
  doExample?: string;
  dontExample?: string;
  migrationStatus?: string;
  children: ReactNode;
}) {
  return (
    <article className="ds-component-doc" data-component={name}>
      <div className="ds-component-doc__meta">
        <h3 className="ds-type-card-title">{name}</h3>
        <code className="ds-component-doc__import">{importPath}</code>
        {props ? <p className="ds-type-caption">Props: {props}</p> : null}
        {usage ? <p className="ds-type-body-small">{usage}</p> : null}
        {migrationStatus ? (
          <p className="ds-type-caption" data-testid="ds-migration-status">
            Migration: {migrationStatus}
          </p>
        ) : null}
        <ul className="ds-component-doc__rules">
          {doExample ? <li className="ds-component-doc__do">Do: {doExample}</li> : null}
          {dontExample ? <li className="ds-component-doc__dont">Don&apos;t: {dontExample}</li> : null}
        </ul>
      </div>
      <div className="ds-component-doc__preview">{children}</div>
    </article>
  );
}
