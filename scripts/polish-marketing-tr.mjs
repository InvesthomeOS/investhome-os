/**
 * Re-translate English-looking leaf values under marketing.* in tr.json
 * using an expanded phrase glossary, preserving already-Turkish strings.
 */
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const enPath = path.join(root, 'apps/web/messages/en.json');
const trPath = path.join(root, 'apps/web/messages/tr.json');

const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));
const tr = JSON.parse(fs.readFileSync(trPath, 'utf8'));

const PHRASES = new Map(
  Object.entries({
    // Leads
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
    // Common
    'Access denied': 'Erişim reddedildi',
    'Not Connected': 'Bağlı değil',
    'Not connected': 'Bağlı değil',
    'No data': 'Veri yok',
    'Unknown': 'Bilinmiyor',
    'Loading…': 'Yükleniyor…',
    'Loading...': 'Yükleniyor…',
    'Yes': 'Evet',
    'No': 'Hayır',
    'Total': 'Toplam',
    'Active': 'Aktif',
    'Draft': 'Taslak',
    'Status': 'Durum',
    'Name': 'Ad',
    'Type': 'Tür',
    'Size': 'Boyut',
    'Mode': 'Mod',
    'Language': 'Dil',
    'Description': 'Açıklama',
    'Back': 'Geri',
    'Next': 'İleri',
    'Previous': 'Önceki',
    'Cancel': 'İptal',
    'Create': 'Oluştur',
    'Save draft': 'Taslağı kaydet',
    'Save changes': 'Değişiklikleri kaydet',
    'Apply': 'Uygula',
    'Reset': 'Sıfırla',
    'Search': 'Ara',
    'Retry': 'Yeniden dene',
    'Clear': 'Temizle',
    'Approve': 'Onayla',
    'Reject': 'Reddet',
    'Schedule': 'Planla',
    'Complete': 'Tamamla',
    'Pause': 'Duraklat',
    'Activate': 'Etkinleştir',
    'Archive': 'Arşivle',
    'Duplicate': 'Kopyala',
    'Delete': 'Sil',
    'Included': 'Dahil',
    'Overview': 'Genel Bakış',
    'Members': 'Üyeler',
    'Segments': 'Segmentler',
    'Campaigns': 'Kampanyalar',
    'Campaign': 'Kampanya',
    'Consent': 'Onay',
    'Activity': 'Aktivite',
    'Settings': 'Ayarlar',
    'Channels': 'Kanallar',
    'Channel': 'Kanal',
    'Content': 'İçerik',
    'Forms': 'Formlar',
    'Form': 'Form',
    'Assets': 'Varlıklar',
    'Approvals': 'Onaylar',
    'Budget': 'Bütçe',
    'Budgets': 'Bütçeler',
    'Spend': 'Harcama',
    'Leads': 'Leadler',
    'Start': 'Başlangıç',
    'End': 'Bitiş',
    'Title': 'Başlık',
    'Body': 'Gövde',
    'Post': 'Gönderi',
    'Posts': 'Gönderiler',
    'Provider': 'Sağlayıcı',
    'Readiness': 'Hazırlık',
    'Scheduled': 'Planlandı',
    'Published': 'Yayınlandı',
    'Archived': 'Arşivlendi',
    'Approved': 'Onaylandı',
    'Blocked': 'Engelli',
    'Pending': 'Beklemede',
    'Completed': 'Tamamlandı',
    'Cancelled': 'İptal edildi',
    'Planning': 'Planlama',
    'Paused': 'Duraklatıldı',
    'Error': 'Hata',
    'Syncing': 'Senkronize ediliyor',
    'Delayed': 'Gecikmeli',
    'Connected': 'Bağlı',
    'Default': 'Varsayılan',
    'Document': 'Belge',
    'Rights': 'Haklar',
    'Guidelines': 'Kılavuzlar',
    'Logos': 'Logolar',
    'Colors': 'Renkler',
    'Typography': 'Tipografi',
    'Voice': 'Ses',
    'Terminology': 'Terminoloji',
    'Legal': 'Yasal',
    'Monthly': 'Aylık',
    'Quarterly': 'Çeyreklik',
    'Board': 'Yönetim kurulu',
    'Country': 'Ülke',
    'Project': 'Proje',
    'Projects': 'Projeler',
    'Creative': 'Kreatif',
    'Landing Page': 'Landing Sayfası',
    'Landing Pages': 'Landing Sayfaları',
    'Revenue': 'Gelir',
    'Audience': 'Kitle',
    'Audiences': 'Kitleler',
    'Automation': 'Otomasyon',
    'Awareness': 'Farkındalık',
    'Reach': 'Erişim',
    'Engagement': 'Etkileşim',
    'Traffic': 'Trafik',
    'Lead Generation': 'Lead Üretimi',
    'Conversion': 'Dönüşüm',
    'Retention': 'Elde tutma',
    'Nurture': 'Besleme',
    'Retargeting': 'Yeniden hedefleme',
    'Other': 'Diğer',
    'Cards': 'Kartlar',
    'Timeline': 'Zaman çizelgesi',
    'Calendar': 'Takvim',
    'Table': 'Tablo',
    'Grid': 'Izgara',
    'Pipeline': 'Hat',
    'Basics': 'Temel',
    'Objective': 'Hedef',
    'Targets': 'Hedefler',
    'Ownership': 'Sahiplik',
    'Tracking': 'İzleme',
    'Scheduling': 'Planlama',
    'Personalisation': 'Kişiselleştirme',
    'Confirm': 'Onayla',
    'Preview': 'Önizleme',
    'Subject': 'Konu',
    'Sender': 'Gönderen',
    'Template': 'Şablon',
    'Variants': 'Varyantlar',
    'Format': 'Biçim',
    'Brief': 'Brif',
    'Editor': 'Editör',
    'Versions': 'Sürümler',
    'Slug': 'Slug',
    'Currency': 'Para birimi',
    'Planned': 'Planlanan',
    'Spent': 'Harcanan',
    'Event': 'Etkinlik',
    'Events': 'Etkinlikler',
    'Reports': 'Raporlar',
    'Source': 'Kaynak',
    'Code': 'Kod',
    'Metric': 'Metrik',
    'Metrics': 'Metrikler',
    'Actions': 'İşlemler',
    'Trigger': 'Tetikleyici',
    'Executions': 'Yürütmeler',
    'Logs': 'Günlükler',
    'Rules': 'Kurallar',
    'Calculation': 'Hesaplama',
    'Calculated': 'Hesaplandı',
    'Not calculated': 'Hesaplanmadı',
    'Static': 'Statik',
    'Dynamic': 'Dinamik',
    'Hybrid': 'Hibrit',
    'Mixed': 'Karma',
    'Manual': 'Manuel',
    'Daily': 'Günlük',
    'Weekly': 'Haftalık',
    'Contacts': 'Kişiler',
    'Geography': 'Coğrafya',
    'Exclusions': 'Hariç tutmalar',
    'Review': 'İnceleme',
    'Brand': 'Marka',
    'Social': 'Sosyal',
    'Email': 'E-posta',
    'KPIs': 'KPI’lar',
    'Idea': 'Fikir',
    'Requested': 'Talep edildi',
    'Briefing': 'Brifing',
    'In Production': 'Üretimde',
    'Internal Review': 'İç İnceleme',
    'Pending Approval': 'Onay Bekliyor',
    'Expired': 'Süresi doldu',
    'Updated': 'Güncellendi',
    'All types': 'Tüm türler',
    'All statuses': 'Tüm durumlar',
    'Missing Budget': 'Eksik Bütçe',
    'Missing Tracking': 'Eksik İzleme',
    'Missing budget': 'Eksik bütçe',
    'Missing tracking': 'Eksik izleme',
    'Include archived': 'Arşivlenenleri dahil et',
    'Submit for Approval': 'Onaya gönder',
    'Search campaigns…': 'Kampanya ara…',
    'Search content…': 'İçerik ara…',
    'Filter by status': 'Duruma göre filtrele',
    'View mode': 'Görünüm modu',
    'Not set': 'Ayarlanmadı',
    'Page {page} of {pages}': 'Sayfa {page} / {pages}',
    'Total content': 'Toplam içerik',
    'In review': 'İncelemede',
    'New Content': 'Yeni İçerik',
    'New Campaign': 'Yeni Kampanya',
    'New Audience': 'Yeni Kitle',
    'New Segment': 'Yeni Segment',
    'New Source': 'Yeni Kaynak',
    'New Post': 'Yeni Gönderi',
    'New Template': 'Yeni Şablon',
    'Create Content': 'İçerik Oluştur',
    'Create Audience': 'Kitle Oluştur',
    'Create Segment': 'Segment Oluştur',
    'Create segment': 'Segment oluştur',
    'Segment name': 'Segment adı',
    'Audience name': 'Kitle adı',
    'Campaign name': 'Kampanya adı',
    'Campaign code': 'Kampanya kodu',
    'Campaign type': 'Kampanya türü',
    'Start date': 'Başlangıç tarihi',
    'End date': 'Bitiş tarihi',
    'Budget amount': 'Bütçe tutarı',
    'Priority': 'Öncelik',
    'Objective & Type': 'Hedef ve Tür',
    'Projects & Properties': 'Projeler ve Mülkler',
    'Audience & Segments': 'Kitle ve Segmentler',
    'Review & Create': 'İncele ve Oluştur',
    'Save Draft': 'Taslağı kaydet',
    'Unable to create campaign': 'Kampanya oluşturulamadı',
    'Unable to load content': 'İçerik yüklenemedi',
    'Unable to load assets': 'Varlıklar yüklenemedi',
    'Unable to load brand center': 'Marka merkezi yüklenemedi',
    'Unable to load templates': 'Şablonlar yüklenemedi',
    'Unable to load calendar': 'Takvim yüklenemedi',
    'Unable to load approvals': 'Onaylar yüklenemedi',
    'Unable to load insights.': 'İçgörüler yüklenemedi.',
    'Unable to load recommendations.': 'Öneriler yüklenemedi.',
    'Unable to load predictions.': 'Tahminler yüklenemedi.',
    'Unable to load anomalies.': 'Anomaliler yüklenemedi.',
    'Unable to load briefing.': 'Özet yüklenemedi.',
    'Unable to load settings.': 'Ayarlar yüklenemedi.',
    'Unable to load AI dashboard.': 'YZ panosu yüklenemedi.',
    'You need campaign management permissions to view this page.':
      'Bu sayfayı görüntülemek için kampanya yönetim yetkisi gerekir.',
    'You need content publishing permissions to view this page.':
      'Bu sayfayı görüntülemek için içerik yayınlama yetkisi gerekir.',
    'You do not have permission to create campaigns.': 'Kampanya oluşturma yetkiniz yok.',
    'You do not have permission to view this content.': 'Bu içeriği görüntüleme yetkiniz yok.',
    'Plan, approve, launch, and monitor multi-channel campaigns':
      'Çok kanallı kampanyaları planlayın, onaylayın, başlatın ve izleyin',
    'All Campaigns': 'Tüm Kampanyalar',
    'My Campaigns': 'Kampanyalarım',
    'Create, review, and publish marketing content': 'Pazarlama içeriği oluşturun, inceleyin ve yayınlayın',
    'No content yet': 'Henüz içerik yok',
    'Create your first content item to start the production pipeline.':
      'Üretim hattını başlatmak için ilk içerik öğenizi oluşturun.',
    'Publishing readiness': 'Yayın hazırlığı',
    'Content detail sections': 'İçerik detay bölümleri',
    'Guided content creation workflow': 'Rehberli içerik oluşturma iş akışı',
    'Complete {step} in the content detail view after creation.':
      'Oluşturduktan sonra {step} adımını içerik detay görünümünde tamamlayın.',
    'Blog post': 'Blog yazısı',
    'Social post': 'Sosyal gönderi',
    'Landing page': 'Landing sayfası',
    'Ad creative': 'Reklam kreatifi',
    'Content type': 'İçerik türü',
    '← Content Studio': '← İçerik Stüdyosu',
    'Loading content…': 'İçerik yükleniyor…',
    'Content Studio': 'İçerik Stüdyosu',
    'Organic social publishing with provider-aware readiness.':
      'Sağlayıcı farkındalıklı hazırlık ile organik sosyal yayınlama.',
    'No social posts yet': 'Henüz sosyal gönderi yok',
    'Create a post to schedule or publish once a provider is connected.':
      'Sağlayıcı bağlandıktan sonra planlamak veya yayınlamak için bir gönderi oluşturun.',
    'Consent-aware email campaigns with deliverability checks.':
      'Teslim edilebilirlik kontrolleri ile onay odaklı e-posta kampanyaları.',
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
    'Refresh membership': 'Üyeliği yenile',
    'Changes saved': 'Değişiklikler kaydedildi',
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
    'Refresh policy': 'Yenileme politikası',
    'Contact selection is configured after creation from CRM-linked records.':
      'Kişi seçimi oluşturma sonrasında CRM bağlantılı kayıtlardan yapılandırılır.',
    'Link existing segments or create new ones from the Segments workspace.':
      'Mevcut segmentleri bağlayın veya Segmentler çalışma alanından yenilerini oluşturun.',
    'Channel eligibility is evaluated at send time based on consent and provider rules.':
      'Kanal uygunluğu gönderim anında onay ve sağlayıcı kurallarına göre değerlendirilir.',
    'Build rule-based segments with server-side calculation.':
      'Sunucu tarafı hesaplama ile kural tabanlı segmentler oluşturun.',
    'Lead Sources': 'Lead Kaynakları',
    'Configure acquisition sources, hierarchy, and tracking.':
      'Edinme kaynaklarını, hiyerarşiyi ve izlemeyi yapılandırın.',
    'Source hierarchy': 'Kaynak hiyerarşisi',
    'Tracking readiness': 'İzleme hazırlığı',
    'Tracking code': 'İzleme kodu',
    'Lead capture forms and field mapping.': 'Lead yakalama formları ve alan eşleme.',
    'Campaign landing pages and conversion paths.': 'Kampanya landing sayfaları ve dönüşüm yolları.',
    'Campaign budgets — planned and committed amounts.':
      'Kampanya bütçeleri — planlanan ve taahhüt edilen tutarlar.',
    'Budget records appear here when created for campaigns or channels.':
      'Kampanya veya kanallar için oluşturulduğunda bütçe kayıtları burada görünür.',
    'Webinars, launches, and marketing events.': 'Webinarlar, lansmanlar ve pazarlama etkinlikleri.',
    'Open analytics dashboard': 'Analitik panosunu aç',
    'Key metrics': 'Temel metrikler',
    'Full report exports are available from the Analytics dashboard when data sources are connected.':
      'Veri kaynakları bağlandığında tam rapor dışa aktarımları Analitik panosundan kullanılabilir.',
    'Workspace configuration and provider connections.':
      'Çalışma alanı yapılandırması ve sağlayıcı bağlantıları.',
    'Connect email, social, and advertising providers to enable channel features.':
      'Kanal özelliklerini etkinleştirmek için e-posta, sosyal ve reklam sağlayıcılarını bağlayın.',
    'This module is visible in navigation but actions remain disabled until the requirements below are met.':
      'Bu modül gezinmede görünür; aşağıdaki gereksinimler karşılanana kadar işlemler kapalı kalır.',
    'External provider required': 'Harici sağlayıcı gerekli',
    'Connect and authenticate the required marketing provider before using this module.':
      'Bu modülü kullanmadan önce gerekli pazarlama sağlayıcısını bağlayın ve kimlik doğrulayın.',
    'Backend integration in progress': 'Arka uç entegrasyonu devam ediyor',
    'Platform configuration required': 'Platform yapılandırması gerekli',
    'This capability depends on platform-wide vendor and finance configuration.':
      'Bu yetenek platform genelinde tedarikçi ve finans yapılandırmasına bağlıdır.',
    'Linked ad account with spend permissions': 'Harcama yetkili bağlı reklam hesabı',
    'Conversion pixel or server-side tracking': 'Dönüşüm pikseli veya sunucu tarafı izleme',
    'Event trigger and condition engine': 'Olay tetikleyici ve koşul motoru',
    'Reliable execution queue for workflow steps': 'İş akışı adımları için güvenilir yürütme kuyruğu',
    'Vendor registry in Finance workspace': 'Finans çalışma alanında tedarikçi kaydı',
    'Contract and PO approval workflow': 'Sözleşme ve satın alma onay iş akışı',
    'Spend reconciliation with campaign budgets': 'Kampanya bütçeleri ile harcama mutabakatı',
    'Creative assets linked to Documents storage — no duplicate file bytes':
      'Documents depolamaya bağlı kreatif varlıklar — yinelenen dosya baytı yok',
    'Register assets from Documents to track rights and usage.':
      'Hakları ve kullanımı izlemek için Documents üzerinden varlık kaydedin.',
    'Guidelines, terminology, and compliance for marketing content':
      'Pazarlama içeriği için kılavuzlar, terminoloji ve uyumluluk',
    'Brand Center': 'Marka Merkezi',
    'Reusable content templates with placeholder validation':
      'Yer tutucu doğrulamalı yeniden kullanılabilir içerik şablonları',
    'Marketing Calendar': 'Pazarlama Takvimi',
    'Schedule content to see it on the marketing calendar.':
      'Pazarlama takviminde görmek için içerik planlayın.',
    'Not scheduled': 'Planlanmadı',
    'Content, campaign, and budget approval queue': 'İçerik, kampanya ve bütçe onay kuyruğu',
    'Approval requests appear here when submitted.': 'Gönderildiğinde onay talepleri burada görünür.',
    'Email campaign wizard': 'E-posta kampanya sihirbazı',
    'Back to Email': 'E-postaya dön',
    'Draft saved': 'Taslak kaydedildi',
    'Connect an email provider before scheduling sends':
      'Gönderileri planlamadan önce bir e-posta sağlayıcısı bağlayın',
    'Select audience…': 'Kitle seçin…',
    'Sender profile': 'Gönderen profili',
    'Select sender…': 'Gönderen seçin…',
    'Subject line': 'Konu satırı',
    'Preview text': 'Önizleme metni',
    'Select template…': 'Şablon seçin…',
    'Schedule send': 'Gönderimi planla',
    'Unsubscribe required': 'Abonelikten çıkış gerekli',
    'Unsubscribe link present in content': 'İçerikte abonelikten çıkış bağlantısı mevcut',
    'Lead generation': 'Lead üretimi',
    'Personalisation tokens are applied from the selected template and audience fields.':
      'Kişiselleştirme belirteçleri seçili şablon ve kitle alanlarından uygulanır.',
    // AI
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
    'Natural language analytics from connected data only.':
      'Yalnızca bağlı verilerden doğal dil analitiği.',
    'Copilot access denied': 'Asistan erişimi reddedildi',
    'You need copilot query permission.': 'Asistan sorgu yetkisine ihtiyacınız var.',
    'Ask about campaigns, leads, performance, or budget allocation…':
      'Kampanyalar, leadler, performans veya bütçe dağılımı hakkında sorun…',
    'e.g. Which is the best campaign by linked leads?':
      'örn. Bağlı leadlere göre en iyi kampanya hangisi?',
    'Analyzing…': 'Analiz ediliyor…',
    'Insufficient data': 'Yetersiz veri',
    'Query failed': 'Sorgu başarısız',
    'Categorized insights from campaigns, channels, audiences, and revenue.':
      'Kampanyalar, kanallar, kitleler ve gelirden kategorize içgörüler.',
    'Evidence-based campaign and budget recommendations — never auto-executed.':
      'Kanıta dayalı kampanya ve bütçe önerileri — asla otomatik uygulanmaz.',
    'Missing evidence — cannot accept until evidence is attached.':
      'Eksik kanıt — kanıt eklenene kadar kabul edilemez.',
    'Framework slots for lead scoring, revenue, optimization, and next best action.':
      'Lead skorlama, gelir, optimizasyon ve sonraki en iyi aksiyon için çerçeve yuvaları.',
    'All values show Unknown until a real model pipeline is connected.':
      'Gerçek bir model hattı bağlanana kadar tüm değerler Bilinmiyor gösterir.',
    'Model not connected': 'Model bağlı değil',
    'Prediction framework slots are available but no model is connected.':
      'Tahmin çerçeve yuvaları mevcut ancak model bağlı değil.',
    'Anomaly Detection': 'Anomali Tespiti',
    'Traffic, lead, conversion, and tracking anomalies with evidence.':
      'Kanıtlı trafik, lead, dönüşüm ve izleme anomalileri.',
    'Daily, weekly, monthly, quarterly, and board summaries.':
      'Günlük, haftalık, aylık, çeyreklik ve yönetim kurulu özetleri.',
    'Copilot, predictions, and anomaly detection configuration.':
      'Asistan, tahminler ve anomali tespiti yapılandırması.',
    'Copilot enabled': 'Asistan etkin',
    'Predictions enabled': 'Tahminler etkin',
    'Anomaly detection': 'Anomali tespiti',
    'Model pipeline': 'Model hattı',
    'Default confidence': 'Varsayılan güven',
    'Settings are read-only for your role.': 'Rolünüz için ayarlar salt okunur.',
    'Overall Marketing Health': 'Genel Pazarlama Sağlığı',
    'Conversion Funnel': 'Dönüşüm Hunisi',
    'Channel Performance': 'Kanal Performansı',
    'Campaign Projects': 'Kampanya Projeleri',
    'Lead & Audience Metrics': 'Lead ve Kitle Metrikleri',
    'Tracking Health': 'İzleme Sağlığı',
    'Partially connected': 'Kısmen bağlı',
    'Authentication required': 'Kimlik doğrulama gerekli',
    'Permission restricted': 'Yetki kısıtlı',
    'Investor Acquisition': 'Yatırımcı Edinimi',
    'Buyer Acquisition': 'Alıcı Edinimi',
    'Broker Acquisition': 'Broker Edinimi',
    'Property Launch': 'Mülk Lansmanı',
    'Project Launch': 'Proje Lansmanı',
    'Event Promotion': 'Etkinlik Tanıtımı',
    'Brand Awareness': 'Marka Farkındalığı',
    'Lead Contexts': 'Lead Bağlamları',
    'Deliverability': 'Teslim edilebilirlik',
    'Readiness checklist': 'Hazırlık kontrol listesi',
    'Unsubscribe required:': 'Abonelikten çıkış gerekli:',
    'Unsubscribe link present:': 'Abonelikten çıkış bağlantısı mevcut:',
    'Subject:': 'Konu:',
    'Save draft': 'Taslağı kaydet',
    'Configure channels': 'Kanalları yapılandır',
    'Link content assets to this campaign.': 'Bu kampanyaya içerik varlıklarını bağlayın.',
    'Form integration is not yet connected.': 'Form entegrasyonu henüz bağlı değil.',
    'Approval history for this campaign.': 'Bu kampanya için onay geçmişi.',
    'View in Approvals workspace': 'Onaylar çalışma alanında görüntüle',
    'Channel assignments are configured per campaign.': 'Kanal atamaları kampanya başına yapılandırılır.',
  }).sort((a, b) => b[0].length - a[0].length),
);

const KEEP_AS_IS = new Set([
  'WhatsApp',
  'SMS',
  'UTM',
  'KPI',
  'KPIs',
  'CRM',
  'API',
  'ML',
  'AI',
  'Email',
  'Slug',
  'LinkedIn',
  'UTM',
]);

function looksTurkish(s) {
  return /[çğıöşüÇĞİÖŞÜ]/.test(s);
}

function translate(value) {
  if (typeof value !== 'string') return value;
  if (!value.trim()) return value;
  if (KEEP_AS_IS.has(value)) return value;
  if (looksTurkish(value)) return value;

  if (PHRASES.has(value)) return PHRASES.get(value);

  let out = value;
  for (const [enPhrase, trPhrase] of PHRASES) {
    if (out.includes(enPhrase)) {
      out = out.split(enPhrase).join(trPhrase);
    }
  }
  return out;
}

function polish(trNode, enNode) {
  let changed = 0;
  if (typeof enNode === 'string') {
    const next = translate(enNode);
    // Prefer translating from English source for consistency when TR still looks English
    if (typeof trNode === 'string') {
      if (!looksTurkish(trNode) && next !== trNode) {
        return { value: next, changed: 1 };
      }
      // If TR equals EN and we have a better translation
      if (trNode === enNode && next !== enNode) {
        return { value: next, changed: 1 };
      }
      return { value: trNode, changed: 0 };
    }
    return { value: next, changed: 1 };
  }
  if (Array.isArray(enNode)) {
    const arr = [];
    for (let i = 0; i < enNode.length; i++) {
      const r = polish(trNode?.[i], enNode[i]);
      arr.push(r.value);
      changed += r.changed;
    }
    return { value: arr, changed };
  }
  if (enNode && typeof enNode === 'object') {
    const out = { ...(trNode && typeof trNode === 'object' ? trNode : {}) };
    for (const [k, v] of Object.entries(enNode)) {
      const r = polish(out[k], v);
      out[k] = r.value;
      changed += r.changed;
    }
    return { value: out, changed };
  }
  return { value: trNode ?? enNode, changed: 0 };
}

const result = polish(tr.marketing, en.marketing);
tr.marketing = result.value;

// Extra status enums for leads
tr.marketing.leads.handoffStatus = {
  ready: 'Devir için hazır',
  blocked: 'Engelli',
  pending: 'Beklemede',
  completed: 'Tamamlandı',
  in_progress: 'Devam ediyor',
  handed_off: 'Devredildi',
  not_ready: 'Hazır değil',
};

en.marketing.leads.handoffStatus = {
  ready: 'Ready for handoff',
  blocked: 'Blocked',
  pending: 'Pending',
  completed: 'Completed',
  in_progress: 'In progress',
  handed_off: 'Handed off',
  not_ready: 'Not ready',
};

fs.writeFileSync(trPath, `${JSON.stringify(tr, null, 2)}\n`, 'utf8');
fs.writeFileSync(enPath, `${JSON.stringify(en, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({ changedLeaves: result.changed }, null, 2));
