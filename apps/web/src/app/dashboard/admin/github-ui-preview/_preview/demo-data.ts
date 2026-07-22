/**
 * Demo-only fixtures for GitHub UI G1 preview.
 * Never wire to production APIs or mutations.
 */

export type PipelineStageId =
  | 'new_lead'
  | 'qualified'
  | 'meeting'
  | 'reservation'
  | 'contract'
  | 'closing'
  | 'won'
  | 'lost';

export type Opportunity = {
  id: string;
  title: string;
  company: string;
  investor: string;
  initials: string;
  stage: PipelineStageId;
  valueTry: number;
  probability: number;
  closeDate: string;
  owner: string;
  project: string;
  type: 'sales' | 'investor';
  email: string;
  phone: string;
  notes: string;
};

export type ProjectRow = {
  id: string;
  name: string;
  phase: string;
  progress: number;
  health: 'on_track' | 'watch' | 'risk';
  openIssues: number;
  due: string;
};

export type IssuePriority = 'urgent' | 'high' | 'medium' | 'low';

export type ConstructionIssue = {
  id: string;
  key: string;
  title: string;
  projectId: string;
  status: 'backlog' | 'ready' | 'in_progress' | 'blocked' | 'review' | 'done';
  priority: IssuePriority;
  assignee: string;
  initials: string;
  due: string;
  blockers: number;
  labels: string[];
  description: string;
};

export type MarketingKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  up: boolean;
};

export type CampaignRow = {
  id: string;
  name: string;
  channel: string;
  spend: number;
  leads: number;
  cpl: number;
  conv: number;
};

export type SourceRow = {
  source: string;
  sessions: number;
  leads: number;
  rate: number;
  revenue: number;
};

export const STAGE_META: {
  id: PipelineStageId;
  labelTr: string;
  tone: 'neutral' | 'info' | 'warn' | 'success' | 'danger';
}[] = [
  { id: 'new_lead', labelTr: 'Yeni Lead', tone: 'neutral' },
  { id: 'qualified', labelTr: 'Nitelikli', tone: 'info' },
  { id: 'meeting', labelTr: 'Toplantı', tone: 'info' },
  { id: 'reservation', labelTr: 'Rezervasyon', tone: 'warn' },
  { id: 'contract', labelTr: 'Sözleşme', tone: 'warn' },
  { id: 'closing', labelTr: 'Kapanış', tone: 'warn' },
  { id: 'won', labelTr: 'Kazanıldı', tone: 'success' },
  { id: 'lost', labelTr: 'Kaybedildi', tone: 'danger' },
];

export const OPPORTUNITIES: Opportunity[] = [
  {
    id: 'opp-01',
    title: 'Marina A-1204 · 3+1',
    company: 'Anadolu Capital',
    investor: 'Selin Yılmaz',
    initials: 'SY',
    stage: 'new_lead',
    valueTry: 18_400_000,
    probability: 20,
    closeDate: '2026-08-12',
    owner: 'Emre K.',
    project: 'Marina Residences',
    type: 'sales',
    email: 'selin@anadolucapital.demo',
    phone: '+90 532 100 01 01',
    notes: 'İlk keşif araması tamamlandı. Site ziyareti talep edildi.',
  },
  {
    id: 'opp-02',
    title: 'Skyline B-802 · Ofis',
    company: 'Bosphorus Partners',
    investor: 'Can Demir',
    initials: 'CD',
    stage: 'new_lead',
    valueTry: 22_100_000,
    probability: 15,
    closeDate: '2026-09-01',
    owner: 'Ayşe T.',
    project: 'Skyline Tower',
    type: 'investor',
    email: 'can@bosphorus.demo',
    phone: '+90 533 200 02 02',
    notes: 'Kurumsal yatırımcı; due diligence paketi bekleniyor.',
  },
  {
    id: 'opp-03',
    title: 'Green Park V-14',
    company: 'Ege Family Office',
    investor: 'Deniz Arslan',
    initials: 'DA',
    stage: 'qualified',
    valueTry: 9_750_000,
    probability: 35,
    closeDate: '2026-08-22',
    owner: 'Emre K.',
    project: 'Green Park Villas',
    type: 'sales',
    email: 'deniz@egefo.demo',
    phone: '+90 534 300 03 03',
    notes: 'Bütçe onaylı. Finansman seçenekleri karşılaştırılıyor.',
  },
  {
    id: 'opp-04',
    title: 'Marina A-905 · 2+1',
    company: 'Marmara Holdings',
    investor: 'Burak Şen',
    initials: 'BŞ',
    stage: 'qualified',
    valueTry: 11_200_000,
    probability: 40,
    closeDate: '2026-08-18',
    owner: 'Ayşe T.',
    project: 'Marina Residences',
    type: 'sales',
    email: 'burak@marmara.demo',
    phone: '+90 535 400 04 04',
    notes: 'İkinci görüşme planlandı.',
  },
  {
    id: 'opp-05',
    title: 'Central Hub · Blok C pay',
    company: 'Anadolu Capital',
    investor: 'Selin Yılmaz',
    initials: 'SY',
    stage: 'meeting',
    valueTry: 34_000_000,
    probability: 45,
    closeDate: '2026-09-15',
    owner: 'CFO Ofis',
    project: 'Central Hub Mixed',
    type: 'investor',
    email: 'selin@anadolucapital.demo',
    phone: '+90 532 100 01 01',
    notes: 'Yönetim kurulu sunumu 24 Temmuz.',
  },
  {
    id: 'opp-06',
    title: 'Skyline B-1201',
    company: 'Nova Living',
    investor: 'İpek Kara',
    initials: 'İK',
    stage: 'meeting',
    valueTry: 15_600_000,
    probability: 50,
    closeDate: '2026-08-28',
    owner: 'Emre K.',
    project: 'Skyline Tower',
    type: 'sales',
    email: 'ipek@novaliving.demo',
    phone: '+90 536 500 05 05',
    notes: 'Show-flat gezisi tamamlandı.',
  },
  {
    id: 'opp-07',
    title: 'Marina A-1502 · Penthouse',
    company: 'Bosphorus Partners',
    investor: 'Can Demir',
    initials: 'CD',
    stage: 'reservation',
    valueTry: 41_500_000,
    probability: 65,
    closeDate: '2026-08-08',
    owner: 'Ayşe T.',
    project: 'Marina Residences',
    type: 'sales',
    email: 'can@bosphorus.demo',
    phone: '+90 533 200 02 02',
    notes: 'Rezervasyon bedeli yatırıldı; sözleşme taslağı hazır.',
  },
  {
    id: 'opp-08',
    title: 'Green Park V-03',
    company: 'Ege Family Office',
    investor: 'Deniz Arslan',
    initials: 'DA',
    stage: 'reservation',
    valueTry: 8_900_000,
    probability: 60,
    closeDate: '2026-08-14',
    owner: 'Emre K.',
    project: 'Green Park Villas',
    type: 'sales',
    email: 'deniz@egefo.demo',
    phone: '+90 534 300 03 03',
    notes: 'Ödeme planı onay bekliyor.',
  },
  {
    id: 'opp-09',
    title: 'Skyline Ofis Katı 18',
    company: 'Marmara Holdings',
    investor: 'Burak Şen',
    initials: 'BŞ',
    stage: 'contract',
    valueTry: 27_800_000,
    probability: 75,
    closeDate: '2026-07-30',
    owner: 'Hukuk',
    project: 'Skyline Tower',
    type: 'investor',
    email: 'burak@marmara.demo',
    phone: '+90 535 400 04 04',
    notes: 'Sözleşme incelemesi 2. tur.',
  },
  {
    id: 'opp-10',
    title: 'Marina A-704',
    company: 'Nova Living',
    investor: 'İpek Kara',
    initials: 'İK',
    stage: 'closing',
    valueTry: 12_400_000,
    probability: 85,
    closeDate: '2026-07-24',
    owner: 'Ayşe T.',
    project: 'Marina Residences',
    type: 'sales',
    email: 'ipek@novaliving.demo',
    phone: '+90 536 500 05 05',
    notes: 'Tapu randevusu alındı.',
  },
  {
    id: 'opp-11',
    title: 'Central Hub · Ticari 4',
    company: 'Anadolu Capital',
    investor: 'Selin Yılmaz',
    initials: 'SY',
    stage: 'won',
    valueTry: 19_200_000,
    probability: 100,
    closeDate: '2026-07-10',
    owner: 'Emre K.',
    project: 'Central Hub Mixed',
    type: 'sales',
    email: 'selin@anadolucapital.demo',
    phone: '+90 532 100 01 01',
    notes: 'Kapandı — teslim planı operasyona aktarıldı.',
  },
  {
    id: 'opp-12',
    title: 'Green Park V-22',
    company: 'Atlas Gayrimenkul',
    investor: 'Murat Ak',
    initials: 'MA',
    stage: 'lost',
    valueTry: 7_100_000,
    probability: 0,
    closeDate: '2026-07-05',
    owner: 'Ayşe T.',
    project: 'Green Park Villas',
    type: 'sales',
    email: 'murat@atlas.demo',
    phone: '+90 537 600 06 06',
    notes: 'Rakip projeyi seçti — fiyat hassasiyeti.',
  },
  {
    id: 'opp-13',
    title: 'Skyline B-501',
    company: 'Bosphorus Partners',
    investor: 'Can Demir',
    initials: 'CD',
    stage: 'contract',
    valueTry: 16_750_000,
    probability: 70,
    closeDate: '2026-08-02',
    owner: 'Emre K.',
    project: 'Skyline Tower',
    type: 'sales',
    email: 'can@bosphorus.demo',
    phone: '+90 533 200 02 02',
    notes: 'Kredi onayı bekleniyor.',
  },
  {
    id: 'opp-14',
    title: 'Marina Ticari Zemin',
    company: 'Ege Family Office',
    investor: 'Deniz Arslan',
    initials: 'DA',
    stage: 'meeting',
    valueTry: 21_300_000,
    probability: 42,
    closeDate: '2026-09-05',
    owner: 'CFO Ofis',
    project: 'Marina Residences',
    type: 'investor',
    email: 'deniz@egefo.demo',
    phone: '+90 534 300 03 03',
    notes: 'Getiri modeli paylaşılacak.',
  },
];

export const PROJECTS: ProjectRow[] = [
  {
    id: 'prj-marina',
    name: 'Marina Residences',
    phase: 'İnşaat',
    progress: 72,
    health: 'on_track',
    openIssues: 18,
    due: '2026-11-30',
  },
  {
    id: 'prj-skyline',
    name: 'Skyline Tower',
    phase: 'Satış + İnşaat',
    progress: 58,
    health: 'watch',
    openIssues: 24,
    due: '2027-03-15',
  },
  {
    id: 'prj-green',
    name: 'Green Park Villas',
    phase: 'Temel',
    progress: 34,
    health: 'on_track',
    openIssues: 11,
    due: '2026-12-20',
  },
  {
    id: 'prj-hub',
    name: 'Central Hub Mixed',
    phase: 'Planlama',
    progress: 18,
    health: 'risk',
    openIssues: 9,
    due: '2027-06-01',
  },
];

export const ISSUE_COLUMNS: { id: ConstructionIssue['status']; labelTr: string }[] = [
  { id: 'backlog', labelTr: 'Backlog' },
  { id: 'ready', labelTr: 'Hazır' },
  { id: 'in_progress', labelTr: 'Devam' },
  { id: 'blocked', labelTr: 'Blokeli' },
  { id: 'review', labelTr: 'İnceleme' },
  { id: 'done', labelTr: 'Tamam' },
];

export const ISSUES: ConstructionIssue[] = [
  {
    id: 'iss-01',
    key: 'MR-214',
    title: 'Kat 12 ıslak hacim su yalıtımı',
    projectId: 'prj-marina',
    status: 'in_progress',
    priority: 'high',
    assignee: 'Hasan Usta',
    initials: 'HU',
    due: '2026-07-22',
    blockers: 0,
    labels: ['Islak hacim', 'Kalite'],
    description: 'Banyo ve mutfak alanlarında membran testi sonrası ikinci kat.',
  },
  {
    id: 'iss-02',
    key: 'MR-208',
    title: 'Cephe panel montajı — güney',
    projectId: 'prj-marina',
    status: 'blocked',
    priority: 'urgent',
    assignee: 'Leyla M.',
    initials: 'LM',
    due: '2026-07-21',
    blockers: 2,
    labels: ['Cephe'],
    description: 'Vinç slotu ve panel tedarik gecikmesi.',
  },
  {
    id: 'iss-03',
    key: 'SK-119',
    title: 'Asansör kuyu betonarme kontrol',
    projectId: 'prj-skyline',
    status: 'review',
    priority: 'high',
    assignee: 'Mert Ç.',
    initials: 'MÇ',
    due: '2026-07-23',
    blockers: 0,
    labels: ['Yapı'],
    description: 'Şantiye şefi imza turu bekleniyor.',
  },
  {
    id: 'iss-04',
    key: 'SK-122',
    title: 'Mekanik oda havalandırma revizyonu',
    projectId: 'prj-skyline',
    status: 'ready',
    priority: 'medium',
    assignee: 'Ayşe T.',
    initials: 'AT',
    due: '2026-07-28',
    blockers: 0,
    labels: ['MEP'],
    description: 'Revizyon çizimleri onaylandı — saha başlangıcı.',
  },
  {
    id: 'iss-05',
    key: 'GP-055',
    title: 'Villa 14 temel demir bağlama',
    projectId: 'prj-green',
    status: 'in_progress',
    priority: 'high',
    assignee: 'Hasan Usta',
    initials: 'HU',
    due: '2026-07-25',
    blockers: 0,
    labels: ['Temel'],
    description: 'Demir kontrol listesi %80 tamam.',
  },
  {
    id: 'iss-06',
    key: 'GP-048',
    title: 'Şantiye giriş güvenlik bariyeri',
    projectId: 'prj-green',
    status: 'backlog',
    priority: 'low',
    assignee: 'Operasyon',
    initials: 'OP',
    due: '2026-08-05',
    blockers: 0,
    labels: ['İSG'],
    description: 'Tedarikçi teklifleri toplanacak.',
  },
  {
    id: 'iss-07',
    key: 'CH-031',
    title: 'İmar dosyası eksik evrak',
    projectId: 'prj-hub',
    status: 'blocked',
    priority: 'urgent',
    assignee: 'Hukuk',
    initials: 'HK',
    due: '2026-07-20',
    blockers: 3,
    labels: ['İzin'],
    description: 'Belediye ek belge talebi — kritik yol.',
  },
  {
    id: 'iss-08',
    key: 'MR-220',
    title: 'Ortak alan zemin kaplama numuneleri',
    projectId: 'prj-marina',
    status: 'ready',
    priority: 'medium',
    assignee: 'Leyla M.',
    initials: 'LM',
    due: '2026-07-29',
    blockers: 0,
    labels: ['İç mimari'],
    description: '3 alternatif numune onay panosuna.',
  },
  {
    id: 'iss-09',
    key: 'SK-130',
    title: 'Yangın merdiveni korkuluk montajı',
    projectId: 'prj-skyline',
    status: 'done',
    priority: 'medium',
    assignee: 'Mert Ç.',
    initials: 'MÇ',
    due: '2026-07-15',
    blockers: 0,
    labels: ['İSG'],
    description: 'Kabul tutanağı arşive yüklendi.',
  },
  {
    id: 'iss-10',
    key: 'MR-201',
    title: 'Beton numune laboratuvar sonuçları',
    projectId: 'prj-marina',
    status: 'review',
    priority: 'high',
    assignee: 'Kalite',
    initials: 'KQ',
    due: '2026-07-21',
    blockers: 0,
    labels: ['Kalite'],
    description: 'C35 sonuçları bekleniyor.',
  },
  {
    id: 'iss-11',
    key: 'GP-061',
    title: 'Peyzaj sulama hattı ön yerleşim',
    projectId: 'prj-green',
    status: 'backlog',
    priority: 'low',
    assignee: 'Peyzaj',
    initials: 'PY',
    due: '2026-08-12',
    blockers: 0,
    labels: ['Peyzaj'],
    description: 'Mimari ile koordinasyon notu.',
  },
  {
    id: 'iss-12',
    key: 'CH-028',
    title: 'Yatırımcı sunumu maliyet güncellemesi',
    projectId: 'prj-hub',
    status: 'in_progress',
    priority: 'high',
    assignee: 'CFO Ofis',
    initials: 'CF',
    due: '2026-07-24',
    blockers: 1,
    labels: ['Finans'],
    description: 'Bütçe sapma tablosu güncelleniyor.',
  },
  {
    id: 'iss-13',
    key: 'MR-225',
    title: 'Kat 14 elektrik pano montajı',
    projectId: 'prj-marina',
    status: 'backlog',
    priority: 'medium',
    assignee: 'MEP',
    initials: 'MP',
    due: '2026-08-01',
    blockers: 0,
    labels: ['MEP'],
    description: 'Malzeme sahaya geldi — planlama bekleniyor.',
  },
  {
    id: 'iss-14',
    key: 'MR-218',
    title: 'Ortak alan aydınlatma numune onayı',
    projectId: 'prj-marina',
    status: 'review',
    priority: 'medium',
    assignee: 'Leyla M.',
    initials: 'LM',
    due: '2026-07-26',
    blockers: 0,
    labels: ['İç mimari'],
    description: 'Mimari onay panosu tamamlanacak.',
  },
  {
    id: 'iss-15',
    key: 'MR-230',
    title: 'Otopark havalandırma fan bakımı',
    projectId: 'prj-marina',
    status: 'done',
    priority: 'low',
    assignee: 'Hasan Usta',
    initials: 'HU',
    due: '2026-07-12',
    blockers: 0,
    labels: ['MEP'],
    description: 'Periyodik bakım tutanağı arşivlendi.',
  },
  {
    id: 'iss-16',
    key: 'MR-232',
    title: 'Kat 10 seramik iş programı',
    projectId: 'prj-marina',
    status: 'ready',
    priority: 'high',
    assignee: 'Kalite',
    initials: 'KQ',
    due: '2026-07-27',
    blockers: 0,
    labels: ['İç mimari', 'Kalite'],
    description: 'Alt yüklenici ekibi pazartesi başlıyor.',
  },
];

export const MARKETING_KPIS: MarketingKpi[] = [
  { id: 'clicks', label: 'Tıklama', value: '48.2K', delta: '+12.4%', up: true },
  { id: 'leads', label: 'Lead', value: '1.284', delta: '+8.1%', up: true },
  { id: 'cpl', label: 'CPL', value: '₺2.140', delta: '−6.2%', up: true },
  { id: 'conv', label: 'Dönüşüm', value: '3.8%', delta: '+0.4pp', up: true },
  { id: 'spend', label: 'Harcama', value: '₺2.75M', delta: '+3.1%', up: false },
];

export const CONVERSION_SERIES = {
  labels: ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'],
  leads: [142, 168, 155, 190, 210, 124, 98],
  conversions: [18, 22, 19, 28, 31, 14, 11],
};

export const CAMPAIGNS: CampaignRow[] = [
  {
    id: 'c1',
    name: 'Marina Early Bird',
    channel: 'Meta + Search',
    spend: 420_000,
    leads: 186,
    cpl: 2260,
    conv: 4.2,
  },
  {
    id: 'c2',
    name: 'Skyline Soft Launch',
    channel: 'E-posta + WhatsApp',
    spend: 180_000,
    leads: 94,
    cpl: 1915,
    conv: 5.1,
  },
  {
    id: 'c3',
    name: 'Brand Always-On',
    channel: 'Display',
    spend: 95_000,
    leads: 41,
    cpl: 2317,
    conv: 2.4,
  },
  {
    id: 'c4',
    name: 'Green Park Açılış',
    channel: 'Search',
    spend: 210_000,
    leads: 112,
    cpl: 1875,
    conv: 3.9,
  },
];

export const SOURCES: SourceRow[] = [
  { source: 'Google Ads', sessions: 18240, leads: 412, rate: 2.3, revenue: 9_800_000 },
  { source: 'Meta Ads', sessions: 22110, leads: 368, rate: 1.7, revenue: 7_400_000 },
  { source: 'WhatsApp', sessions: 6420, leads: 214, rate: 3.3, revenue: 5_100_000 },
  { source: 'Organik / SEO', sessions: 9840, leads: 156, rate: 1.6, revenue: 3_200_000 },
  { source: 'Tavsiye', sessions: 2100, leads: 98, rate: 4.7, revenue: 4_600_000 },
];

export function formatTry(value: number): string {
  if (value >= 1_000_000) {
    const m = value / 1_000_000;
    return `₺${m.toLocaleString('tr-TR', { maximumFractionDigits: 1 })}M`;
  }
  return `₺${value.toLocaleString('tr-TR')}`;
}

export function formatShortDate(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' });
}
