import type { HTMLAttributes, ReactNode } from 'react';

export type WidgetColumnSpan = 3 | 4 | 6 | 8 | 12;

export interface WidgetColumnProps extends HTMLAttributes<HTMLDivElement> {
  span?: WidgetColumnSpan;
  children?: ReactNode;
}

export function WidgetColumn({ span = 6, children, className, ...props }: WidgetColumnProps) {
  return (
    <div
      className={`ds-widget-column ds-widget-column--span-${span}${className ? ` ${className}` : ''}`}
      {...props}
    >
      {children}
    </div>
  );
}
