/**
 * Location intelligence refresh is a same-origin API POST plus a read-only GET poll.
 * The browser never calls Google, Walk Score, or a text AI provider.
 */

const POLL_LIMIT = 30;

export function locationRefreshPath(projectId) {
  return locationPath(projectId, '/location-intelligence/refresh');
}

export function locationReadPath(projectId) {
  return locationPath(projectId, '/location-intelligence');
}

function locationPath(projectId, suffix) {
  if (typeof projectId !== 'string' || projectId.trim() === '') {
    throw new Error('project id is required');
  }
  return `/projects/${projectId.trim()}${suffix}`;
}

export function refreshStatusFromResponse(body) {
  const status = body && typeof body.status === 'string' ? body.status : '';
  if (status === 'queued' || status === 'already_queued' || status === 'disabled') return status;
  return 'error';
}

export function shouldPollAfterRefresh(status) {
  return status === 'queued' || status === 'already_queued';
}

export function locationPollSettled(intel) {
  const status = intel && typeof intel.status === 'string' ? intel.status : '';
  return status === 'success' || status === 'failed';
}

function errorMessage(err) {
  if (err instanceof Error && err.message) return err.message;
  return 'Request failed';
}

export function createLocationRefreshController({
  projectId,
  post,
  read,
  intervalMs = 4000,
}) {
  let busy = false;
  let timer = null;
  let polls = 0;
  let polling = false;
  const listeners = new Set();

  function emit(event) {
    for (const listener of listeners) listener(event);
  }

  function stopTimer() {
    if (timer) clearInterval(timer);
    timer = null;
  }

  function finishPoll() {
    stopTimer();
    polls = 0;
    busy = false;
    emit({ type: 'idle' });
  }

  async function pollOnce() {
    if (polling) return;
    polling = true;
    polls += 1;
    try {
      const intel = await read(locationReadPath(projectId));
      emit({ type: 'intel', intel });
      if (locationPollSettled(intel) || polls >= POLL_LIMIT) finishPoll();
    } catch (err) {
      if (polls >= POLL_LIMIT) {
        stopTimer();
        polls = 0;
        busy = false;
        emit({ type: 'status', status: 'error', error: errorMessage(err) });
      }
    } finally {
      polling = false;
    }
  }

  return {
    projectId,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    async click() {
      if (busy) return { posted: false, reason: 'in_flight' };
      busy = true;
      emit({ type: 'status', status: 'working', error: null });
      try {
        const body = await post(locationRefreshPath(projectId));
        const status = refreshStatusFromResponse(body);
        if (status === 'error') {
          busy = false;
          emit({
            type: 'status',
            status: 'error',
            error: 'Unexpected refresh response',
          });
          return { posted: true, status };
        }
        emit({ type: 'status', status, error: null });
        if (shouldPollAfterRefresh(status)) {
          stopTimer();
          polls = 0;
          void pollOnce();
          timer = setInterval(() => {
            void pollOnce();
          }, intervalMs);
        } else {
          busy = false;
        }
        return { posted: true, status };
      } catch (err) {
        busy = false;
        const error = errorMessage(err);
        emit({ type: 'status', status: 'error', error });
        return { posted: true, status: 'error', error };
      }
    },
    stop() {
      stopTimer();
      busy = false;
    },
  };
}
