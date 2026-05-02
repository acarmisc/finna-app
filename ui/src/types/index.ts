export type ToastTone = 'info' | 'success' | 'warning' | 'danger';

export interface Toast {
  id: string;
  message: string;
  tone?: ToastTone;
}
