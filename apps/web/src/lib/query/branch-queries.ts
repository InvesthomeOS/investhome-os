import {
  archiveBranch,
  assignBranchManager,
  createBranch,
  deactivateBranch,
  deleteBranch,
  duplicateBranch,
  fetchBranch,
  fetchBranches,
  updateBranch,
  type BranchInput,
  type BranchListParams,
} from '@/lib/api/branches';

export const branchQueryKeys = {
  all: ['branches'] as const,
  list: (params: BranchListParams) => ['branches', 'list', params] as const,
  detail: (id: string) => ['branches', 'detail', id] as const,
};

export const branchQueries = {
  list: (params: BranchListParams) => ({
    queryKey: branchQueryKeys.list(params),
    queryFn: () => fetchBranches(params),
  }),
  detail: (id: string) => ({
    queryKey: branchQueryKeys.detail(id),
    queryFn: () => fetchBranch(id),
    enabled: Boolean(id),
  }),
};

export const branchMutations = {
  create: createBranch,
  update: updateBranch,
  delete: deleteBranch,
  archive: archiveBranch,
  deactivate: deactivateBranch,
  duplicate: duplicateBranch,
  assignManager: assignBranchManager,
};

export type { BranchInput, BranchListParams };
