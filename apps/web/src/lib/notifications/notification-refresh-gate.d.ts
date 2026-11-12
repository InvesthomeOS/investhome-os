export function createNotificationRefreshGate(): (task: () => Promise<void>) => Promise<void>;
