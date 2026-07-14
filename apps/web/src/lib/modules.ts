import { MODULE_NAMES, type ModuleName } from '@investhome/shared';

export function isModuleName(value: string): value is ModuleName {
  return (MODULE_NAMES as readonly string[]).includes(value);
}
