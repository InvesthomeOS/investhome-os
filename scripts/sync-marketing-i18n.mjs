/**
 * Sync missing marketing.* namespaces from en.json into tr.json with Turkish translations.
 * Also deep-fills missing leaf keys within existing namespaces.
 */
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const enPath = path.join(root, 'apps/web/messages/en.json');
const trPath = path.join(root, 'apps/web/messages/tr.json');

const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));
const tr = JSON.parse(fs.readFileSync(trPath, 'utf8'));

/** Exact phrase map (English → Turkish). Longer phrases first after sort. */
const PHRASES = {
  'Marketing Leads': 'Pazarlama Leadleri',
  'Acquisition context view — references canonical Sales leads and CRM contacts.':
    'Edinme bağlamı görünümü — kanonik Satış leadleri ve CRM kişilerine referans verir.',
  'Ready for handoff': 'Devir için hazır',
  'Lead acquisition context': 'Lead edinme bağlamı',
  'Handoff status': 'Devir durumu',
  'UTM source': 'UTM kaynağı',
  'UTM Source': 'UTM Kaynağı',
  'Marketing score': 'Pazarlama skoru',
  'Handoff blockers': 'Devir engelleri',
  'Lead Sources': 'Lead Kaynakları',
  'Configure acquisition sources, hierarchy, and tracking.':
    'Edinme kaynaklarını, hiyerarşiyi ve izlemeyi yapılandırın.',
  'New Source': 'Yeni Kaynak',
  'Source hierarchy': 'Kaynak hiyerarşisi',
  'Tracking readiness': 'İzleme hazırlığı',
  'Tracking code': 'İzleme kodu',
  'Content Studio': 'İçerik Stüdyosu',
  'Create, review, and publish marketing content': 'Pazarlama içeriği oluşturun, inceleyin ve yayınlayın',
  'New Content': 'Yeni İçerik',
  'Access denied': 'Erişim reddedildi',
  'You need content publishing permissions to view this page.':
    'Bu sayfayı görüntülemek için içerik yayınlama yetkisi gerekir.',
  'Unable to load content': 'İçerik yüklenemedi',
  'No content yet': 'Henüz içerik yok',
  'Create your first content item to start the production pipeline.':
    'Üretim hattını başlatmak için ilk içerik öğenizi oluşturun.',
  'Search content…': 'İçerik ara…',
  'Filter by status': 'Duruma göre filtrele',
  'All statuses': 'Tüm durumlar',
  'View mode': 'Görünüm modu',
  'Not set': 'Ayarlanmadı',
  'Page {page} of {pages}': 'Sayfa {page} / {pages}',
  'Total content': 'Toplam içerik',
  'In review': 'İncelemede',
  'In Production': 'Üretimde',
  'Internal Review': 'İç İnceleme',
  'Pending Approval': 'Onay Bekliyor',
  'Publishing readiness': 'Yayın hazırlığı',
  'Content detail sections': 'İçerik detay bölümleri',
  'Create Content': 'İçerik Oluştur',
  'Guided content creation workflow': 'Rehberli içerik oluşturma iş akışı',
  'Complete {step} in the content detail view after creation.':
    'Oluşturduktan sonra {step} adımını içerik detay görünümünde tamamlayın.',
  'Blog post': 'Blog yazısı',
  'Social post': 'Sosyal gönderi',
  'Landing page': 'Landing sayfası',
  'Ad creative': 'Reklam kreatifi',
  '← Content Studio': '← İçerik Stüdyosu',
  'Loading content…': 'İçerik yükleniyor…',
  'You do not have permission to view this content.': 'Bu içeriği görüntüleme yetkiniz yok.',
  'Organic social publishing with provider-aware readiness.':
    'Sağlayıcı farkındalıklı hazırlık ile organik sosyal yayınlama.',
  'New Post': 'Yeni Gönderi',
  'No social posts yet': 'Henüz sosyal gönderi yok',
  'Create a post to schedule or publish once a provider is connected.':
    'Sağlayıcı bağlandıktan sonra planlamak veya yayınlamak için bir gönderi oluşturun.',
  'Consent-aware email campaigns with deliverability checks.':
    'Teslim edilebilirlik kontrolleri ile onay odaklı e-posta kampanyaları.',
  'New Campaign': 'Yeni Kampanya',
  'No email campaigns yet': 'Henüz e-posta kampanyası yok',
  'Create a campaign and complete the wizard before scheduling.':
    'Planlamadan önce bir kampanya oluşturun ve sihirbazı tamamlayın.',
  'Template-gated WhatsApp campaigns and conversations.':
    'Şablon kontrollü WhatsApp kampanyaları ve konuşmaları.',
  'No WhatsApp campaigns yet': 'Henüz WhatsApp kampanyası yok',
  'Connect WhatsApp and approve templates before sending.':
    'Göndermeden önce WhatsApp bağlayın ve şablonları onaylayın.',
  'SMS campaigns with segment validation and opt-out compliance.':
    'Segment doğrulama ve çıkış uyumluluğu ile SMS kampanyaları.',
  'No SMS campaigns yet': 'Henüz SMS kampanyası yok',
  'Create a campaign with opt-out text before scheduling.':
    'Planlamadan önce çıkış metni içeren bir kampanya oluşturun.',
  'Define and manage target audiences with consent-aware membership.':
    'Onay odaklı üyelik ile hedef kitleleri tanımlayın ve yönetin.',
  'New Audience': 'Yeni Kitle',
  'Back to audiences': 'Kitlelere dön',
  'No audiences yet': 'Henüz kitle yok',
  'Create an audience to target contacts and companies.':
    'Kişileri ve şirketleri hedeflemek için bir kitle oluşturun.',
  'Audience detail sections': 'Kitle detay bölümleri',
  'Audience not found': 'Kitle bulunamadı',
  'This audience does not exist or you do not have access.':
    'Bu kitle mevcut değil veya erişiminiz yok.',
  'Member count': 'Üye sayısı',
  'No description': 'Açıklama yok',
  'No members': 'Üye yok',
  'Contact / Company': 'Kişi / Şirket',
  'Why included / excluded': 'Neden dahil / hariç',
  'No linked segments': 'Bağlı segment yok',
  'Add segments during audience setup or link them from campaign planning.':
    'Kitle kurulumunda segment ekleyin veya kampanya planlamasından bağlayın.',
  '{count} segment reference(s) could not be resolved': '{count} segment referansı çözülemedi',
  'No linked campaigns': 'Bağlı kampanya yok',
  "Campaigns reference audiences during planning. Link this audience from a campaign's audience step.":
    'Kampanyalar planlama sırasında kitlelere referans verir. Bu kitleyi kampanyanın kitle adımından bağlayın.',
  'Browse campaigns': 'Kampanyalara göz at',
  'No consent requirements configured': 'Onay gereksinimi yapılandırılmadı',
  'Set consent requirements in audience settings or during the creation wizard.':
    'Onay gereksinimlerini kitle ayarlarında veya oluşturma sihirbazında belirleyin.',
  'Consent requirements': 'Onay gereksinimleri',
  'Readiness blockers': 'Hazırlık engelleri',
  'No activity yet': 'Henüz aktivite yok',
  'Audience changes and membership updates for {id} will appear here when activity tracking is enabled.':
    'Aktivite izleme etkinleştirildiğinde {id} için kitle değişiklikleri ve üyelik güncellemeleri burada görünür.',
  'Audience name': 'Kitle adı',
  'Save changes': 'Değişiklikleri kaydet',
  'Refresh membership': 'Üyeliği yenile',
  'Changes saved': 'Değişiklikler kaydedildi',
  'Create Audience': 'Kitle Oluştur',
  'Save draft': 'Taslağı kaydet',
  'Draft saved locally': 'Taslak yerel olarak kaydedildi',
  'Audience mode': 'Kitle modu',
  'Primary language': 'Birincil dil',
  'Consent policy': 'Onay politikası',
  'Target region': 'Hedef bölge',
  'Exclusion notes': 'Hariç tutma notları',
  'Refresh cadence': 'Yenileme sıklığı',
  'Provider synced': 'Sağlayıcı senkron',
  'Marketing consent': 'Pazarlama onayı',
  'Transactional only': 'Yalnızca işlemsel',
  'Contact selection is configured after creation from CRM-linked records.':
    'Kişi seçimi oluşturma sonrasında CRM bağlantılı kayıtlardan yapılandırılır.',
  'Link existing segments or create new ones from the Segments workspace.':
    'Mevcut segmentleri bağlayın veya Segmentler çalışma alanından yenilerini oluşturun.',
  'Channel eligibility is evaluated at send time based on consent and provider rules.':
    'Kanal uygunluğu gönderim anında onay ve sağlayıcı kurallarına göre değerlendirilir.',
  'Build rule-based segments with server-side calculation.':
    'Sunucu tarafı hesaplama ile kural tabanlı segmentler oluşturun.',
  'New Segment': 'Yeni Segment',
  'Not calculated': 'Hesaplanmadı',
  'Create Segment': 'Segment Oluştur',
  'Segment name': 'Segment adı',
  'Create segment': 'Segment oluştur',
  'AI Marketing Intelligence': 'Yapay Zeka Pazarlama Zekâsı',
  'Executive AI dashboard, copilot, insights, and prediction frameworks.':
    'Yönetici YZ panosu, yardımcı, içgörüler ve tahmin çerçeveleri.',
  'Answers derive from connected operational data only. Predictions show Unknown until a model pipeline is connected.':
    'Yanıtlar yalnızca bağlı operasyonel verilerden türetilir. Model hattı bağlanana kadar tahminler Bilinmiyor gösterir.',
  'Executive AI Dashboard': 'Yönetici YZ Panosu',
  'AI Copilot': 'YZ Asistanı',
  'Insight Center': 'İçgörü Merkezi',
  'Prediction Frameworks': 'Tahmin Çerçeveleri',
  'Executive Briefings': 'Yönetici Özetleri',
  'Marketing health, insights, recommendations, and prediction confidence.':
    'Pazarlama sağlığı, içgörüler, öneriler ve tahmin güveni.',
  'You do not have permission to view AI marketing intelligence.':
    'YZ pazarlama zekâsını görüntüleme yetkiniz yok.',
  'Contact your administrator for AI access.': 'YZ erişimi için yöneticinize başvurun.',
  'Unable to load AI dashboard.': 'YZ panosu yüklenemedi.',
  'Executive Summary': 'Yönetici Özeti',
  'Marketing Health': 'Pazarlama Sağlığı',
  'Prediction Confidence': 'Tahmin Güveni',
  'Lead Quality': 'Lead Kalitesi',
  'Critical Insights': 'Kritik İçgörüler',
  'Campaign Recommendations': 'Kampanya Önerileri',
  'Anomaly Alerts': 'Anomali Uyarıları',
  'Executive Briefing': 'Yönetici Özeti',
  'ML model pipeline not connected.': 'ML model hattı bağlı değil.',
  'No Insights': 'İçgörü yok',
  'Insights appear when operational data or alerts are available.':
    'İçgörüler operasyonel veri veya uyarılar mevcut olduğunda görünür.',
  'No Recommendations': 'Öneri yok',
  'Recommendations require connected campaign and analytics data.':
    'Öneriler bağlı kampanya ve analitik verisi gerektirir.',
  'Overall Marketing Health': 'Genel Pazarlama Sağlığı',
  'Conversion Funnel': 'Dönüşüm Hunisi',
  'Channel Performance': 'Kanal Performansı',
  'Campaign Projects': 'Kampanya Projeleri',
  'Lead & Audience Metrics': 'Lead ve Kitle Metrikleri',
  'Tracking Health': 'İzleme Sağlığı',
  'Partially connected': 'Kısmen bağlı',
  'Not connected': 'Bağlı değil',
  'Authentication required': 'Kimlik doğrulama gerekli',
  'Permission restricted': 'Yetki kısıtlı',
  'No data': 'Veri yok',
  'Pending approval': 'Onay bekliyor',
  'Build and manage marketing workflow automations.':
    'Pazarlama iş akışı otomasyonlarını oluşturun ve yönetin.',
};

const WORD_MAP = {
  Context: 'Bağlam',
  Handoff: 'Devir',
  Campaign: 'Kampanya',
  Campaigns: 'Kampanyalar',
  Total: 'Toplam',
  Blocked: 'Engelli',
  Active: 'Aktif',
  Draft: 'Taslak',
  Name: 'Ad',
  Type: 'Tür',
  Status: 'Durum',
  Size: 'Boyut',
  Mode: 'Mod',
  Language: 'Dil',
  Readiness: 'Hazırlık',
  Overview: 'Genel Bakış',
  Members: 'Üyeler',
  Segments: 'Segmentler',
  Consent: 'Onay',
  Activity: 'Aktivite',
  Settings: 'Ayarlar',
  Description: 'Açıklama',
  Back: 'Geri',
  Next: 'İleri',
  Previous: 'Önceki',
  Cancel: 'İptal',
  Create: 'Oluştur',
  Step: 'Adım',
  Basics: 'Temel',
  Contacts: 'Kişiler',
  Channels: 'Kanallar',
  Geography: 'Coğrafya',
  Exclusions: 'Hariç tutmalar',
  Review: 'İnceleme',
  Confirm: 'Onayla',
  Static: 'Statik',
  Dynamic: 'Dinamik',
  Hybrid: 'Hibrit',
  Mixed: 'Karma',
  Manual: 'Manuel',
  Daily: 'Günlük',
  Weekly: 'Haftalık',
  Included: 'Dahil',
  Unknown: 'Bilinmiyor',
  Yes: 'Evet',
  No: 'Hayır',
  Segment: 'Segment',
  Rules: 'Kurallar',
  Calculation: 'Hesaplama',
  Calculated: 'Hesaplandı',
  Title: 'Başlık',
  Scheduled: 'Planlandı',
  Updated: 'Güncellendi',
  Published: 'Yayınlandı',
  Expired: 'Süresi doldu',
  Archived: 'Arşivlendi',
  Approved: 'Onaylandı',
  Idea: 'Fikir',
  Requested: 'Talep edildi',
  Briefing: 'Brifing',
  Brief: 'Brif',
  Editor: 'Editör',
  Versions: 'Sürümler',
  Assets: 'Varlıklar',
  Approvals: 'Onaylar',
  Objective: 'Hedef',
  Audience: 'Kitle',
  Projects: 'Projeler',
  Format: 'Biçim',
  Table: 'Tablo',
  Grid: 'Izgara',
  Pipeline: 'Hat',
  Calendar: 'Takvim',
  Posts: 'Gönderiler',
  Provider: 'Sağlayıcı',
  Post: 'Gönderi',
  Email: 'E-posta',
  Social: 'Sosyal',
  Loading: 'Yükleniyor',
  Error: 'Hata',
  Syncing: 'Senkronize ediliyor',
  Delayed: 'Gecikmeli',
  Recommendations: 'Öneriler',
  Predictions: 'Tahminler',
  Anomalies: 'Anomaliler',
  Briefings: 'Özetler',
  Hub: 'Merkez',
  Dashboard: 'Pano',
  Copilot: 'Asistan',
  Insights: 'İçgörüler',
  Unknown: 'Bilinmiyor',
  KPIs: 'KPI’lar',
  Reports: 'Raporlar',
  Budgets: 'Bütçeler',
  Events: 'Etkinlikler',
  Templates: 'Şablonlar',
  Brand: 'Marka',
  Forms: 'Formlar',
  Source: 'Kaynak',
  Code: 'Kod',
  Actions: 'İşlemler',
  Delete: 'Sil',
  Duplicate: 'Kopyala',
  Pause: 'Duraklat',
  Activate: 'Etkinleştir',
  Archive: 'Arşivle',
  Metrics: 'Metrikler',
  Logs: 'Günlükler',
  Trigger: 'Tetikleyici',
  Executions: 'Yürütmeler',
  Paused: 'Duraklatıldı',
  Completed: 'Tamamlandı',
  Cancelled: 'İptal edildi',
  Planning: 'Planlama',
  Scheduled: 'Planlandı',
};

function translateString(value) {
  if (typeof value !== 'string') return value;
  if (PHRASES[value]) return PHRASES[value];

  // Prefer longer phrase matches
  const sorted = Object.keys(PHRASES).sort((a, b) => b.length - a.length);
  for (const en of sorted) {
    if (value.includes(en)) {
      value = value.split(en).join(PHRASES[en]);
    }
  }

  // Whole-word replacements for short labels
  if (WORD_MAP[value]) return WORD_MAP[value];

  // Tokenized title-case phrases like "Lead Quality"
  const parts = value.split(' ');
  if (parts.length > 1 && parts.every((p) => /^[A-Za-z{}/…—\-',.]+$/.test(p) || p.includes('{'))) {
    const mapped = parts.map((p) => WORD_MAP[p] ?? p);
    if (mapped.some((p, i) => p !== parts[i])) return mapped.join(' ');
  }

  return value;
}

function translateTree(node) {
  if (typeof node === 'string') return translateString(node);
  if (Array.isArray(node)) return node.map(translateTree);
  if (node && typeof node === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(node)) {
      out[k] = translateTree(v);
    }
    return out;
  }
  return node;
}

function deepFill(target, source) {
  let added = 0;
  for (const [key, value] of Object.entries(source)) {
    if (!(key in target)) {
      target[key] = translateTree(value);
      added += 1;
    } else if (
      value &&
      typeof value === 'object' &&
      !Array.isArray(value) &&
      target[key] &&
      typeof target[key] === 'object' &&
      !Array.isArray(target[key])
    ) {
      added += deepFill(target[key], value);
    }
  }
  return added;
}

if (!tr.marketing) tr.marketing = {};
const beforeMissing = Object.keys(en.marketing).filter((k) => !(k in tr.marketing));
const added = deepFill(tr.marketing, en.marketing);
const afterMissing = Object.keys(en.marketing).filter((k) => !(k in tr.marketing));

fs.writeFileSync(trPath, `${JSON.stringify(tr, null, 2)}\n`, 'utf8');

console.log(JSON.stringify({ beforeMissing, afterMissing, namespacesFilled: added }, null, 2));
