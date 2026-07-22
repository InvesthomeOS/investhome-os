export type DataClass = 'LIVE' | 'PARTIAL' | 'DEMO' | 'BLOCKED';

export type PortalLocale = 'tr' | 'en';

export interface PortalInvestor {
  id: string;
  fullName: string;
  email: string;
  phone: string;
  city: string;
  country: string;
  tier: 'standard' | 'preferred' | 'platinum';
  memberSince: string;
  language: PortalLocale;
  avatarInitials: string;
  twoFactorEnabled: boolean;
}

export interface PortfolioHolding {
  id: string;
  projectId: string;
  projectName: string;
  location: string;
  status: 'active' | 'construction' | 'rental' | 'exited';
  committed: number;
  invested: number;
  currentValue: number;
  ownershipPct: number;
  irr: number;
  roi: number;
  currency: 'TRY' | 'USD' | 'EUR';
  sparkline: number[];
}

export interface ProjectDetail {
  id: string;
  name: string;
  location: string;
  status: string;
  completionPct: number;
  overview: string;
  photos: { id: string; caption: string; tone: string }[];
  milestones: { id: string; title: string; date: string; status: 'done' | 'current' | 'upcoming' }[];
  budget: { label: string; planned: number; actual: number }[];
  news: { id: string; title: string; date: string; summary: string }[];
  rentalProjection: { month: string; amount: number }[];
  map: { lat: number; lng: number; label: string };
  documentIds: string[];
  investorId: string;
}

export interface Reservation {
  id: string;
  projectName: string;
  unit: string;
  status: 'held' | 'confirmed' | 'expired' | 'converted';
  reservedAt: string;
  expiresAt: string;
  amount: number;
  currency: 'TRY';
  investorId: string;
}

export interface Contract {
  id: string;
  title: string;
  projectName: string;
  status: 'draft' | 'pending_signature' | 'active' | 'completed';
  signedAt: string | null;
  value: number;
  currency: 'TRY';
  investorId: string;
}

export interface Payment {
  id: string;
  label: string;
  projectName: string;
  dueDate: string;
  paidAt: string | null;
  amount: number;
  currency: 'TRY';
  status: 'scheduled' | 'due' | 'paid' | 'overdue' | 'partial';
  investorId: string;
}

export interface RentalIncomeRow {
  id: string;
  projectName: string;
  period: string;
  gross: number;
  net: number;
  occupancy: number;
  currency: 'TRY';
  investorId: string;
}

export type DocumentCategory =
  | 'contracts'
  | 'statements'
  | 'kyc'
  | 'project'
  | 'tax'
  | 'legal'
  | 'other';

export interface PortalDocument {
  id: string;
  title: string;
  category: DocumentCategory;
  projectName: string | null;
  version: string;
  uploadedAt: string;
  sizeLabel: string;
  mime: string;
  investorId: string;
  canDownload: boolean;
  canPreview: boolean;
  classification: DataClass;
}

export interface ReportPreset {
  id: string;
  titleKey: string;
  descriptionKey: string;
  frequency: 'monthly' | 'quarterly' | 'annual' | 'on_demand';
  classification: DataClass;
}

export interface PortalMessage {
  id: string;
  threadId: string;
  from: string;
  subject: string;
  preview: string;
  body: string;
  at: string;
  read: boolean;
  investorId: string;
}

export interface PortalTask {
  id: string;
  title: string;
  dueDate: string;
  status: 'open' | 'done' | 'overdue';
  priority: 'low' | 'medium' | 'high';
  investorId: string;
}

export interface PortalMeeting {
  id: string;
  title: string;
  at: string;
  location: string;
  withWhom: string;
  investorId: string;
}

export type NotificationType =
  | 'payment'
  | 'document'
  | 'project'
  | 'message'
  | 'security'
  | 'system';

export interface PortalNotification {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  at: string;
  read: boolean;
  investorId: string;
}

export interface DeviceSession {
  id: string;
  device: string;
  location: string;
  lastActive: string;
  current: boolean;
}

export interface PortalSessionPayload {
  investorId: string;
  email: string;
  issuedAt: string;
}
