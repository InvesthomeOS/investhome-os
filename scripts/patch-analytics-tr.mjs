import fs from 'node:fs';

const trPath = 'apps/web/messages/tr.json';
const tr = JSON.parse(fs.readFileSync(trPath, 'utf8'));
const a = tr.marketing.analytics;

Object.assign(a, {
  unknown: 'Bilinmiyor',
  empty: 'Veri yok',
  accessDenied: 'Pazarlama analitiğini görüntüleme yetkiniz yok.',
  accessDeniedHint: 'Pano erişimi için yöneticinize başvurun.',
  loadFailed: 'Analitik verileri yüklenemedi.',
  dataFreshness: 'Veri güncelliği',
});

a.hub = {
  ...a.hub,
  title: 'Pazarlama Komuta Merkezi',
  subtitle: 'Kampanyalar, leadler, kanallar ve dönüşümlerden operasyonel analitik.',
  openExecutive: 'Yönetici Panosunu Aç',
  workspaceOverview: 'Çalışma Alanı Özeti',
};

a.executive = {
  title: 'Yönetici Panosu',
  subtitle: "Gerçek operasyonel verilerden KPI'lar, huni, sağlık, uyarılar ve öneriler.",
};

a.performance = {
  title: 'Performans',
  subtitle: 'Kampanya ve kanal performans özetleri.',
};

a.funnel = {
  title: 'Dönüşüm Hunisi',
  subtitle: 'İzleme kullanılamadığında dürüst bilinmiyor durumlarıyla aşama aşama huni.',
};

a.channels = {
  title: 'Kanal Analitiği',
  subtitle: 'Kanal bağlantı durumu ve lead atıfı.',
};

a.projects = {
  title: 'Proje Analitiği',
  subtitle: 'Kampanya ve proje performans toplamları.',
};

a.audiences = {
  title: 'Kitle Analitiği',
  subtitle: 'Lead kalitesi ve kitle dönüşüm metrikleri.',
};

a.tracking = {
  title: 'İzleme Sağlığı',
  subtitle: 'UTM ve izleme yapılandırma durumu.',
};

a.health = {
  title: 'Pazarlama Sağlığı',
  subtitle: 'Operasyonel kanıtlardan türetilen kategori sağlık skorları.',
};

a.widgets = {
  title: "Widget'lar",
  subtitle: 'Yapılandırılabilir widget kaydı ve düzen.',
};

a.settings = {
  ...a.settings,
  title: 'Pano Ayarları',
  subtitle: 'Düzen, filtreler ve kayıtlı görünümler.',
  layoutMode: 'Düzen düzenleme modu',
  enterEditMode: 'Düzenleme moduna geç',
  exitEditMode: 'Düzenleme modundan çık',
  filters: 'Genel filtreler',
  resetFilters: 'Filtreleri sıfırla',
  savedViews: 'Kayıtlı görünümler',
  noSavedViews: 'Henüz kayıtlı görünüm yok.',
};

a.tabs = {
  ariaLabel: 'Pazarlama panosu bölümleri',
  hub: 'Merkez',
  executive: 'Yönetici',
  performance: 'Performans',
  funnel: 'Huni',
  channels: 'Kanallar',
  projects: 'Projeler',
  audiences: 'Kitleler',
  tracking: 'İzleme',
  health: 'Sağlık',
  widgets: "Widget'lar",
  settings: 'Ayarlar',
};

a.sections = {
  kpiBar: 'KPI Çubuğu',
  funnel: 'Dönüşüm Hunisi',
  health: 'Pazarlama Sağlığı',
  campaigns: 'Aktif Kampanyalar',
  channels: 'Kanal Özeti',
  alerts: 'Yönetici Uyarıları',
  recommendations: 'Öneriler',
};

fs.writeFileSync(trPath, `${JSON.stringify(tr, null, 2)}\n`);
console.log('executive.title=', tr.marketing.analytics.executive.title);
