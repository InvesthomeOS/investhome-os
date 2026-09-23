import type { IhIconName } from '@/components/icons/ih-icons';

export type FileCategoryKey =
  | 'contracts'
  | 'identity'
  | 'financial'
  | 'marketing'
  | 'legal'
  | 'other';

export type FileTypeKey = 'pdf' | 'docx' | 'xlsx' | 'png' | 'jpg' | 'zip' | 'other';

export type FileRelatedKind = 'customer' | 'investor' | 'project';

export type FileViewMode = 'grid' | 'list';

export type FileRecord = {
  id: string;
  name: string;
  fileType: FileTypeKey;
  category: FileCategoryKey;
  size: string;
  version: string;
  updatedAt: string;
  relatedKind: FileRelatedKind;
  relatedName: string;
  owner: string;
  recent: boolean;
};

export type FileCategoryChip = {
  id: FileCategoryKey | 'all';
  count: number;
};

export type FilesWorkspacePreview = {
  files: FileRecord[];
  categories: FileCategoryChip[];
  recentIds: string[];
};

export const FILE_TYPE_ICON: Record<FileTypeKey, IhIconName> = {
  pdf: 'documents',
  docx: 'documents',
  xlsx: 'barChart',
  png: 'sparkles',
  jpg: 'sparkles',
  zip: 'inbox',
  other: 'documents',
};
