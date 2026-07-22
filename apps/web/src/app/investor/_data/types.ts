export type InvestmentStatus = 'active' | 'pending' | 'matured' | 'exited';

export type InvestorTier = 'standard' | 'gold' | 'platinum';

export type TimelineEventType =
  | 'distribution'
  | 'document'
  | 'message'
  | 'investment'
  | 'signature'
  | 'task';

export type NotificationType = 'info' | 'action' | 'alert';

export type DistributionStatus = 'scheduled' | 'paid' | 'pending';

export interface InvestorProfile {
  id: string;
  name: string;
  email: string;
  avatarInitials: string;
  memberSince: string;
  investorTier: InvestorTier;
  phone: string;
}

export interface Investment {
  id: string;
  name: string;
  property: string;
  location: string;
  status: InvestmentStatus;
  investedAmount: number;
  currentValue: number;
  equity: number;
  roi: number;
  irr: number;
  currency: string;
  investedAt: string;
  projectedExitDate?: string;
}

export interface Distribution {
  id: string;
  investmentId: string;
  investmentName: string;
  amount: number;
  currency: string;
  scheduledDate: string;
  status: DistributionStatus;
}

export interface TimelineEvent {
  id: string;
  type: TimelineEventType;
  title: string;
  description: string;
  timestamp: string;
}

export interface InvestorNotification {
  id: string;
  title: string;
  message: string;
  read: boolean;
  timestamp: string;
  type: NotificationType;
}

export interface PendingDocument {
  id: string;
  title: string;
  investmentName: string;
  dueDate: string;
  requiresSignature: boolean;
}

export interface NextDistribution {
  date: string;
  amount: number;
  currency: string;
  investmentName: string;
}

export interface DashboardKpis {
  totalInvested: number;
  portfolioValue: number;
  estimatedEquity: number;
  annualCashFlow: number;
  projectedRoi: number;
  irr: number;
  nextDistribution: NextDistribution;
  unreadMessages: number;
  pendingDocuments: number;
  pendingSignatures: number;
  currency: string;
}

export interface InvestorNavItem {
  href: string;
  label: string;
  matchPaths?: string[];
}
