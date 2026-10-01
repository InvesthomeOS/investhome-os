import DOMPurify from 'isomorphic-dompurify';

const EMAIL_RE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
const HTML_TAG_RE = /<\/?[a-z](?:[^>'"]|'[^']*'|"[^"]*")*>/i;
const ESCAPED_HTML_RE = /&lt;\/?[a-z](?:[^&]|&(?!gt;))*&gt;/i;
const UNCLOSED_TAG_RE = /<\/?[a-z][^>]*$/i;
const NAMED_ENTITIES: Record<string, string> = {
  nbsp: ' ',
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  hellip: '…',
  ndash: '–',
  mdash: '—',
  copy: '©',
  reg: '®',
  trade: '™',
  rsquo: '’',
  lsquo: '‘',
  rdquo: '”',
  ldquo: '“',
};

const DECORATIVE_ICON_URL =
  /https?:\/\/(?:static\.wazzup24\.com\/images\/bitrix\/whatsapp\.png|[^\s"'<>]+\/bitrix\/whatsapp\.png)\S*/gi;

export type EmailParty = {
  name?: string;
  address?: string;
  label: string;
};

export type ParsedEmail = {
  subject: string;
  sender: EmailParty | null;
  recipients: EmailParty[];
  cc: EmailParty[];
  preview: string;
  html: string;
  text: string;
  links: Array<{ href: string; label: string }>;
};

export type WhatsAppMedia = {
  kind: 'image' | 'pdf' | 'file' | 'link';
  url: string;
  caption?: string;
};

export type EmailSourceKind = 'html' | 'escaped-html' | 'plain';

function fromCodePoint(code: number): string {
  if (!Number.isFinite(code) || code <= 0) return '';
  try {
    return String.fromCodePoint(code);
  } catch {
    return '';
  }
}

function decodeEntitiesOnce(value: string): string {
  return value
    .replace(/&nbsp;/gi, ' ')
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) => fromCodePoint(parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, num) => fromCodePoint(Number(num)))
    .replace(/&([a-z]+);/gi, (match, name) => NAMED_ENTITIES[String(name).toLowerCase()] ?? match);
}

export function unescapeEmailSource(value: string | null | undefined): string {
  let current = String(value || '');
  for (let i = 0; i < 5; i += 1) {
    const next = decodeEntitiesOnce(current);
    if (next === current) break;
    current = next;
  }
  return current;
}

export function looksLikeHtml(value: string | null | undefined): boolean {
  const text = String(value || '');
  return HTML_TAG_RE.test(text) || /<(?:div|br|p|span|table|a|ul|ol|li|img|blockquote)\b/i.test(text);
}

export function looksLikeEscapedHtml(value: string | null | undefined): boolean {
  return ESCAPED_HTML_RE.test(String(value || ''));
}

export function detectEmailSourceKind(value: string | null | undefined): EmailSourceKind {
  const text = String(value || '');
  const html = looksLikeHtml(text);
  const escaped = looksLikeEscapedHtml(text);
  if (escaped && !html) return 'escaped-html';
  if (html) return 'html';
  const unescaped = unescapeEmailSource(text);
  if (looksLikeHtml(unescaped)) return 'escaped-html';
  return 'plain';
}

export function resolveEmailSource(value: string | null | undefined): { kind: EmailSourceKind; source: string } {
  const raw = String(value || '');
  const kind = detectEmailSourceKind(raw);
  if (kind === 'escaped-html') return { kind, source: unescapeEmailSource(raw) };
  if (kind === 'html') return { kind, source: raw };
  return { kind: 'plain', source: unescapeEmailSource(raw) };
}

export function escapeHtml(value: string | null | undefined): string {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function collapsePreviewText(value: string): string {
  return value
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

export function stripHtml(value: string | null | undefined): string {
  const { source } = resolveEmailSource(value);
  const stripped = source
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<head[\s\S]*?<\/head>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|tr|h[1-6]|li|blockquote|table)>/gi, '\n')
    .replace(/<[^>]*>/g, ' ')
    .replace(UNCLOSED_TAG_RE, ' ')
    .replace(/\[[^\]]+\]/g, ' ')
    .replace(DECORATIVE_ICON_URL, ' ')
    .replace(/\bhref\s*=\s*["'][^"']*["']/gi, ' ');
  return collapsePreviewText(unescapeEmailSource(stripped));
}

export function looksLikePayloadDump(value: string | null | undefined): boolean {
  const raw = String(value || '').trim();
  const text = stripHtml(raw);
  if (!text) return true;
  if ((text.startsWith('{') || text.startsWith('[')) && /"(ID|AUTHOR_ID|COMMENT|UF_|fields|result|bitrix)"/i.test(text)) {
    return true;
  }
  if (/bitrix24\.com/i.test(text) && /webhook/i.test(text)) return true;
  if (/^\s*<\?xml/i.test(raw)) return true;
  return false;
}

export function noteFingerprint(params: {
  id: string;
  entityId?: string | null;
  createdAt?: string | null;
  text: string;
  sha256?: string | null;
}): string {
  if (params.sha256) return `sha:${params.entityId || ''}:${params.sha256}`;
  const norm = params.text.replace(/\s+/g, ' ').trim().toLowerCase();
  const day = String(params.createdAt || '').slice(0, 10);
  return `txt:${params.entityId || ''}:${day}:${norm.slice(0, 240)}`;
}

export function emailPreviewText(value: string | null | undefined, maxChars = 280): string {
  const text = stripHtml(value)
    .replace(/^(Gönderen|From|Kimden|Kime|To|Cc|Konu|Subject|Gönderildi|Sent|Alıcı):.+$/gim, '')
    .replace(/\s+/g, ' ')
    .trim();
  if (text.length <= maxChars) return text;
  return `${text.slice(0, maxChars).trim()}…`;
}

export function isDecorativeMediaUrl(url: string | null | undefined): boolean {
  return /static\.wazzup24\.com\/images\/bitrix\/whatsapp\.png|\/bitrix\/whatsapp\.png/i.test(String(url || ''));
}

export function looksLikeRawMarkup(value: string | null | undefined): boolean {
  const text = String(value || '');
  return looksLikeHtml(text) || looksLikeEscapedHtml(text) || /href\s*=|&nbsp;/i.test(text);
}

const PURIFY_ALLOWED_TAGS = [
  'p',
  'br',
  'div',
  'span',
  'a',
  'strong',
  'em',
  'b',
  'i',
  'u',
  'ul',
  'ol',
  'li',
  'table',
  'thead',
  'tbody',
  'tfoot',
  'tr',
  'td',
  'th',
  'img',
  'blockquote',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'hr',
  'pre',
];

const PURIFY_ALLOWED_ATTR = ['href', 'src', 'alt', 'title', 'colspan', 'rowspan', 'width', 'height', 'target', 'rel'];

const PURIFY_FORBID_TAGS = [
  'script',
  'iframe',
  'object',
  'embed',
  'form',
  'input',
  'button',
  'textarea',
  'select',
  'option',
  'link',
  'meta',
  'base',
  'style',
  'svg',
  'math',
  'video',
  'audio',
  'applet',
  'frame',
  'frameset',
  'template',
  'noscript',
  'canvas',
];

const TRACKING_IMG_RE =
  /(?:pixel|tracker|beacon|open\.gif|spacer\.gif|doubleclick|analytics|facebook\.com\/tr|google-analytics)/i;

const PURIFY_CONFIG = {
  ALLOWED_TAGS: PURIFY_ALLOWED_TAGS,
  ALLOWED_ATTR: PURIFY_ALLOWED_ATTR,
  ALLOW_DATA_ATTR: false,
  ALLOW_UNKNOWN_PROTOCOLS: false,
  FORBID_TAGS: PURIFY_FORBID_TAGS,
  FORBID_ATTR: ['style', 'srcset', 'srcdoc', 'xlink:href', 'formaction', 'action'],
  KEEP_CONTENT: true,
  IN_PLACE: false,
  SAFE_FOR_XML: true,
};

type AttrNode = {
  tagName?: string;
  nodeName?: string;
  textContent: string | null;
  getAttribute(name: string): string | null;
  setAttribute(name: string, value: string): void;
  removeAttribute(name: string): void;
  getAttributeNames?(): string[];
  remove?(): void;
  parentNode?: { removeChild(child: AttrNode): void } | null;
};

let purifyHooksInstalled = false;

function tagNameOf(node: AttrNode): string {
  return String(node.tagName || node.nodeName || '').toLowerCase();
}

function stripEventHandlers(el: AttrNode) {
  const names = typeof el.getAttributeNames === 'function' ? el.getAttributeNames() : [];
  for (const name of names) {
    if (name.toLowerCase().startsWith('on')) {
      el.removeAttribute(name);
    }
  }
}

function safeEmailHref(value: string | null | undefined): string | null {
  const href = String(value || '').trim();
  if (!href) return null;
  if (/[\u0000-\u001f\u007f]/.test(href)) return null;
  if (/^(javascript|vbscript|data):/i.test(href.replace(/[\s\u0000]+/g, ''))) return null;
  if (href.startsWith('//')) return null;

  if (/^https?:\/\//i.test(href)) {
    try {
      const url = new URL(href);
      if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
      return url.href;
    } catch {
      return null;
    }
  }

  if (/^mailto:/i.test(href)) {
    const rest = href.slice(7);
    const address = rest.split('?')[0].trim();
    if (!address || /[\s<>]/.test(address)) return null;
    if (/^(javascript|vbscript|data):/i.test(address)) return null;
    return href;
  }

  return null;
}

function safeEmailImgSrc(value: string | null | undefined): string | null {
  const src = String(value || '').trim();
  if (!src) return null;
  if (/[\u0000-\u001f\u007f]/.test(src)) return null;
  if (/^(javascript|vbscript|data):/i.test(src.replace(/[\s\u0000]+/g, ''))) return null;
  if (src.startsWith('//')) return null;
  if (/^cid:/i.test(src)) return src;
  if (/^https?:\/\//i.test(src)) {
    try {
      const url = new URL(src);
      if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
      if (TRACKING_IMG_RE.test(url.href)) return null;
      return url.href;
    } catch {
      return null;
    }
  }
  return null;
}

function isTrackingImage(el: AttrNode): boolean {
  const width = Number(el.getAttribute('width') || 0);
  const height = Number(el.getAttribute('height') || 0);
  const src = el.getAttribute('src') || '';
  if ((width > 0 && width <= 2) || (height > 0 && height <= 2)) return true;
  return TRACKING_IMG_RE.test(src);
}

function removeNode(el: AttrNode) {
  if (typeof el.remove === 'function') {
    el.remove();
    return;
  }
  el.parentNode?.removeChild(el);
}

function fillEmptyMailto(el: AttrNode) {
  const href = el.getAttribute('href') || '';
  if (!/^mailto:/i.test(href)) return;
  if ((el.textContent || '').trim()) return;
  const address = href.replace(/^mailto:/i, '').split('?')[0].trim();
  if (address) el.textContent = address;
}

function ensurePurifyHooks() {
  if (purifyHooksInstalled) return;
  purifyHooksInstalled = true;
  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    const el = node as unknown as AttrNode;
    if (typeof el.getAttribute !== 'function') return;
    stripEventHandlers(el);
    const tag = tagNameOf(el);

    if (tag === 'a') {
      const href = safeEmailHref(el.getAttribute('href'));
      if (href) {
        el.setAttribute('href', href);
        if (/^https?:/i.test(href)) {
          el.setAttribute('target', '_blank');
          el.setAttribute('rel', 'noopener noreferrer nofollow');
        } else {
          el.removeAttribute('target');
          el.removeAttribute('rel');
        }
        fillEmptyMailto(el);
      } else {
        el.removeAttribute('href');
        el.removeAttribute('target');
        el.removeAttribute('rel');
      }
      return;
    }

    if (tag === 'img') {
      const src = safeEmailImgSrc(el.getAttribute('src'));
      if (!src || isTrackingImage(el)) {
        removeNode(el);
        return;
      }
      el.setAttribute('src', src);
      el.setAttribute('alt', el.getAttribute('alt') || '');
    }
  });
}

function sanitizeEmailHtmlFragment(dirty: string): string {
  if (!String(dirty || '').trim()) return '';
  ensurePurifyHooks();
  return String(DOMPurify.sanitize(dirty, PURIFY_CONFIG));
}

function extractEmailAnchors(html: string): Array<{ href: string; label: string }> {
  const source = String(html || '');
  if (!source.trim()) return [];
  const links: Array<{ href: string; label: string }> = [];
  const tagRe = /<a\b([^>]*)>([\s\S]*?)<\/a>/gi;
  let match: RegExpExecArray | null;
  while ((match = tagRe.exec(source))) {
    const hrefMatch = String(match[1] || '').match(/\bhref\s*=\s*(?:"([^"]*)"|'([^']*)')/i);
    const href = safeEmailHref(hrefMatch?.[1] ?? hrefMatch?.[2] ?? '');
    if (!href) continue;
    const label = String(match[2] || '')
      .replace(/<[^>]*>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim() || href.replace(/^mailto:/i, '');
    if (!links.some((item) => item.href === href)) links.push({ href, label });
  }
  return links;
}

function safeUrl(value: string | null | undefined): string | null {
  const href = String(value || '').trim();
  if (!href) return null;
  if (/^(javascript|vbscript|data):/i.test(href)) return null;
  if (/^(https?:|mailto:|cid:|tel:)/i.test(href)) return href;
  if (href.startsWith('/') && !href.startsWith('//')) return href;
  return null;
}

function plainTextToHtml(text: string): string {
  const escaped = escapeHtml(text);
  if (!escaped) return '';
  return escaped
    .split(/\n{2,}/)
    .map((block) => `<p>${block.replace(/\n/g, '<br>')}</p>`)
    .join('');
}

export function sanitizeHtml(html: string | null | undefined): string {
  const { kind, source } = resolveEmailSource(html);
  if (!source.trim()) return '';
  const wrapped = kind === 'plain' ? plainTextToHtml(source) : source;
  return sanitizeEmailHtmlFragment(wrapped);
}

function parseParty(raw: string | null | undefined): EmailParty | null {
  const text = unescapeEmailSource(String(raw || ''))
    .replace(/\s+/g, ' ')
    .trim();
  if (!text) return null;
  const angle = text.match(/^(.*)<([^>]+)>$/);
  if (angle) {
    const name = angle[1].replace(/["']/g, '').trim();
    const address = angle[2].trim();
    return { name: name || undefined, address, label: name ? `${name} <${address}>` : address };
  }
  const email = text.match(EMAIL_RE)?.[0];
  if (email) {
    const name = text.replace(email, '').replace(/[<>]/g, '').trim();
    return { name: name || undefined, address: email, label: name ? `${name} <${email}>` : email };
  }
  return { label: text };
}

function splitParties(raw: string | null | undefined): EmailParty[] {
  return String(raw || '')
    .split(/;|,(?=[^<]*>|[^,]*@)/)
    .map((item) => parseParty(item))
    .filter((item): item is EmailParty => Boolean(item));
}

function headerValue(text: string, labels: string[]): string | null {
  for (const label of labels) {
    const match = text.match(new RegExp(`(?:^|\\n)\\s*${label}\\s*[:：]\\s*(.+)`, 'i'));
    if (match?.[1]) return match[1].split('\n')[0].trim();
  }
  return null;
}

export function parseEmailContent(title: string, html: string | null | undefined): ParsedEmail {
  const source = String(html || '');
  const text = stripHtml(source);
  const subject =
    headerValue(text, ['Konu', 'Subject']) ||
    title.replace(/^E-posta:\s*/i, '').trim() ||
    'E-posta';
  const sender = parseParty(headerValue(text, ['Gönderen', 'From', 'Kimden']));
  const recipients = splitParties(headerValue(text, ['Kime', 'To', 'Alıcı']));
  const cc = splitParties(headerValue(text, ['Cc', 'CC', 'Bilgi']));
  const preview = emailPreviewText(source);
  const safe = sanitizeHtml(bbcodeToHtml(source));
  const links = extractEmailAnchors(safe);
  return {
    subject,
    sender,
    recipients,
    cc,
    preview: preview || text.slice(0, 220),
    html: safe,
    text,
    links,
  };
}

export function bbcodeToHtml(value: string | null | undefined): string {
  let text = String(value || '');
  text = text.replace(/\[img\](.*?)\[\/img\]/gi, (_, url) => {
    const href = safeUrl(String(url).trim());
    return href ? `<img src="${href}" alt="">` : '';
  });
  text = text.replace(/\[url=(.*?)\](.*?)\[\/url\]/gi, (_, url, label) => {
    const href = safeUrl(String(url).trim());
    const caption = stripHtml(String(label));
    return href ? `<a href="${href}">${caption || href}</a>` : caption;
  });
  text = text.replace(/\[url\](.*?)\[\/url\]/gi, (_, url) => {
    const href = safeUrl(String(url).trim());
    return href ? `<a href="${href}">${href}</a>` : '';
  });
  text = text.replace(/\[b\]([\s\S]*?)\[\/b\]/gi, '<strong>$1</strong>');
  text = text.replace(/\[i\]([\s\S]*?)\[\/i\]/gi, '<em>$1</em>');
  text = text.replace(/\[u\]([\s\S]*?)\[\/u\]/gi, '<u>$1</u>');
  text = text.replace(/\[br\s*\/?\]/gi, '<br>');
  return text;
}

export function parseWhatsappMedia(value: string | null | undefined): { text: string; media: WhatsAppMedia[] } {
  const source = String(value || '');
  const media: WhatsAppMedia[] = [];
  const consume = (kind: WhatsAppMedia['kind'], url: string, caption?: string) => {
    if (!url || isDecorativeMediaUrl(url) || media.some((item) => item.url === url)) return;
    media.push({ kind, url, caption });
  };
  source.replace(/\[img\](.*?)\[\/img\]/gi, (_, url) => {
    const href = safeUrl(String(url).trim());
    if (href && !isDecorativeMediaUrl(href)) consume('image', href);
    return '';
  });
  source.replace(/\[url=(.*?)\](.*?)\[\/url\]/gi, (_, url, label) => {
    const href = safeUrl(String(url).trim());
    const caption = stripHtml(String(label));
    if (!href) return '';
    const lower = href.toLowerCase();
    if (/\.(png|jpe?g|gif|webp)(\?|$)/i.test(lower) || /image/i.test(caption)) consume('image', href, caption);
    else if (/\.pdf(\?|$)/i.test(lower) || /\.pdf/i.test(caption)) consume('pdf', href, caption);
    else consume(/store\.|disk|file/i.test(lower) ? 'file' : 'link', href, caption);
    return '';
  });
  const filename = source.match(/[^\s<>]+\.(pdf|png|jpe?g|gif|webp|docx?|xlsx?)/i);
  if (filename && !media.length) {
    consume(/\.(png|jpe?g|gif|webp)$/i.test(filename[0]) ? 'image' : /\.pdf$/i.test(filename[0]) ? 'pdf' : 'file', filename[0], filename[0]);
  }
  const html = sanitizeHtml(bbcodeToHtml(source));
  const text = stripHtml(html || source);
  return { text, media };
}

export function taskStatusLabel(status: string | null | undefined): string {
  const value = String(status || '').toLowerCase();
  if (value === 'completed') return 'Tamamlandı';
  if (value === 'in_progress') return 'Devam ediyor';
  if (value === 'waiting') return 'Beklemede';
  if (value === 'cancelled') return 'İptal';
  if (value === 'deferred') return 'Ertelendi';
  if (value === 'not_started' || value === 'planned') return 'Başlamadı';
  return status || '—';
}
