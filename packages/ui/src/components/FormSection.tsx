import type { ReactNode } from 'react';

export interface FormSectionProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export function FormSection({ title, children, className }: FormSectionProps) {
  return (
    <section className={`ih-form-section${className ? ` ${className}` : ''}`}>
      <h3 className="ih-form-section__title">{title}</h3>
      <div className="ih-form-section__body">{children}</div>
    </section>
  );
}
