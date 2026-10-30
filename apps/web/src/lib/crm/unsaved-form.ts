export const DISCARD_UNSAVED_TR = 'Kaydedilmemiş değişiklikler var. Kapatılsın mı?';
export const DISCARD_UNSAVED_EN = 'There are unsaved changes. Close without saving?';
export const SAVE_FAILED_TR = 'Kayıt kaydedilemedi. Yeniden deneyin.';
export const SAVE_FAILED_EN = 'The record could not be saved. Try again.';

export function confirmDiscardUnsaved(tr: boolean): boolean {
  return window.confirm(tr ? DISCARD_UNSAVED_TR : DISCARD_UNSAVED_EN);
}

export function saveFailedMessage(tr: boolean): string {
  return tr ? SAVE_FAILED_TR : SAVE_FAILED_EN;
}
