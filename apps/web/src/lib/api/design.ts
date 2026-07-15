import { apiFetch } from '@/lib/api/client';
import { formatDate } from '@/lib/api/leads';

export const DESIGN_TYPES = [
  'colored_floor_plan',
  'marketing_floor_plan',
  'furniture_layout',
  'material_plan',
  'interior_concept',
  'exterior_concept',
  'other',
] as const;

export type DesignType = (typeof DESIGN_TYPES)[number];

export const DESIGN_STATUSES = [
  'draft',
  'ready_for_review',
  'revision_requested',
  'approved',
  'rejected',
  'failed',
  'archived',
] as const;

export type DesignStatus = (typeof DESIGN_STATUSES)[number];

export const FURNITURE_TYPES = [
  'sofa',
  'armchair',
  'coffee_table',
  'dining_table',
  'dining_chair',
  'bed',
  'bedside_table',
  'wardrobe',
  'desk',
  'media_unit',
  'rug',
  'kitchen_island',
  'stool',
  'vanity',
  'bathtub',
  'shower',
  'toilet',
  'other',
] as const;

export type FurnitureType = (typeof FURNITURE_TYPES)[number];

export interface DesignParameters {
  mode: 'basic_overlay' | 'room_regions';
  palette: string;
  regions: Array<{ id: string; label?: string | null; color: string }>;
  backgroundColor?: string | null;
  selected_style_preset_id?: string | null;
  selected_material_package_id?: string | null;
  color_overlays?: Array<Record<string, unknown>>;
  furniture_items?: string[];
  furniture_placements?: Array<{
    instance_id: string;
    catalog_id: string;
    x: number;
    y: number;
    rotation: number;
    width: number;
    depth: number;
    height?: number;
  }>;
  furniture_positions?: Record<string, { x: number; y: number }>;
  furniture_rotations?: Record<string, number>;
  furniture_dimensions?: Record<string, { width: number; depth: number; height: number }>;
  editor_metadata?: Record<string, unknown>;
}

export interface DesignProject {
  id: string;
  project_id: string;
  document_id: string;
  document_version_id: string;
  drawing_analysis_id: string | null;
  title: string;
  description: string | null;
  design_type: DesignType;
  status: DesignStatus;
  source_geometry_version: string | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  review_comment: string | null;
  review_submitted_at: string | null;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  project_name: string | null;
  document_title: string | null;
  created_by_name: string | null;
  reviewed_by_name: string | null;
  current_version_number: number | null;
  version_count: number;
}

export interface DesignVersion {
  id: string;
  design_project_id: string;
  version_number: number;
  source_geometry_version: string | null;
  design_parameters: DesignParameters | null;
  output_location: string | null;
  thumbnail_location: string | null;
  created_by_user_id: string | null;
  created_by_name: string | null;
  created_at: string;
}

export interface StylePreset {
  id: string;
  name: string;
  code: string;
  description: string | null;
  color_palette: Record<string, string> | null;
  material_preferences: Record<string, unknown> | null;
  furniture_preferences: Record<string, unknown> | null;
  is_system_preset: boolean;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface MaterialPackage {
  id: string;
  name: string;
  description: string | null;
  flooring: string | null;
  wall_finish: string | null;
  ceiling_finish: string | null;
  cabinetry: string | null;
  countertop: string | null;
  backsplash: string | null;
  bathroom_finish: string | null;
  metal_finish: string | null;
  door_finish: string | null;
  color_palette: Record<string, string> | null;
  reference_document_ids: string[] | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface FurnitureItem {
  id: string;
  name: string;
  code: string;
  room_type: string | null;
  furniture_type: FurnitureType;
  width: number | null;
  depth: number | null;
  height: number | null;
  measurement_unit: string;
  default_rotation: number;
  icon_or_preview: string | null;
  metadata: Record<string, unknown> | null;
  is_system_item: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface VersionCompareDiff {
  style_preset_changed: boolean;
  style_preset_a: string | null;
  style_preset_b: string | null;
  material_package_changed: boolean;
  material_package_a: string | null;
  material_package_b: string | null;
  furniture_count_a: number;
  furniture_count_b: number;
  furniture_added: string[];
  furniture_removed: string[];
  furniture_moved: string[];
  colors_changed: boolean;
  color_diff_summary: string | null;
}

export interface VersionCompareResult {
  version_a: DesignVersion;
  version_b: DesignVersion;
  design_status: DesignStatus;
  diff: VersionCompareDiff;
  comparison_note: string;
}

export interface DesignSourceRegion {
  id: string;
  label: string | null;
  element_type: string;
  has_geometry: boolean;
}

export interface CompatibleSourceDocument {
  id: string;
  title: string;
  document_type: string;
  document_version_id: string;
  drawing_analysis_id: string | null;
  preview_status: string | null;
  has_room_regions: boolean;
}

export interface DesignFilters {
  search?: string;
  project_id?: string;
  design_type?: string;
  status?: string;
}

export interface DesignProjectInput {
  project_id: string;
  document_id: string;
  document_version_id?: string;
  drawing_analysis_id?: string;
  title: string;
  description?: string;
  design_type: DesignType;
}

function buildQuery(filters: DesignFilters): string {
  const params = new URLSearchParams();
  if (filters.search) params.set('search', filters.search);
  if (filters.project_id) params.set('project_id', filters.project_id);
  if (filters.design_type) params.set('design_type', filters.design_type);
  if (filters.status) params.set('status', filters.status);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchDesignProjects(filters: DesignFilters = {}): Promise<{ items: DesignProject[]; total: number }> {
  return apiFetch(`/design/projects${buildQuery(filters)}`);
}

export async function fetchDesignProject(id: string): Promise<DesignProject> {
  return apiFetch(`/design/projects/${id}`);
}

export async function createDesignProject(input: DesignProjectInput): Promise<DesignProject> {
  return apiFetch('/design/projects', { method: 'POST', body: JSON.stringify(input) });
}

export async function updateDesignProject(id: string, input: Partial<DesignProjectInput>): Promise<DesignProject> {
  return apiFetch(`/design/projects/${id}`, { method: 'PATCH', body: JSON.stringify(input) });
}

export async function archiveDesignProject(id: string): Promise<DesignProject> {
  return apiFetch(`/design/projects/${id}/archive`, { method: 'POST' });
}

export async function submitDesignForReview(id: string): Promise<DesignProject> {
  return apiFetch(`/design/projects/${id}/submit-review`, { method: 'POST' });
}

export async function requestDesignRevision(id: string, comment?: string): Promise<DesignProject> {
  return apiFetch(`/design/projects/${id}/request-revision`, {
    method: 'POST',
    body: JSON.stringify({ comment: comment ?? null }),
  });
}

export async function approveDesignProject(id: string, comment?: string): Promise<DesignProject> {
  return apiFetch(`/design/projects/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ comment: comment ?? null }),
  });
}

export async function rejectDesignProject(id: string, comment?: string): Promise<DesignProject> {
  return apiFetch(`/design/projects/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ comment: comment ?? null }),
  });
}

export async function fetchDesignVersions(designProjectId: string): Promise<{ items: DesignVersion[]; total: number }> {
  return apiFetch(`/design/projects/${designProjectId}/versions`);
}

export async function saveDesignVersion(
  designProjectId: string,
  designParameters: DesignParameters,
): Promise<DesignVersion> {
  return apiFetch(`/design/projects/${designProjectId}/versions`, {
    method: 'POST',
    body: JSON.stringify({ design_parameters: designParameters }),
  });
}

export async function compareDesignVersions(
  designProjectId: string,
  versionAId: string,
  versionBId: string,
): Promise<VersionCompareResult> {
  return apiFetch(`/design/projects/${designProjectId}/compare-versions`, {
    method: 'POST',
    body: JSON.stringify({ version_a_id: versionAId, version_b_id: versionBId }),
  });
}

export async function applyMaterialPackage(
  designProjectId: string,
  materialPackageId: string,
  designParameters?: DesignParameters,
): Promise<DesignVersion> {
  return apiFetch(`/design/projects/${designProjectId}/apply-material-package`, {
    method: 'POST',
    body: JSON.stringify({
      material_package_id: materialPackageId,
      design_parameters: designParameters ?? null,
    }),
  });
}

export async function fetchDesignSourceRegions(
  designProjectId: string,
): Promise<{ mode: string; regions: DesignSourceRegion[] }> {
  return apiFetch(`/design/projects/${designProjectId}/source-regions`);
}

export async function fetchCompatibleSourceDocuments(
  projectId: string,
): Promise<{ items: CompatibleSourceDocument[]; total: number }> {
  return apiFetch(`/design/compatible-documents?project_id=${projectId}`);
}

export async function fetchStylePresets(search?: string): Promise<{ items: StylePreset[]; total: number }> {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  return apiFetch(`/design/style-presets${query}`);
}

export async function fetchStylePreset(id: string): Promise<StylePreset> {
  return apiFetch(`/design/style-presets/${id}`);
}

export async function createStylePreset(input: {
  name: string;
  code: string;
  description?: string;
  color_palette?: Record<string, string>;
}): Promise<StylePreset> {
  return apiFetch('/design/style-presets', { method: 'POST', body: JSON.stringify(input) });
}

export async function fetchMaterialPackages(search?: string): Promise<{ items: MaterialPackage[]; total: number }> {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  return apiFetch(`/design/material-packages${query}`);
}

export async function fetchMaterialPackage(id: string): Promise<MaterialPackage> {
  return apiFetch(`/design/material-packages/${id}`);
}

export async function createMaterialPackage(input: Partial<MaterialPackage> & { name: string }): Promise<MaterialPackage> {
  return apiFetch('/design/material-packages', { method: 'POST', body: JSON.stringify(input) });
}

export async function fetchFurnitureItems(filters?: {
  search?: string;
  room_type?: string;
  furniture_type?: string;
}): Promise<{ items: FurnitureItem[]; total: number }> {
  const params = new URLSearchParams();
  if (filters?.search) params.set('search', filters.search);
  if (filters?.room_type) params.set('room_type', filters.room_type);
  if (filters?.furniture_type) params.set('furniture_type', filters.furniture_type);
  const query = params.toString();
  return apiFetch(`/design/furniture${query ? `?${query}` : ''}`);
}

export { formatDate as formatDesignDate };
