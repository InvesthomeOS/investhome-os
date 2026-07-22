import { fetchDepartments, type DepartmentListParams } from '@/lib/api/departments';

export const departmentQueryKeys = {
  all: ['departments'] as const,
  list: (params: DepartmentListParams) => ['departments', 'list', params] as const,
};

export const departmentQueries = {
  list: (params: DepartmentListParams) => ({
    queryKey: departmentQueryKeys.list(params),
    queryFn: () => fetchDepartments(params),
  }),
};
