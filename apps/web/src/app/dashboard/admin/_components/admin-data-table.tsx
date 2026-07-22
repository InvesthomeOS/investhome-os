'use client';

import { Button, Pagination, Table, TableToolbar } from '@investhome/ui';
import { useMemo, useState, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';

export type AdminTableColumn<T> = {
  id: string;
  header: string;
  sortable?: boolean;
  render: (row: T) => ReactNode;
  exportValue?: (row: T) => string;
  defaultVisible?: boolean;
};

type AdminDataTableProps<T> = {
  rows: T[];
  columns: AdminTableColumn<T>[];
  rowKey: (row: T) => string;
  pageSize?: number;
  activeRowKey?: string | null;
  onRowClick?: (row: T) => void;
  exportFileName?: string;
  emptyMessage?: string;
  selectedIds?: string[];
  onSelectedIdsChange?: (ids: string[]) => void;
};

function compareValues(a: string, b: string): number {
  return a.localeCompare(b, undefined, { sensitivity: 'base' });
}

export function AdminDataTable<T>({
  rows,
  columns,
  rowKey,
  pageSize = 25,
  activeRowKey = null,
  onRowClick,
  exportFileName = 'admin-export.csv',
  emptyMessage,
  selectedIds,
  onSelectedIdsChange,
}: AdminDataTableProps<T>) {
  const t = useTranslations('adminShell.table');
  const tCommon = useTranslations('common');
  const [page, setPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(
    () => new Set(columns.filter((column) => column.defaultVisible !== false).map((column) => column.id)),
  );
  const [internalSelectedKeys, setInternalSelectedKeys] = useState<Set<string>>(new Set());
  const selectedKeys = useMemo(
    () => (selectedIds ? new Set(selectedIds) : internalSelectedKeys),
    [selectedIds, internalSelectedKeys],
  );

  const updateSelection = (next: Set<string>) => {
    if (onSelectedIdsChange) {
      onSelectedIdsChange(Array.from(next));
      return;
    }
    setInternalSelectedKeys(next);
  };

  const visibleColumnList = columns.filter((column) => visibleColumns.has(column.id));

  const sortedRows = useMemo(() => {
    if (!sortColumn) {
      return rows;
    }
    const column = columns.find((item) => item.id === sortColumn);
    if (!column?.exportValue) {
      return rows;
    }
    const sorted = [...rows].sort((left, right) => {
      const result = compareValues(column.exportValue!(left), column.exportValue!(right));
      return sortDirection === 'asc' ? result : -result;
    });
    return sorted;
  }, [columns, rows, sortColumn, sortDirection]);

  const totalPages = Math.max(1, Math.ceil(sortedRows.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageRows = sortedRows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const toggleSort = (columnId: string) => {
    if (sortColumn === columnId) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortColumn(columnId);
    setSortDirection('asc');
  };

  const toggleColumn = (columnId: string) => {
    setVisibleColumns((current) => {
      const next = new Set(current);
      if (next.has(columnId)) {
        if (next.size <= 1) {
          return next;
        }
        next.delete(columnId);
      } else {
        next.add(columnId);
      }
      return next;
    });
  };

  const toggleRowSelection = (key: string) => {
    const next = new Set(selectedKeys);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    updateSelection(next);
  };

  const exportCsv = () => {
    const exportColumns = visibleColumnList.filter((column) => column.exportValue);
    const header = exportColumns.map((column) => column.header).join(',');
    const body = sortedRows
      .map((row) =>
        exportColumns
          .map((column) => `"${(column.exportValue?.(row) ?? '').replace(/"/g, '""')}"`)
          .join(','),
      )
      .join('\n');
    const blob = new Blob([`${header}\n${body}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = exportFileName;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (rows.length === 0 && emptyMessage) {
    return <p>{emptyMessage}</p>;
  }

  return (
    <div className="admin-data-table">
      <TableToolbar
        actions={
          <>
            <Button type="button" variant="secondary" onClick={exportCsv}>
              {t('export')}
            </Button>
          </>
        }
      >
        <details className="admin-data-table__columns">
          <summary>{t('columns')}</summary>
          <div className="admin-data-table__column-list">
            {columns.map((column) => (
              <label key={column.id}>
                <input
                  type="checkbox"
                  checked={visibleColumns.has(column.id)}
                  onChange={() => toggleColumn(column.id)}
                />
                {column.header}
              </label>
            ))}
          </div>
        </details>
      </TableToolbar>

      <Table wrapClassName="ih-table-wrap admin-table-wrap admin-table-wrap--sticky">
        <thead>
          <tr>
            <th scope="col">
              <span className="sr-only">{t('select')}</span>
            </th>
            {visibleColumnList.map((column) => (
              <th
                key={column.id}
                scope="col"
                aria-sort={
                  column.sortable && sortColumn === column.id
                    ? sortDirection === 'asc'
                      ? 'ascending'
                      : 'descending'
                    : undefined
                }
              >
                {column.sortable ? (
                  <button
                    type="button"
                    className="admin-data-table__sort ih-table__sort"
                    data-sort={sortColumn === column.id ? sortDirection : undefined}
                    onClick={() => toggleSort(column.id)}
                  >
                    {column.header}
                    <span className="ih-table__sort-indicator" aria-hidden="true">
                      ▲
                    </span>
                  </button>
                ) : (
                  column.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {pageRows.map((row) => {
            const key = rowKey(row);
            const isActive = activeRowKey === key;
            return (
              <tr
                key={key}
                className={
                  [isActive ? 'admin-table__row--active' : null, selectedKeys.has(key) ? 'admin-table__row--selected' : null]
                    .filter(Boolean)
                    .join(' ') || undefined
                }
                aria-selected={selectedKeys.has(key) || isActive ? true : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                <td>
                  <input
                    type="checkbox"
                    checked={selectedKeys.has(key)}
                    aria-label={t('selectRow')}
                    onChange={() => toggleRowSelection(key)}
                    onClick={(event) => event.stopPropagation()}
                  />
                </td>
                {visibleColumnList.map((column) => (
                  <td key={column.id}>{column.render(row)}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </Table>

      <Pagination
        page={currentPage}
        pageSize={pageSize}
        total={sortedRows.length}
        onPrevious={() => setPage((current) => Math.max(1, current - 1))}
        onNext={() => setPage((current) => Math.min(totalPages, current + 1))}
        previousLabel={tCommon('backToDashboard').startsWith('←') ? '←' : t('previous')}
        nextLabel={t('next')}
        ariaLabel={t('ariaLabel')}
        summary={t('pageSummary', { page: currentPage, totalPages, count: sortedRows.length })}
      />
    </div>
  );
}
