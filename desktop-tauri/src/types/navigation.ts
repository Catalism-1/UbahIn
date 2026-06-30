export type PageId =
  | 'home'
  | 'pdf'
  | 'image'
  | 'heic'
  | 'history'
  | 'settings'
  | 'engine'
  | 'merge-pdf'
  | 'compress-pdf'
  | 'resize-image'
  | 'pdf-word';

export interface NavigationItem {
  id: PageId;
  label: string;
  icon: string;
}

export type EngineStatus = 'unchecked' | 'checking' | 'ready' | 'error';
