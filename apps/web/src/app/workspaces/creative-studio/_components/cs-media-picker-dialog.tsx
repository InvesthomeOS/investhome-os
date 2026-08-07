'use client';

import { Dialog } from '@investhome/ui';

import { CsMediaPicker, type CsMediaPickerProps } from './cs-media-picker';

export type CsMediaPickerDialogProps = Omit<CsMediaPickerProps, 'variant' | 'onClose'> & {
  open: boolean;
  onClose: () => void;
  title?: string;
};

/**
 * Shared Choose Asset dialog — one picker for all Creative Studio builders.
 */
export function CsMediaPickerDialog({
  open,
  onClose,
  title,
  labels,
  ...pickerProps
}: CsMediaPickerDialogProps) {
  const dialogTitle = title ?? labels?.title ?? labels?.chooseAsset ?? 'Choose Asset';
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={dialogTitle}
      ariaLabel={dialogTitle}
    >
      <CsMediaPicker
        {...pickerProps}
        labels={labels}
        variant="panel"
        onClose={onClose}
        testId={pickerProps.testId ?? 'cs-media-picker-dialog'}
      />
    </Dialog>
  );
}
