import type { HTMLAttributes, ReactNode } from 'react';

export interface AppPageProps extends HTMLAttributes<HTMLElement> {
  children?: ReactNode;
}

export function AppPage({ children, className, ...props }: AppPageProps) {
  return (
    <main className={`ds-app-page${className ? ` ${className}` : ''}`} {...props}>
      {children}
    </main>
  );
}
