'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { relationshipQueries } from '@/workspaces/crm/hooks/use-relationships';
import type { CrmGraphEdge, CrmGraphNode } from '@/workspaces/crm/api/relationships';

import './relationships-workspace.css';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

const NODE_COLORS: Record<string, string> = {
  contact: '#1f4e5f',
  company: '#2f6f6a',
  project: '#c4a35a',
  investment: '#c47a3a',
  property: '#6b7c8a',
};

const TYPE_LABELS: Record<string, string> = {
  contact_company: 'Kişi ↔ Şirket',
  investor: 'Kişi ↔ Proje / Yatırım',
  colleague: 'Kişi ↔ Kişi',
  partner: 'Ortaklık / Co-owner',
  company_project: 'Şirket ↔ Proje',
};

type Props = {
  embedded?: boolean;
  search?: string;
  relationshipType?: string;
  projectGroup?: string;
  pairKind?: string;
};

export function RelationshipNetworkView({
  embedded = false,
  search = '',
  relationshipType = '',
  projectGroup = '',
  pairKind = '',
}: Props) {
  const locale = useLocale();
  const tr = locale.startsWith('tr');
  const router = useRouter();
  const { openContact } = useContactCard();
  const { authLoading, canRead } = useCrmAccess();
  const graphRef = useRef<{ zoomToFit?: (ms?: number) => void } | undefined>(undefined);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [localSearch, setLocalSearch] = useState(search);

  useEffect(() => {
    setLocalSearch(search);
  }, [search]);

  const graphParams = useMemo(
    () => ({
      limit: 200,
      relationship_type: relationshipType || undefined,
      project_group: projectGroup || undefined,
      pair_kind: pairKind || undefined,
    }),
    [pairKind, projectGroup, relationshipType],
  );

  const graphQuery = useQuery({
    ...relationshipQueries.graph(graphParams),
    enabled: !authLoading && canRead,
  });

  const graphData = useMemo(() => {
    const nodes = graphQuery.data?.nodes ?? [];
    const edges = graphQuery.data?.edges ?? [];
    const query = localSearch.trim().toLowerCase();
    const filteredNodes = query
      ? nodes.filter((node) => node.label.toLowerCase().includes(query))
      : nodes;
    const nodeIds = new Set(filteredNodes.map((node) => node.id));
    return {
      nodes: filteredNodes.map((node) => ({
        ...node,
        color: NODE_COLORS[node.entity_type] || '#6b7c8a',
      })),
      links: edges
        .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
        .map((edge) => ({
          ...edge,
          source: edge.source,
          target: edge.target,
        })),
    };
  }, [graphQuery.data, localSearch]);

  const selectedNode: CrmGraphNode | undefined = graphQuery.data?.nodes.find((node) => node.id === selectedNodeId);
  const selectedEdge: CrmGraphEdge | undefined = graphQuery.data?.edges.find((edge) => edge.id === selectedEdgeId);

  const openNode = useCallback(
    (node: CrmGraphNode) => {
      if (node.entity_type === 'contact') {
        openContact(node.entity_id);
        return;
      }
      if (node.entity_type === 'company') {
        router.push(`/workspaces/crm/companies/${node.entity_id}`);
        return;
      }
      if (node.entity_type === 'project') {
        router.push(`/dashboard/projects/${node.entity_id}`);
      }
    },
    [openContact, router],
  );

  const handleNodeClick = useCallback(
    (node: { id?: string | number }) => {
      if (!node?.id) return;
      const nodeId = String(node.id);
      setSelectedNodeId(nodeId);
      setSelectedEdgeId(null);
      const found = graphQuery.data?.nodes.find((item) => item.id === nodeId);
      if (found) openNode(found);
    },
    [graphQuery.data?.nodes, openNode],
  );

  const handleLinkClick = useCallback((link: { id?: string | number; relationship_id?: string }) => {
    const edgeId = link?.id ? String(link.id) : null;
    setSelectedEdgeId(edgeId);
    setSelectedNodeId(null);
    const relationshipId = link?.relationship_id || edgeId;
    if (relationshipId) router.push(`/workspaces/crm/relationships/${relationshipId}`);
  }, [router]);

  useEffect(() => {
    if (graphRef.current && graphData.nodes.length > 0) {
      setTimeout(() => graphRef.current?.zoomToFit?.(400), 300);
    }
  }, [graphData.nodes.length]);

  if (authLoading) return <LoadingState label={tr ? 'Yükleniyor…' : 'Loading…'} />;
  if (!canRead) {
    return <ErrorState title={tr ? 'Erişim yok' : 'Access denied'} message={tr ? 'Erişim yok' : 'Access denied'} />;
  }
  if (graphQuery.isLoading) return <LoadingState label={tr ? 'Ağ yükleniyor…' : 'Loading graph…'} />;
  if (graphQuery.isError) {
    return (
      <ErrorState
        title={tr ? 'Ağ yüklenemedi' : 'Graph failed'}
        message={graphQuery.error?.message ?? (tr ? 'Ağ yüklenemedi' : 'Graph failed')}
        action={
          <Button type="button" onClick={() => void graphQuery.refetch()}>
            {tr ? 'Yeniden dene' : 'Retry'}
          </Button>
        }
      />
    );
  }

  return (
    <div className={embedded ? 'crm-rel-graph' : 'crm-network-view'} data-testid="crm-relationships-graph">
      {!embedded ? (
        <header className="ctc-ds__header">
          <div>
            <h1>{tr ? 'Ağ Grafiği' : 'Network graph'}</h1>
            <p>{tr ? 'Yalnızca CRM’de kayıtlı ilişkiler.' : 'Only stored CRM relationships.'}</p>
          </div>
          <Link href="/workspaces/crm/relationships" className="crm-people-tools">
            {tr ? 'Listeye dön' : 'Back to list'}
          </Link>
        </header>
      ) : null}

      {!embedded ? (
        <div className="crm-network-toolbar">
          <input
            type="search"
            value={localSearch}
            onChange={(event) => setLocalSearch(event.target.value)}
            placeholder={tr ? 'Düğüm ara' : 'Search nodes'}
            aria-label={tr ? 'Düğüm ara' : 'Search nodes'}
            data-testid="crm-relationships-graph-search"
          />
        </div>
      ) : null}

      {graphQuery.data?.warning ? <p className="crm-agreements-count">{graphQuery.data.warning}</p> : null}
      <p className="crm-agreements-count" data-testid="crm-relationships-graph-stats">
        {tr
          ? `${graphData.nodes.length} düğüm · ${graphData.links.length} ilişki`
          : `${graphData.nodes.length} nodes · ${graphData.links.length} edges`}
      </p>

      {graphData.nodes.length === 0 ? (
        <EmptyState
          title={tr ? 'Gösterilecek ilişki yok' : 'No relationships to graph'}
          description={tr ? 'Filtreleri daraltın veya kayıtlı bir ilişki seçin.' : 'Narrow filters or pick a stored relationship.'}
        />
      ) : (
        <div className="crm-rel-graph-canvas">
          <ForceGraph2D
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ref={graphRef as any}
            graphData={graphData}
            nodeLabel="label"
            nodeColor="color"
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            onNodeClick={handleNodeClick}
            onLinkClick={handleLinkClick}
            cooldownTicks={80}
          />
        </div>
      )}

      {selectedNode ? (
        <aside className="crm-rel-graph-panel">
          <h3>{selectedNode.label}</h3>
          <p>{selectedNode.entity_type}</p>
          <Button type="button" variant="secondary" size="sm" onClick={() => openNode(selectedNode)}>
            {tr ? 'Kayda git' : 'Open record'}
          </Button>
        </aside>
      ) : null}

      {selectedEdge ? (
        <aside className="crm-rel-graph-panel">
          <h3>{TYPE_LABELS[selectedEdge.relationship_type] || selectedEdge.relationship_type}</h3>
          <p>{selectedEdge.source} → {selectedEdge.target}</p>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => router.push(`/workspaces/crm/relationships/${selectedEdge.relationship_id}`)}
          >
            {tr ? 'İlişki detayı' : 'Relationship detail'}
          </Button>
        </aside>
      ) : null}

      <div>
        <Button variant="secondary" size="sm" onClick={() => graphRef.current?.zoomToFit?.(400)}>
          {tr ? 'Sığdır' : 'Fit'}
        </Button>
      </div>
    </div>
  );
}
