import type { ReactNode, SVGProps } from 'react';

export type IhIconName =
  | 'home'
  | 'executive'
  | 'sales'
  | 'investors'
  | 'projects'
  | 'inventory'
  | 'finance'
  | 'crm'
  | 'marketing'
  | 'documents'
  | 'design'
  | 'activity'
  | 'settings'
  | 'admin'
  | 'users'
  | 'roles'
  | 'permissions'
  | 'search'
  | 'bell'
  | 'user'
  | 'logout'
  | 'theme'
  | 'chevronLeft'
  | 'chevronRight'
  | 'chevronDown'
  | 'plus'
  | 'calendar'
  | 'sparkles'
  | 'alert'
  | 'check'
  | 'trendingUp'
  | 'barChart'
  | 'target'
  | 'clock'
  | 'inbox'
  | 'phone'
  | 'mail'
  | 'arrowRight'
  | 'refresh'
  | 'empty'
  | 'meeting'
  | 'quickAction';

export type IhIconSize = 'sm' | 'md' | 'lg' | 'nav' | number;

const ICON_SIZE_PX: Record<Exclude<IhIconSize, number>, number> = {
  sm: 14,
  md: 18,
  lg: 20,
  nav: 18,
};

type IconProps = SVGProps<SVGSVGElement> & {
  size?: IhIconSize;
};

function resolveIconSize(size: IhIconSize = 'lg'): number {
  return typeof size === 'number' ? size : ICON_SIZE_PX[size];
}

function BaseIcon({ size = 'lg', children, ...props }: IconProps & { children: ReactNode }) {
  const px = resolveIconSize(size);
  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

const PATHS: Record<IhIconName, ReactNode> = {
  home: (
    <>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 10v10h14V10" />
      <path d="M10 20v-6h4v6" />
    </>
  ),
  executive: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  sales: (
    <>
      <path d="M4 19V5" />
      <path d="M4 19h16" />
      <path d="M8 15v-4" />
      <path d="M12 15V8" />
      <path d="M16 15v-7" />
    </>
  ),
  investors: (
    <>
      <circle cx="9" cy="8" r="3" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M3.5 19c.8-3 2.8-4.5 5.5-4.5s4.7 1.5 5.5 4.5" />
      <path d="M14 19c.4-1.8 1.6-2.8 3-2.8 1.5 0 2.6 1 3 2.8" />
    </>
  ),
  projects: (
    <>
      <path d="M4 8h16v11H4z" />
      <path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M4 13h16" />
    </>
  ),
  inventory: (
    <>
      <path d="M3 8.5 12 4l9 4.5-9 4.5L3 8.5z" />
      <path d="M3 8.5v7L12 20l9-4.5v-7" />
      <path d="M12 13v7" />
    </>
  ),
  finance: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 7v10" />
      <path d="M9.5 9.5c.6-1 1.5-1.5 2.5-1.5 1.7 0 3 1 3 2.5S13.7 13 12 13s-3 1-3 2.5 1.3 2.5 3 2.5c1 0 1.9-.5 2.5-1.5" />
    </>
  ),
  crm: (
    <>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 19c1.2-3.2 3.6-5 7-5s5.8 1.8 7 5" />
    </>
  ),
  marketing: (
    <>
      <path d="M4 11v2a2 2 0 0 0 2 2h2l7 4V5l-7 4H6a2 2 0 0 0-2 2z" />
      <path d="M18 9.5a3.5 3.5 0 0 1 0 5" />
    </>
  ),
  documents: (
    <>
      <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h6" />
      <path d="M9 17h4" />
    </>
  ),
  design: (
    <>
      <path d="M12 3 4.5 7.5v9L12 21l7.5-4.5v-9L12 3z" />
      <path d="M12 12 4.5 7.5" />
      <path d="M12 12v9" />
      <path d="M12 12l7.5-4.5" />
    </>
  ),
  activity: (
    <>
      <path d="M4 12h4l2.5-6 3 12L16 12h4" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.2M12 18.8V21M4.9 6.5l1.6 1.6M17.5 15.9l1.6 1.6M3 12h2.2M18.8 12H21M4.9 17.5l1.6-1.6M17.5 8.1l1.6-1.6" />
    </>
  ),
  admin: (
    <>
      <path d="M12 3 4 6v5c0 4.5 3.2 8.4 8 10 4.8-1.6 8-5.5 8-10V6l-8-3z" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 19c.8-3 2.8-4.5 5.5-4.5s4.7 1.5 5.5 4.5" />
      <circle cx="17.5" cy="9" r="2.2" />
      <path d="M15 19c.3-1.5 1.4-2.4 2.5-2.4" />
    </>
  ),
  roles: (
    <>
      <rect x="4" y="5" width="16" height="14" rx="2" />
      <path d="M8 10h8" />
      <path d="M8 14h5" />
    </>
  ),
  permissions: (
    <>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16.5 16.5 21 21" />
    </>
  ),
  bell: (
    <>
      <path d="M6 16h12l-1.2-1.5a6 6 0 0 1-1.3-3.7V9a4.5 4.5 0 0 0-9 0v1.8c0 1.35-.45 2.67-1.3 3.7L6 16z" />
      <path d="M10 19a2 2 0 0 0 4 0" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 19c1.2-3.2 3.6-5 7-5s5.8 1.8 7 5" />
    </>
  ),
  logout: (
    <>
      <path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4" />
      <path d="M15 12H8" />
      <path d="M15 12l-3-3" />
      <path d="M15 12l-3 3" />
    </>
  ),
  theme: (
    <>
      <path d="M12 3a9 9 0 1 0 9 9h-9V3z" />
      <circle cx="12" cy="12" r="9" />
    </>
  ),
  chevronLeft: <path d="M14.5 5.5 8 12l6.5 6.5" />,
  chevronRight: <path d="M9.5 5.5 16 12l-6.5 6.5" />,
  chevronDown: <path d="M6 9.5 12 15.5 18 9.5" />,
  plus: (
    <>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </>
  ),
  calendar: (
    <>
      <rect x="3.5" y="5" width="17" height="15" rx="2" />
      <path d="M8 3.5V7" />
      <path d="M16 3.5V7" />
      <path d="M3.5 10h17" />
    </>
  ),
  sparkles: (
    <>
      <path d="M12 3l1.2 4.3L17.5 8.5 13.2 9.7 12 14l-1.2-4.3L6.5 8.5l4.3-1.2L12 3z" />
      <path d="M18.5 13.5 19 15.5 21 16l-2 .5-.5 2-.5-2-2-.5 2-.5.5-2z" />
    </>
  ),
  alert: (
    <>
      <path d="M12 4 3.5 19h17L12 4z" />
      <path d="M12 10v4" />
      <path d="M12 16.5h.01" />
    </>
  ),
  check: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="m8.5 12.5 2.5 2.5 4.5-5" />
    </>
  ),
  trendingUp: (
    <>
      <path d="M4 17 10 11l4 4 6-7" />
      <path d="M14 8h6v6" />
    </>
  ),
  barChart: (
    <>
      <path d="M4 19V5" />
      <path d="M4 19h16" />
      <path d="M8 15v-3" />
      <path d="M12 15V9" />
      <path d="M16 15v-6" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="1.5" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4.5l3 2" />
    </>
  ),
  inbox: (
    <>
      <path d="M4 13h4l1.5 2.5h5L16 13h4v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-5z" />
      <path d="M4 13 7 5h10l3 8" />
    </>
  ),
  phone: (
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z" />
  ),
  mail: (
    <>
      <rect x="3.5" y="5.5" width="17" height="13" rx="2" />
      <path d="m4.8 7.2 7.2 5.6 7.2-5.6" />
    </>
  ),
  arrowRight: (
    <>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 12a8 8 0 1 1-2.3-5.6" />
      <path d="M20 4v5h-5" />
    </>
  ),
  empty: (
    <>
      <rect x="4" y="5" width="16" height="14" rx="2" />
      <path d="M8 10h8" />
      <path d="M8 14h5" />
    </>
  ),
  meeting: (
    <>
      <rect x="3.5" y="5" width="17" height="15" rx="2" />
      <path d="M8 3.5V7" />
      <path d="M16 3.5V7" />
      <path d="M3.5 10h17" />
      <circle cx="10" cy="15" r="1.2" />
      <circle cx="14" cy="15" r="1.2" />
    </>
  ),
  quickAction: (
    <>
      <path d="M13 3 5 14h6l-1 7 9-12h-6l0-6z" />
    </>
  ),
};

export function IhIcon({ name, size = 'lg', className, ...props }: IconProps & { name: IhIconName }) {
  return (
    <BaseIcon size={size} className={className} {...props}>
      {PATHS[name]}
    </BaseIcon>
  );
}
