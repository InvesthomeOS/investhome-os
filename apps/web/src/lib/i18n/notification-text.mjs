const EN = {
  'crm.task_due.title': 'Task reminder',
  'crm.task_due.message': '{title} is due now.',
  'crm.task_overdue.title': 'Overdue task',
  'crm.task_overdue.message': 'Task is overdue: {title}',
  'crm.meeting_soon.title': 'Meeting reminder',
  'crm.meeting_soon.message': 'Your meeting is in {minutes} minutes: {title}',
  'crm.new_lead.title': 'New lead',
  'crm.new_lead.message': 'New lead: {name}',
  'crm.agreement_created.title': 'Agreement created',
  'crm.agreement_created.message': 'A new agreement was created: {name}',
  'crm.agreement.title': 'Agreement',
  'crm.agreement.message': 'Agreement updated: {name}',
  'crm.sale.title': 'Sale',
  'crm.sale.message': 'Sale recorded: {name}',
  'crm.instagram_message.title': 'New Instagram message',
  'crm.instagram_message.message': '{name}',
  'crm.facebook_message.title': 'New Facebook message',
  'crm.facebook_message.message': '{name}',
  'crm.meta_message.title': 'New Meta message',
  'crm.meta_message.message': '{name}',
  'crm.meta_comment.title': 'New Meta comment',
  'crm.meta_comment.message': '{name}',
  'crm.social_published.title': 'Social post published',
  'crm.social_published.message': '{title} was published.',
};

const TR = {
  'crm.task_due.title': 'Görev hatırlatması',
  'crm.task_due.message': '{title} görevini yapma zamanı geldi.',
  'crm.task_overdue.title': 'Geciken görev',
  'crm.task_overdue.message': 'Görev süresi geçti: {title}',
  'crm.meeting_soon.title': 'Toplantı hatırlatması',
  'crm.meeting_soon.message': '{minutes} dakika sonra toplantınız var: {title}',
  'crm.new_lead.title': 'Yeni Lead',
  'crm.new_lead.message': 'Yeni Lead: {name}',
  'crm.agreement_created.title': 'Yeni anlaşma oluşturuldu',
  'crm.agreement_created.message': 'Yeni anlaşma oluşturuldu: {name}',
  'crm.agreement.title': 'Anlaşma',
  'crm.agreement.message': 'Anlaşma güncellendi: {name}',
  'crm.sale.title': 'Satış',
  'crm.sale.message': 'Satış kaydedildi: {name}',
  'crm.instagram_message.title': 'Instagram’dan yeni mesaj',
  'crm.instagram_message.message': '{name}',
  'crm.facebook_message.title': 'Facebook’tan yeni mesaj',
  'crm.facebook_message.message': '{name}',
  'crm.meta_message.title': 'Meta mesajı',
  'crm.meta_message.message': '{name}',
  'crm.meta_comment.title': 'Meta yorumu',
  'crm.meta_comment.message': '{name}',
  'crm.social_published.title': 'Sosyal medya yayını',
  'crm.social_published.message': '{title} yayınlandı.',
};

const KIND_EN = {
  task_due: 'Task reminder',
  task_overdue: 'Overdue task',
  tasks_overdue: 'Overdue task',
  meeting_soon: 'Meeting reminder',
  new_lead: 'New lead',
  agreement_created: 'Agreement',
  agreement: 'Agreement',
  sale: 'Sale',
  instagram_message: 'Instagram message',
  facebook_message: 'Facebook message',
  meta_message: 'Meta message',
  meta_comment: 'Meta comment',
  social_published: 'Social post published',
};

const KIND_TR = {
  task_due: 'Görev hatırlatması',
  task_overdue: 'Geciken görev',
  tasks_overdue: 'Geciken görev',
  meeting_soon: 'Toplantı hatırlatması',
  new_lead: 'Yeni Lead',
  agreement_created: 'Anlaşma',
  agreement: 'Anlaşma',
  sale: 'Satış',
  instagram_message: 'Instagram mesajı',
  facebook_message: 'Facebook mesajı',
  meta_message: 'Meta mesajı',
  meta_comment: 'Meta yorumu',
  social_published: 'Sosyal medya yayını',
};

export function notificationTextPath(key) {
  const raw = String(key || '').trim();
  return raw.startsWith('notifications.') ? raw.slice('notifications.'.length) : raw;
}

export function isRawMessageKey(value) {
  const text = String(value ?? '').trim();
  if (!text) return true;
  if (text.startsWith('notifications.')) return true;
  return /^[a-z0-9_]+(?:\.[a-z0-9_]+)+$/.test(text);
}

function interpolate(template, metadata) {
  return String(template).replace(/\{(\w+)\}/g, (_, token) => {
    const value = metadata?.[token];
    return value == null ? '' : String(value);
  });
}

function lookup(locale, path) {
  const table = locale === 'tr' ? TR : EN;
  const aliased = path.replaceAll('tasks_overdue', 'task_overdue');
  return table[path] || table[aliased] || '';
}

function humanFallback(path, metadata, locale) {
  const parts = path.split('.').filter((part) => !['title', 'message', 'notifications', 'crm'].includes(part));
  const leaf = parts[parts.length - 1] || 'notification';
  const kinds = locale === 'tr' ? KIND_TR : KIND_EN;
  const label = kinds[leaf] || leaf.replaceAll('_', ' ');
  const subject = metadata?.title || metadata?.name || metadata?.project || metadata?.related_label || '';
  return subject ? `${label}: ${subject}` : label;
}

export function notificationFallback(key, metadata = {}, locale = 'en') {
  const path = notificationTextPath(key);
  const template = lookup(locale === 'tr' ? 'tr' : 'en', path);
  const text = (template ? interpolate(template, metadata) : humanFallback(path, metadata, locale))
    .replace(/\s+/g, ' ')
    .replace(/:\s*$/, '')
    .trim();
  if (!text || isRawMessageKey(text)) return locale === 'tr' ? 'Bildirim' : 'Notification';
  return text;
}
