/**
 * Patch TR marketing leaves that are still identical to EN.
 * Brand/product tokens (WhatsApp, SMS, UTM, Slug, etc.) are left as-is when intentional.
 */
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const trPath = path.join(root, 'apps/web/messages/tr.json');
const tr = JSON.parse(fs.readFileSync(trPath, 'utf8'));

/** Dot-path → Turkish value */
const PATCHES = {
  'quickActions.title': 'Hızlı işlemler',
  'quickActions.empty': 'Rolünüz için hızlı işlem yok.',
  'quickActions.createLeadSource': 'Lead Kaynağı Oluştur',
  'quickActions.createLandingPage': 'Landing Sayfası Oluştur',
  'quickActions.whatsappCampaign': 'WhatsApp Kampanyası',
  'quickActions.uploadAsset': 'Varlık Yükle',
  'quickActions.requestApproval': 'Onay Talep Et',
  'quickActions.addBudget': 'Bütçe Ekle',
  'quickActions.openCalendar': 'Takvimi Aç',
  'quickActions.openAnalytics': 'Analitiği Aç',
  'quickActions.createCampaign': 'Kampanya Oluştur',
  'quickActions.createForm': 'Form Oluştur',
  'quickActions.scheduleSocial': 'Sosyal Planla',
  'quickActions.createEvent': 'Etkinlik Oluştur',
  'quickActions.emailCampaign': 'E-posta Kampanyası',

  'dashboard.subtitle': 'Kampanya özeti ve çalışma alanı metrikleri',
  'dashboard.loading': 'Pano yükleniyor…',
  'dashboard.accessDenied': 'Pazarlama panosunu görüntüleme yetkiniz yok.',
  'dashboard.sections.widgets': 'Pano widget’ları',
  'dashboard.sections.alerts': 'Uyarılar',
  'dashboard.sections.recommendations': 'Önerilen Aksiyonlar',
  'dashboard.widgets.upcoming_events': 'Yaklaşan Etkinlikler',
  'dashboard.widgets.lead_source_performance': 'Lead Kaynak Performansı',
  'dashboard.widgets.attribution_summary': 'Atıf Özeti',
  'dashboard.widgets.alerts': 'Uyarılar',
  'dashboard.widgets.recommended_actions': 'Önerilen Aksiyonlar',
  'dashboard.widgets.quick_actions': 'Hızlı İşlemler',
  'dashboard.widgetStates.error': 'Bu widget yüklenemedi',
  'dashboard.widgetStates.not_connected': 'Sağlayıcı bağlı değil',
  'dashboard.widgetStates.empty': 'Henüz veri yok',

  'analytics.widgetStates.error': 'Yüklenemedi',
  'analytics.widgetStates.unknown': 'Bilinmiyor — veri kaynağı bağlı değil',

  'ai.tabs.ariaLabel': 'YZ pazarlama zekâsı bölümleri',
  'ai.dashboard.noAnomaliesHint': 'Bağlı veri kaynaklarında anomali tespit edilmedi.',
  'ai.copilot.disclaimer':
    'Asistan kural tabanlı sorgu ayrıştırması kullanır — üretici YZ değildir. Güven açıklanır; uydurma sonuç yok.',
  'ai.copilot.ask': 'Sor',
  'ai.insights.accessDeniedHint': 'YZ görüntüleme yetkisine ihtiyacınız var.',
  'ai.insights.allCategories': 'Tümü',
  'ai.insights.noInsightsHint': 'Bağlı veri kaynaklarından içgörü yok.',
  'ai.insights.categories.landing_page': 'Landing Sayfası',
  'ai.insights.categories.form': 'Form',
  'ai.recommendations.accessDeniedHint': 'YZ görüntüleme yetkisine ihtiyacınız var.',
  'ai.recommendations.evidenceNote': 'Kabul öncesi öneriler kanıt referansı gerektirir.',
  'ai.recommendations.noRecommendationsHint':
    'Yeterli operasyonel kanıt olduğunda öneriler görünür.',
  'ai.predictions.accessDeniedHint': 'YZ görüntüleme yetkisine ihtiyacınız var.',
  'ai.anomalies.accessDeniedHint': 'YZ görüntüleme yetkisine ihtiyacınız var.',
  'ai.anomalies.noAnomaliesHint': 'Anomali tespit edilmedi.',
  'ai.briefings.accessDeniedHint': 'YZ görüntüleme yetkisine ihtiyacınız var.',
  'ai.settings.accessDeniedHint': 'YZ görüntüleme yetkisine ihtiyacınız var.',

  'modules.campaigns.description': 'Pazarlama kampanyalarını planlayın, başlatın ve yönetin.',
  'modules.campaigns.detailTitle': 'Kampanya Detayı',
  'modules.campaigns.detailDescription': 'Kampanya yapılandırması, kanallar ve performans.',
  'modules.audiences.description': 'Hedef kitleleri tanımlayın ve yönetin.',
  'modules.segments.description': 'Statik, dinamik ve davranışsal kitle segmentleri.',
  'modules.leads.description': 'Satış ve CRM’e bağlı pazarlama lead bağlamı.',
  'modules.sources.description': 'Lead edinme kaynaklarını izleyin ve yapılandırın.',
  'modules.contentStudio.description': 'Pazarlama içerik varlıklarını oluşturun ve yönetin.',
  'modules.social.description': 'Organik ve ücretli sosyal içerik planlama.',
  'modules.email.description': 'E-posta kampanyaları ve şablonlar.',
  'modules.whatsapp.description': 'WhatsApp mesajlaşma kampanyaları.',
  'modules.sms.description': 'SMS kampanyaları ve uyumluluk.',
  'modules.advertising.description': 'Kanallar arası ücretli medya kampanyaları.',
  'modules.assets.description': 'Documents depolamasına bağlı kreatif varlıklar.',
  'modules.brand.description': 'Marka kuralları ve varlık kütüphanesi.',
  'modules.templates.description': 'Yeniden kullanılabilir içerik ve mesaj şablonları.',
  'modules.calendar.description': 'Pazarlama takvimi ve planlanmış aktiviteler.',
  'modules.attribution.title': 'Atıf',
  'modules.attribution.description': 'Çok dokunuşlu atıf ve UTM izleme.',
  'modules.analytics.description': 'Pazarlama performans analitiği ve dışa aktarımlar.',
  'modules.automations.title': 'Otomasyonlar',
  'modules.automations.description': 'Pazarlama iş akışı otomasyonları.',
  'modules.approvals.description': 'Kampanya, içerik ve bütçe onay iş akışları.',
  'modules.vendors.title': 'Tedarikçiler',
  'modules.vendors.description': 'Ajans ve tedarikçi yönetimi.',
  'modules.reports.description': 'Pazarlama raporları ve dışa aktarımlar.',

  'campaigns.emptyTitle': 'Henüz kampanya yok',
  'campaigns.emptyDescription': 'Planlama ve yürütmeye başlamak için ilk kampanyanızı oluşturun.',
  'campaigns.noData': 'Veri yok',
  'campaigns.bulk.selected': '{count} seçili',
  'campaigns.wizard.saveDraft': 'Taslağı kaydet',
  'campaigns.wizard.priorities.low': 'Düşük',
  'campaigns.wizard.priorities.normal': 'Normal',
  'campaigns.wizard.priorities.high': 'Yüksek',
  'campaigns.wizard.priorities.urgent': 'Acil',
  'campaigns.wizard.hints.projects':
    'Oluşturma sonrası kampanya detayından proje ve mülkleri bağlayın.',
  'campaigns.wizard.hints.audience':
    'Oluşturma sonrası kampanya detayından kitle ve segment atayın.',
  'campaigns.wizard.hints.channels':
    'Oluşturma sonrası kampanya detayından kanal atamalarını yapılandırın.',
  'campaigns.wizard.hints.approvals': 'Onay iş akışı kampanya oluşturma sonrasında yapılandırılır.',
  'campaigns.wizard.hints.targets': 'Performans hedefleri oluşturma sonrasında eklenebilir.',
  'campaigns.detail.notFound': 'Kampanya bulunamadı',
  'campaigns.detail.tabs.attribution': 'Atıf',
  'campaigns.detail.overview.conversions': 'Dönüşümler',
  'campaigns.detail.overview.noData': 'Veri yok',
  'campaigns.detail.overview.activationBlocked': 'Aktivasyon engellendi',
  'campaigns.detail.planning.executiveSummary': 'Yönetici özeti',
  'campaigns.detail.planning.objectives': 'Hedefler',
  'campaigns.detail.planning.milestones': 'Kilometre taşları',
  'campaigns.detail.planning.noMilestones': 'Henüz kilometre taşı yok',
  'campaigns.detail.planning.save': 'Özeti kaydet',
  'campaigns.detail.budget.title': 'Bütçe ve Dağılımlar',
  'campaigns.detail.budget.allocation': 'Dağılım',
  'campaigns.detail.budget.noData': 'Veri yok',
  'campaigns.detail.budget.noAllocations': 'Henüz bütçe dağılımı yok',
  'campaigns.detail.tracking.save': 'Kaydet',
  'campaigns.detail.tracking.validate': 'Doğrula',
  'campaigns.detail.leads.title': 'Kampanya Leadleri',
  'campaigns.detail.leads.subtitle':
    'Pazarlama lead bağlamı — kanonik Satış leadleri ve CRM kişilerine referans',
  'campaigns.detail.leads.emptyTitle': 'Henüz lead yok',
  'campaigns.detail.leads.emptyDescription':
    'Bu kampanya üzerinden edinilen leadler MarketingLeadContext ile burada görünür.',
  'campaigns.detail.leads.leadId': 'Satış Lead ID',
  'campaigns.detail.leads.contactId': 'CRM Kişi ID',
  'campaigns.detail.leads.createdAt': 'Edinilme',
  'campaigns.detail.shell.analytics.description':
    'Kampanya performans analitiği bağlı sağlayıcı entegrasyonları gerektirir.',
  'campaigns.detail.shell.attribution.title': 'Atıf',
  'campaigns.detail.shell.attribution.description': 'Çok dokunuşlu atıf verisi henüz mevcut değil.',
  'campaigns.detail.shell.attribution.state': 'Veri yok',
  'campaigns.detail.shell.audience.description': 'Kitle atamaları kampanya ayarlarından yönetilir.',
  'campaigns.detail.shell.audience.state': 'Ayarlardan yapılandırın',
  'campaigns.detail.shell.channels.description': 'Kanal atamaları kampanya bazında yapılandırılır.',
  'campaigns.detail.shell.channels.state': 'Kanalları yapılandırın',
  'campaigns.detail.shell.content.description': 'Bu kampanyaya içerik varlıkları bağlayın.',
  'campaigns.detail.shell.content.state': 'Bağlı içerik yok',
  'campaigns.detail.shell.landing-pages.description': 'Landing sayfası entegrasyonu henüz bağlı değil.',
  'campaigns.detail.shell.forms.description': 'Form entegrasyonu henüz bağlı değil.',
  'campaigns.detail.shell.approvals.description': 'Bu kampanya için onay geçmişi.',
  'campaigns.detail.shell.approvals.state': 'Onaylar çalışma alanında görüntüle',
  'campaigns.detail.shell.activity.description':
    'Kampanya yaşam döngüsü olayları CRM aktivite zaman çizelgesine yayınlanır.',
  'campaigns.detail.shell.activity.state': 'CRM Zaman Çizelgesinde görüntüle',

  'common.error': 'Veri yüklenemedi',
  'common.empty': 'Kayıt yok',
  'common.metric': 'Metrik',

  'audiences.segments.name': 'Segment',
  'audiences.wizard.create': 'Kitle oluştur',

  'automations.title': 'Otomasyonlar',
  'automations.wizard.trigger': 'Tetikleyici türü',

  'content.wizard.create': 'İçerik oluştur',

  'assets.loading': 'Varlıklar yükleniyor…',
  'assets.emptyTitle': 'Henüz varlık yok',

  'brand.loading': 'Marka profilleri yükleniyor…',
  'brand.emptyTitle': 'Henüz marka profili yok',
  'brand.emptyDescription': 'Kuralları ve iddiaları yönetmek için bir pazarlama marka profili oluşturun.',

  'templates.loading': 'Şablonlar yükleniyor…',
  'templates.emptyTitle': 'Henüz şablon yok',
  'templates.emptyDescription': 'E-posta, sosyal ve diğer kanallar için şablon oluşturun.',

  'calendar.subtitle': 'Planlanmış içerik ve kampanya aktiviteleri',
  'calendar.loading': 'Takvim yükleniyor…',
  'calendar.emptyTitle': 'Planlanmış içerik yok',

  'approvals.loading': 'Onaylar yükleniyor…',
  'approvals.emptyTitle': 'Bekleyen onay yok',

  'email.wizard.create': 'Taslak kampanya oluştur',
  'email.wizard.providerNotConnected':
    'E-posta sağlayıcısı bağlı değil. Taslak kaydedebilirsiniz; planlama ve gönderim Ayarlar’da sağlayıcı kurulumu gerektirir.',

  'forms.emptyTitle': 'Henüz form yok',

  'budgets.emptyTitle': 'Henüz bütçe yok',

  'events.emptyTitle': 'Henüz etkinlik yok',
  'events.emptyDescription': 'Lansman ve webinarları izlemek için pazarlama etkinlikleri oluşturun.',

  'reports.emptyTitle': 'Henüz rapor verisi yok',

  'settingsModule.emptyTitle': 'Yapılandırılmış sağlayıcı yok',
};

function setPath(obj, dotPath, value) {
  const parts = dotPath.split('.');
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const p = parts[i];
    if (cur[p] == null || typeof cur[p] !== 'object') {
      cur[p] = {};
    }
    cur = cur[p];
  }
  cur[parts[parts.length - 1]] = value;
}

function getPath(obj, dotPath) {
  return dotPath.split('.').reduce((o, p) => (o == null ? undefined : o[p]), obj);
}

let applied = 0;
let skipped = 0;
for (const [dot, value] of Object.entries(PATCHES)) {
  const current = getPath(tr.marketing, dot);
  if (current === undefined) {
    console.warn('MISSING_PATH', dot);
    skipped++;
    continue;
  }
  if (current === value) {
    skipped++;
    continue;
  }
  setPath(tr.marketing, dot, value);
  applied++;
}

fs.writeFileSync(trPath, `${JSON.stringify(tr, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({ applied, skipped, totalPatches: Object.keys(PATCHES).length }));
