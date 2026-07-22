'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useMemo, useRef } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  relationshipQueries,
  relationshipQueryKeys,
  relationshipMutations,
} from '@/workspaces/crm/hooks/use-relationships';
import {
  getScoreBandColor,
  useRelationshipGraphUiStore,
} from '@/workspaces/crm/stores/relationship-graph-ui-store';
import type { CrmGraphNode } from '@/workspaces/crm/api/relationships';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

export function RelationshipNetworkView() {
  const t = useTranslations('crm.relationships.network');
  const tCommon = useTranslations('common');
  const { authLoading, canRead } = useCrmAccess();
  const queryClient = useQueryClient();
  const graphRef = useRef<{ zoomToFit?: (ms?: number) => void } | undefined>(undefined);
  const {
    selectedNodeId,
    searchQuery,
    depth,
    limit,
    centerEntityType,
    centerEntityId,
    categoryFilter,
    typeFilter,
    setSelectedNodeId,
    setSearchQuery,
    setDepth,
    setCenter,
    markExpanded,
  } = useRelationshipGraphUiStore();

  const graphParams = useMemo(
    () => ({
      center_entity_type: centerEntityType ?? undefined,
      center_entity_id: centerEntityId ?? undefined,
      depth,
      limit,
      category: categoryFilter ?? undefined,
      relationship_type: typeFilter ?? undefined,
    }),
    [centerEntityType, centerEntityId, depth, limit, categoryFilter, typeFilter],
  );

  const graphQuery = useQuery({
    ...relationshipQueries.graph(graphParams),
    enabled: !authLoading && canRead,
  });

  const expandMutation = useMutation({
    mutationFn: ({ nodeId, expandDepth }: { nodeId: string; expandDepth: number }) =>
      relationshipMutations.expandNode(nodeId, expandDepth),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: relationshipQueryKeys.all }),
  });

  const graphData = useMemo(() => {
    const nodes = graphQuery.data?.nodes ?? [];
    const edges = graphQuery.data?.edges ?? [];
    const filteredNodes = searchQuery
      ? nodes.filter((n) => n.label.toLowerCase().includes(searchQuery.toLowerCase()))
      : nodes;
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return {
      nodes: filteredNodes.map((n) => ({
        ...n,
        color: getScoreBandColor(n.score),
      })),
      links: edges
        .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
        .map((e) => ({
          ...e,
          source: e.source,
          target: e.target,
        })),
    };
  }, [graphQuery.data, searchQuery]);

  const selectedNode: CrmGraphNode | undefined = graphQuery.data?.nodes.find(
    (n) => n.id === selectedNodeId,
  );

  const handleNodeClick = useCallback(
    (node: { id?: string | number }) => {
      if (!node?.id) return;
      const nodeId = String(node.id);
      setSelectedNodeId(nodeId);
      setCenter(nodeId.split(':')[0] ?? null, nodeId.split(':')[1] ?? null);
    },
    [setSelectedNodeId, setCenter],
  );

  const handleExpand = useCallback(() => {
    if (!selectedNodeId) return;
    markExpanded(selectedNodeId);
    expandMutation.mutate({ nodeId: selectedNodeId, expandDepth: 1 });
  }, [selectedNodeId, markExpanded, expandMutation]);

  const handleExportData = useCallback(() => {
    if (!graphQuery.data) return;
    const blob = new Blob([JSON.stringify(graphQuery.data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'relationship-graph.json';
    a.click();
    URL.revokeObjectURL(url);
  }, [graphQuery.data]);

  useEffect(() => {
    if (graphRef.current && graphData.nodes.length > 0) {
      setTimeout(() => graphRef.current?.zoomToFit?.(400), 300);
    }
  }, [graphData.nodes.length]);

  if (authLoading) return <LoadingState label={tCommon('loading')} />;
  if (!canRead) return <ErrorState title={t('accessDenied')} message={t('accessDenied')} />;
  if (graphQuery.isLoading) return <LoadingState label={t('loading')} />;
  if (graphQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={graphQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void graphQuery.refetch()}>
            {t('loadFailed')}
          </Button>
        }
      />
    );
  }

  return (
    <div className="crm-network-view">
      <header className="crm-workspace-header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('description')}</p>
        </div>
        <div className="crm-workspace-actions">
          <Link href="/workspaces/crm/relationships">
            <Button variant="secondary">{t('backToList')}</Button>
          </Link>
          <Button variant="secondary" onClick={() => graphRef.current?.zoomToFit?.(400)}>
            {t('fitView')}
          </Button>
          <Button variant="secondary" onClick={handleExportData}>
            {t('exportData')}
          </Button>
        </div>
      </header>

      <div className="crm-network-toolbar">
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t('searchNodes')}
          aria-label={t('searchNodes')}
        />
        <label>
          {t('depth')}
          <input
            type="range"
            min={1}
            max={5}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
          />
          {depth}
        </label>
        {graphQuery.data?.warning && <span className="crm-network-warning">{graphQuery.data.warning}</span>}
      </div>

      {graphData.nodes.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <div className="crm-network-canvas" style={{ height: 560, border: '1px solid var(--border, #e5e7eb)' }}>
          <ForceGraph2D
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ref={graphRef as any}
            graphData={graphData}
            nodeLabel="label"
            nodeColor="color"
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            onNodeClick={handleNodeClick}
            cooldownTicks={80}
          />
        </div>
      )}

      {selectedNode && (
        <aside className="crm-network-detail-panel">
          <h3>{selectedNode.label}</h3>
          <p>{t('entityType')}: {selectedNode.entity_type}</p>
          <p>
            {t('score')}:{' '}
            <span style={{ color: getScoreBandColor(selectedNode.score) }}>{selectedNode.score}</span>
          </p>
          <Button onClick={handleExpand} disabled={expandMutation.isPending}>
            {t('expandNode')}
          </Button>
        </aside>
      )}
    </div>
  );
}
