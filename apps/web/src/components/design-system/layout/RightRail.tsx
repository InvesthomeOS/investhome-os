import type { HTMLAttributes, ReactNode } from 'react';

export interface RightRailProps extends HTMLAttributes<HTMLElement> {
  children?: ReactNode;
}

export function RightRail({ children, className, ...props }: RightRailProps) {
  return (
    <aside className={`ds-right-rail${className ? ` ${className}` : ''}`} {...props}>
      {children}
    </aside>
  );
}
