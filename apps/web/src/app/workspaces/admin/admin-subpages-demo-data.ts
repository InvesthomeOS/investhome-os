import type { AdminIntegrationsPreview, SystemLogsPreview } from './admin-subpages-model';

export function makeSystemLogsPreview(): SystemLogsPreview {
  return {
    rows: [
      {
        id: 'log-1',
        timestamp: '26.07.2026 10:42:11',
        level: 'info',
        service: 'api',
        message: 'CRM settings snapshot exported by superadmin@investhome.demo',
        actor: 'superadmin@investhome.demo',
      },
      {
        id: 'log-2',
        timestamp: '26.07.2026 10:38:02',
        level: 'warning',
        service: 'worker',
        message: 'Queue depth above soft threshold (pending=128)',
        actor: 'system',
      },
      {
        id: 'log-3',
        timestamp: '26.07.2026 10:21:44',
        level: 'error',
        service: 'integrations',
        message: 'QuickBooks sync failed — credentials expired',
        actor: 'system',
      },
      {
        id: 'log-4',
        timestamp: '26.07.2026 09:55:18',
        level: 'info',
        service: 'web',
        message: 'Admin workspace session started',
        actor: 'superadmin@investhome.demo',
      },
      {
        id: 'log-5',
        timestamp: '26.07.2026 09:12:03',
        level: 'debug',
        service: 'api',
        message: 'Search index warm-up completed in 412ms',
        actor: 'system',
      },
      {
        id: 'log-6',
        timestamp: '25.07.2026 22:04:51',
        level: 'warning',
        service: 'storage',
        message: 'Object store latency spike (p95=890ms)',
        actor: 'system',
      },
    ],
  };
}

export function makeAdminIntegrationsPreview(): AdminIntegrationsPreview {
  return {
    rows: [
      {
        id: 'google-calendar',
        name: 'Google Calendar',
        provider: 'Google',
        status: 'connected',
        lastSync: '12 min ago',
        icon: 'calendar',
      },
      {
        id: 'outlook',
        name: 'Outlook',
        provider: 'Microsoft',
        status: 'connected',
        lastSync: '1 hour ago',
        icon: 'inbox',
      },
      {
        id: 'slack',
        name: 'Slack',
        provider: 'Slack',
        status: 'connected',
        lastSync: 'Live',
        icon: 'activity',
      },
      {
        id: 'quickbooks',
        name: 'QuickBooks',
        provider: 'Intuit',
        status: 'disconnected',
        lastSync: 'Never',
        icon: 'documents',
      },
      {
        id: 'zapier',
        name: 'Zapier',
        provider: 'Zapier',
        status: 'degraded',
        lastSync: '1 day ago',
        icon: 'sparkles',
      },
      {
        id: 'whatsapp',
        name: 'WhatsApp Business',
        provider: 'Meta',
        status: 'connected',
        lastSync: '4 min ago',
        icon: 'bell',
      },
    ],
  };
}
