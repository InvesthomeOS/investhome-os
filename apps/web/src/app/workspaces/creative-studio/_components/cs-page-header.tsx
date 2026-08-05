'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import type { Route } from 'next';

import { IhIcon, type IhIconName, type IhIconSize } from '@/components/icons/ih-icons';

export type CsPageHeaderBreadcrumb = {
  href?: string;
  label: string;
  current?: boolean;
};

export type CsPageHeaderProps = {
  title: string;
  subtitle?: string;
  titleIcon?: IhIconName;
  titleIconSize?: IhIconSize;
  backHref?: string;
  backLabel?: string;
  breadcrumbs?: CsPageHeaderBreadcrumb[];
  breadcrumbAria?: string;
  actions?: ReactNode;
  meta?: ReactNode;
  /** Extra content under title (e.g. Templates tabs). */
  belowTitle?: ReactNode;
  className?: string;
  copyClassName?: string;
  actionsClassName?: string;
  testId?: string;
};

/**
 * Shared Creative Studio page header shell.
 * Slots only — does not change workspace layout or workflows.
 */
export function CsPageHeader({
  title,
  subtitle,
  titleIcon,
  titleIconSize = 20,
  backHref,
  backLabel,
  breadcrumbs,
  breadcrumbAria,
  actions,
  meta,
  belowTitle,
  className,
  copyClassName,
  actionsClassName,
  testId,
}: CsPageHeaderProps) {
  const rootClass = ['cs-page-header', className].filter(Boolean).join(' ');
  const copyClass = ['cs-page-header__copy', copyClassName].filter(Boolean).join(' ');
  const actionsClass = ['cs-page-header__actions', actionsClassName]
    .filter(Boolean)
    .join(' ');

  return (
    <header className={rootClass} data-testid={testId}>
      <div className={copyClass}>
        {backHref && backLabel ? (
          <Link href={backHref as Route} className="cs-page-header__back">
            <IhIcon name="chevronLeft" size={12} />
            {backLabel}
          </Link>
        ) : null}
        {breadcrumbs && breadcrumbs.length > 0 ? (
          <nav aria-label={breadcrumbAria}>
            <ol className="cs-page-header__breadcrumb">
              {breadcrumbs.flatMap((crumb, index) => {
                const nodes: ReactNode[] = [];
                if (index > 0) {
                  nodes.push(
                    <li
                      key={`sep-${index}`}
                      className="cs-page-header__breadcrumb-sep"
                      aria-hidden="true"
                    >
                      /
                    </li>,
                  );
                }
                nodes.push(
                  crumb.current ? (
                    <li
                      key={`${crumb.label}-${index}`}
                      className="cs-page-header__breadcrumb-current"
                      aria-current="page"
                    >
                      {crumb.label}
                    </li>
                  ) : (
                    <li key={`${crumb.label}-${index}`}>
                      {crumb.href ? (
                        <Link href={crumb.href as Route}>{crumb.label}</Link>
                      ) : (
                        <span>{crumb.label}</span>
                      )}
                    </li>
                  ),
                );
                return nodes;
              })}
            </ol>
          </nav>
        ) : null}
        <h1 className="cs-page-header__title">
          {titleIcon ? <IhIcon name={titleIcon} size={titleIconSize} /> : null}
          {title}
        </h1>
        {subtitle ? <p className="cs-page-header__subtitle">{subtitle}</p> : null}
        {belowTitle}
      </div>
      {meta ? <div className="cs-page-header__meta">{meta}</div> : null}
      {actions ? <div className={actionsClass}>{actions}</div> : null}
    </header>
  );
}
