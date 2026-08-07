/**
 * Media Library ↔ Creative Studio Media API helpers.
 * Demo ids like `a1` must never be treated as Media Library UUIDs.
 */

import type { CreativeStudioMediaAsset, CreativeStudioMediaFolder } from '@/lib/api/creative-studio';

import type {
  AssetKind,
  FileExt,
  MediaAsset,
  MediaFolder,
} from './media-library-model';

const DEMO_ASSET_ID_RE = /^a\d+$/i;
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/** Accept attribute aligned with Document Center / media upload ALLOWED_EXTENSIONS. */
export const ML_UPLOAD_ACCEPT =
  'image/jpeg,image/png,image/webp,image/gif,video/mp4,video/webm,video/quicktime,application/pdf,' +
  'application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,' +
  'application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,' +
  'application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,' +
  'text/csv,text/plain,application/acad,image/vnd.dwg,application/dxf,application/zip,.jpg,.jpeg,.png,.webp,.gif,' +
  '.mp4,.webm,.mov,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.txt,.dwg,.dxf,.zip';

const ALLOWED_EXT = new Set([
  'pdf',
  'docx',
  'doc',
  'xlsx',
  'xls',
  'pptx',
  'ppt',
  'csv',
  'txt',
  'jpg',
  'jpeg',
  'png',
  'webp',
  'gif',
  'mp4',
  'webm',
  'mov',
  'dwg',
  'dxf',
  'zip',
]);

export function isDemoAssetId(id: string | null | undefined): boolean {
  if (!id) return false;
  return DEMO_ASSET_ID_RE.test(id.trim());
}

export function isMediaAssetUuid(id: string | null | undefined): boolean {
  if (!id) return false;
  const trimmed = id.trim();
  if (isDemoAssetId(trimmed)) return false;
  return UUID_RE.test(trimmed);
}

/** Demo sidebar folder ids (temple, social, …) must never be sent as Media API folder_id. */
export function isApiFolderId(id: string | null | undefined): boolean {
  return isMediaAssetUuid(id);
}

export function isAllowedMediaUpload(file: File): boolean {
  if (!file || !file.size) return false;
  const name = file.name || '';
  const ext = name.includes('.') ? name.split('.').pop()!.toLowerCase() : '';
  if (ext && ALLOWED_EXT.has(ext)) return true;
  const type = (file.type || '').split(';')[0].trim().toLowerCase();
  if (!type) return false;
  if (type.startsWith('image/')) return ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(type);
  if (type.startsWith('video/')) return ['video/mp4', 'video/webm', 'video/quicktime'].includes(type);
  return [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/csv',
    'text/plain',
    'application/zip',
    'application/x-zip-compressed',
  ].includes(type);
}

export function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size < 0) return '0 B';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export function relativeDateLabel(iso: string): string {
  const then = Date.parse(iso);
  if (!Number.isFinite(then)) return '';
  const diffMs = Date.now() - then;
  if (diffMs < 60_000) return 'Just now';
  if (diffMs < 3_600_000) return `${Math.floor(diffMs / 60_000)}m ago`;
  if (diffMs < 86_400_000) return `${Math.floor(diffMs / 3_600_000)}h ago`;
  if (diffMs < 604_800_000) return `${Math.floor(diffMs / 86_400_000)}d ago`;
  return new Date(then).toLocaleDateString();
}

export function absoluteDateLabel(iso: string): string {
  const then = Date.parse(iso);
  if (!Number.isFinite(then)) return '';
  return new Date(then).toLocaleString();
}

export function kindFromContentType(contentType: string, filename?: string): AssetKind {
  const ct = (contentType || '').toLowerCase();
  if (ct.startsWith('image/')) return 'image';
  if (ct.startsWith('video/')) return 'video';
  if (ct.startsWith('audio/')) return 'audio';
  if (ct === 'application/pdf') return 'document';
  if (ct.includes('presentation') || ct.includes('powerpoint')) return 'document';
  if (ct.includes('word') || ct.includes('msword') || ct.includes('document')) return 'document';
  if (ct.includes('sheet') || ct.includes('excel') || ct === 'text/csv') return 'document';
  const ext = (filename || '').split('.').pop()?.toLowerCase() ?? '';
  if (['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(ext)) return 'image';
  if (['mp4', 'webm', 'mov'].includes(ext)) return 'video';
  if (['mp3', 'wav'].includes(ext)) return 'audio';
  if (['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'csv', 'txt'].includes(ext)) return 'document';
  return 'other';
}

export function extFromFilename(filename: string, kind: AssetKind): FileExt {
  const raw = filename.includes('.') ? filename.split('.').pop()!.toUpperCase() : '';
  const known: FileExt[] = [
    'JPG',
    'PNG',
    'SVG',
    'MP4',
    'PDF',
    'PPTX',
    'DOCX',
    'MP3',
    'WAV',
  ];
  if (raw === 'JPEG') return 'JPG';
  if ((known as string[]).includes(raw)) return raw as FileExt;
  if (kind === 'image') return 'JPG';
  if (kind === 'video') return 'MP4';
  if (kind === 'audio') return 'MP3';
  if (kind === 'document') return 'PDF';
  return 'PDF';
}

export function mapApiAssetToMediaAsset(
  asset: CreativeStudioMediaAsset,
  options?: {
    folderName?: string;
    displayThumbUrl?: string | null;
  },
): MediaAsset {
  const kind = kindFromContentType(asset.content_type || '', asset.filename);
  const ext = extFromFilename(asset.filename, kind);
  const resolution =
    asset.width && asset.height ? `${asset.width}×${asset.height}` : undefined;
  const created = asset.created_at || asset.updated_at || '';
  const tags = Array.isArray(asset.tags) ? asset.tags.filter(Boolean) : [];
  const isImage = kind === 'image';
  const thumb =
    options?.displayThumbUrl ||
    (isImage ? undefined : undefined);

  return {
    id: asset.id,
    name: asset.filename,
    kind,
    ext,
    sizeLabel: formatBytes(asset.file_size),
    sizeBytes: asset.file_size ?? 0,
    dateLabel: relativeDateLabel(created),
    addedAt: absoluteDateLabel(created) || created,
    addedBy: asset.uploaded_by_user_id ? String(asset.uploaded_by_user_id).slice(0, 8) : '—',
    folderId: asset.folder_id ?? '',
    folderName: options?.folderName || (asset.folder_id ? '—' : 'All Assets'),
    favorite: false,
    trashed: Boolean(asset.archived_at),
    thumbUrl: thumb || undefined,
    resolution,
    description: '',
    tags,
    usages: [],
    history: created
      ? [{ id: `${asset.id}-uploaded`, action: 'Uploaded', actor: '—', at: absoluteDateLabel(created) }]
      : [],
  };
}

export function mapApiFolderToMediaFolder(
  folder: CreativeStudioMediaFolder,
  count: number,
): MediaFolder {
  return {
    id: folder.id,
    name: folder.name,
    count,
  };
}

export function markSampleAssets(assets: MediaAsset[]): MediaAsset[] {
  return assets.map((asset) => ({
    ...asset,
    tags: asset.tags.includes('sample') ? asset.tags : [...asset.tags, 'sample'],
  }));
}
