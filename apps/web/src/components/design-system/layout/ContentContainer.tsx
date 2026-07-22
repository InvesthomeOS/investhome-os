import type { HTMLAttributes, ReactNode } from 'react';

export interface ContentContainerProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

export function ContentContainer({ children, className, ...props }: ContentContainerProps) {
  return (
    <div className={`ds-content-container${className ? ` ${className}` : ''}`} {...props}>
      {children}
    </div>
  );
}
