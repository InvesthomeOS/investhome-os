import type {
  CreativeStudioMediaAsset,
  CreativeStudioMediaAssetListResponse,
  CreativeStudioMediaListParams,
} from '@/lib/api/creative-studio';

import { collectLinkedProjectMedia as collectLinkedProjectMediaUntyped } from './project-gallery-media.mjs';

export {
  PROJECT_MEDIA_FOLDER_CATEGORIES,
  heroRank,
  isOperationalProjectMedia,
  projectMediaCategory,
} from './project-gallery-media.mjs';

export function collectLinkedProjectMedia(
  fetchPage: (params: CreativeStudioMediaListParams) => Promise<CreativeStudioMediaAssetListResponse>,
  projectId: string,
): Promise<CreativeStudioMediaAsset[]> {
  return collectLinkedProjectMediaUntyped(fetchPage, projectId);
}
