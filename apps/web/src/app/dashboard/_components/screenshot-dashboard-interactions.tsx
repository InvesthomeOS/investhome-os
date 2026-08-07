'use client';

import {
  Button,
  Dialog,
  Drawer,
  Input,
  Select,
  TextArea,
} from '@investhome/ui';
import { useTranslations } from 'next-intl';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

export type QuickActionId = 'lead' | 'task' | 'meeting' | 'investor' | 'note' | 'document';

type FieldType = 'text' | 'tel' | 'email' | 'date' | 'time' | 'number' | 'file' | 'textarea' | 'select';

type QuickField = {
  key: string;
  type: FieldType;
};

type QuickActionDefinition = {
  id: QuickActionId;
  icon: IhIconName;
  fields: readonly QuickField[];
};

export const QUICK_ACTIONS: readonly QuickActionDefinition[] = [
  {
    id: 'lead',
    icon: 'sales',
    fields: [
      { key: 'fullName', type: 'text' },
      { key: 'phone', type: 'tel' },
      { key: 'email', type: 'email' },
      { key: 'source', type: 'select' },
      { key: 'projectInterest', type: 'select' },
      { key: 'note', type: 'textarea' },
    ],
  },
  {
    id: 'task',
    icon: 'check',
    fields: [
      { key: 'taskTitle', type: 'text' },
      { key: 'assignee', type: 'text' },
      { key: 'dueDate', type: 'date' },
      { key: 'priority', type: 'select' },
      { key: 'relatedProject', type: 'select' },
      { key: 'description', type: 'textarea' },
    ],
  },
  {
    id: 'meeting',
    icon: 'meeting',
    fields: [
      { key: 'meetingTitle', type: 'text' },
      { key: 'date', type: 'date' },
      { key: 'time', type: 'time' },
      { key: 'participants', type: 'text' },
      { key: 'relatedProject', type: 'select' },
      { key: 'note', type: 'textarea' },
    ],
  },
  {
    id: 'investor',
    icon: 'investors',
    fields: [
      { key: 'fullName', type: 'text' },
      { key: 'phone', type: 'tel' },
      { key: 'email', type: 'email' },
      { key: 'budget', type: 'number' },
      { key: 'projectInterest', type: 'select' },
      { key: 'note', type: 'textarea' },
    ],
  },
  {
    id: 'note',
    icon: 'documents',
    fields: [
      { key: 'title', type: 'text' },
      { key: 'content', type: 'textarea' },
      { key: 'relatedPerson', type: 'text' },
      { key: 'relatedProject', type: 'select' },
    ],
  },
  {
    id: 'document',
    icon: 'inbox',
    fields: [
      { key: 'file', type: 'file' },
      { key: 'documentType', type: 'select' },
      { key: 'relatedPerson', type: 'text' },
      { key: 'relatedProject', type: 'select' },
      { key: 'description', type: 'textarea' },
    ],
  },
] as const;

type DashboardInteractionContextValue = {
  openAi: (prompt?: string) => void;
  openQuickAction: (action: QuickActionId) => void;
  openNotifications: () => void;
  unreadCount: number;
};

const DashboardInteractionContext = createContext<DashboardInteractionContextValue | null>(null);

type ConversationMessage = {
  id: number;
  role: 'assistant' | 'user';
  text: string;
};

type ToastMessage = {
  id: number;
  text: string;
};

function QuickActionForm({
  action,
  onSubmit,
}: {
  action: QuickActionDefinition;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const t = useTranslations('screenshotDashboard');

  return (
    <form id="screenshot-quick-form" className="screenshot-interaction-form" onSubmit={onSubmit}>
      <div className="screenshot-interaction-form__grid">
        {action.fields.map((field) => {
          const label = t(`quick.fields.${field.key}`);
          if (field.type === 'textarea') {
            return (
              <TextArea
                key={field.key}
                id={`quick-${action.id}-${field.key}`}
                name={field.key}
                label={label}
                rows={3}
              />
            );
          }
          if (field.type === 'select') {
            return (
              <Select
                key={field.key}
                id={`quick-${action.id}-${field.key}`}
                name={field.key}
                label={label}
                defaultValue=""
              >
                <option value="">{t('quick.selectPlaceholder')}</option>
                <option value="option-1">{t('quick.optionOne')}</option>
                <option value="option-2">{t('quick.optionTwo')}</option>
              </Select>
            );
          }
          return (
            <Input
              key={field.key}
              id={`quick-${action.id}-${field.key}`}
              name={field.key}
              label={label}
              type={field.type}
              accept={field.type === 'file' ? '.pdf,.doc,.docx,.png,.jpg,.jpeg' : undefined}
              min={field.type === 'number' ? '0' : undefined}
            />
          );
        })}
      </div>
    </form>
  );
}

function AiDrawer({
  open,
  initialPrompt,
  onClose,
}: {
  open: boolean;
  initialPrompt: string;
  onClose: () => void;
}) {
  const t = useTranslations('screenshotDashboard');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ConversationMessage[]>([]);

  useEffect(() => {
    if (open) {
      setInput(initialPrompt);
    }
  }, [initialPrompt, open]);

  const suggestedPrompts = [
    t('ai.prompts.focus'),
    t('ai.prompts.risks'),
    t('ai.prompts.projects'),
    t('ai.prompts.tasks'),
    t('ai.prompts.sales'),
  ];

  const handleInput = (value: string) => {
    setInput(value);
  };

  const sendPrompt = () => {
    const prompt = input.trim();
    if (!prompt) return;
    const nextId = Date.now();
    setMessages((current) => [
      ...current,
      { id: nextId, role: 'user', text: prompt },
      { id: nextId + 1, role: 'assistant', text: t('ai.mockReply') },
    ]);
    setInput('');
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={t('ai.headerTitle')}
      subtitle={t('ai.subtitle')}
      size="md"
      footer={
        <div className="screenshot-ai-drawer__composer">
          <label htmlFor="screenshot-ai-input" className="sr-only">
            {t('ai.inputLabel')}
          </label>
          <input
            id="screenshot-ai-input"
            className="screenshot-ai-drawer__input"
            value={input}
            onChange={(event) => handleInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendPrompt();
              }
            }}
            placeholder={t('ai.inputPlaceholder')}
          />
          <Button type="button" size="sm" onClick={sendPrompt}>
            {t('ai.send')}
          </Button>
        </div>
      }
    >
      <div className="screenshot-ai-drawer">
        <div className="screenshot-ai-drawer__conversation" aria-live="polite">
          <div className="screenshot-ai-drawer__message is-assistant">
            <IhIcon name="sparkles" size={15} />
            <p>{t('ai.welcome')}</p>
          </div>
          {messages.map((message) => (
            <div
              key={message.id}
              className={`screenshot-ai-drawer__message is-${message.role}`}
            >
              {message.role === 'assistant' ? <IhIcon name="sparkles" size={15} /> : null}
              <p>{message.text}</p>
            </div>
          ))}
        </div>
        <section className="screenshot-ai-drawer__suggestions" aria-labelledby="ai-suggestions-title">
          <h3 id="ai-suggestions-title">{t('ai.suggestions')}</h3>
          <div>
            {suggestedPrompts.map((prompt) => (
              <button key={prompt} type="button" onClick={() => setInput(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
        </section>
      </div>
    </Drawer>
  );
}

function MockNotifications({
  open,
  unreadCount,
  onClose,
}: {
  open: boolean;
  unreadCount: number;
  onClose: () => void;
}) {
  const t = useTranslations('screenshotDashboard');

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={t('notifications.title')}
      subtitle={t('notifications.unread', { count: unreadCount })}
      size="sm"
    >
      <ul className="screenshot-notifications">
        {(['lead', 'meeting', 'payment'] as const).map((item, index) => (
          <li key={item} className={index < unreadCount ? 'is-unread' : ''}>
            <span aria-hidden="true" />
            <div>
              <strong>{t(`notifications.items.${item}.title`)}</strong>
              <p>{t(`notifications.items.${item}.body`)}</p>
              <small>{t(`notifications.items.${item}.time`)}</small>
            </div>
          </li>
        ))}
      </ul>
    </Drawer>
  );
}

export function ScreenshotDashboardInteractionProvider({ children }: { children: ReactNode }) {
  const t = useTranslations('screenshotDashboard');
  const [aiOpen, setAiOpen] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [quickAction, setQuickAction] = useState<QuickActionId | null>(null);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const unreadCount = 2;

  const openAi = useCallback((prompt = '') => {
    setAiPrompt(prompt);
    setAiOpen(true);
  }, []);

  const openQuickAction = useCallback((action: QuickActionId) => {
    setQuickAction(action);
  }, []);

  const openNotifications = useCallback(() => {
    setNotificationsOpen(true);
  }, []);

  const closeAi = useCallback(() => {
    setAiOpen(false);
    setAiPrompt('');
  }, []);

  const selectedAction = QUICK_ACTIONS.find((action) => action.id === quickAction) ?? null;

  const submitQuickAction = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedAction) return;
    const id = Date.now();
    setToasts((current) => [
      ...current.slice(-2),
      { id, text: t(`quick.actions.${selectedAction.id}.success`) },
    ]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 4000);
    setQuickAction(null);
  };

  const value = useMemo(
    () => ({ openAi, openQuickAction, openNotifications, unreadCount }),
    [openAi, openQuickAction, openNotifications],
  );

  return (
    <DashboardInteractionContext.Provider value={value}>
      {children}
      <AiDrawer open={aiOpen} initialPrompt={aiPrompt} onClose={closeAi} />
      <MockNotifications
        open={notificationsOpen}
        unreadCount={unreadCount}
        onClose={() => setNotificationsOpen(false)}
      />
      <Dialog
        open={selectedAction !== null}
        onClose={() => setQuickAction(null)}
        title={selectedAction ? t(`quick.actions.${selectedAction.id}.title`) : ''}
        footer={
          <>
            <Button type="button" variant="ghost" size="sm" onClick={() => setQuickAction(null)}>
              {t('quick.cancel')}
            </Button>
            <Button type="submit" form="screenshot-quick-form" size="sm">
              {t('quick.save')}
            </Button>
          </>
        }
      >
        {selectedAction ? (
          <QuickActionForm action={selectedAction} onSubmit={submitQuickAction} />
        ) : null}
      </Dialog>
      {toasts.length > 0 ? (
        <div className="screenshot-toast-stack" role="status" aria-live="polite">
          {toasts.map((toast) => (
            <div className="screenshot-toast" key={toast.id}>
              <IhIcon name="check" size={15} />
              <span>{toast.text}</span>
              <button
                type="button"
                aria-label={t('toastDismiss')}
                onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </DashboardInteractionContext.Provider>
  );
}

export function useScreenshotDashboardInteractions() {
  const context = useContext(DashboardInteractionContext);
  if (!context) {
    throw new Error(
      'useScreenshotDashboardInteractions must be used within ScreenshotDashboardInteractionProvider',
    );
  }
  return context;
}
