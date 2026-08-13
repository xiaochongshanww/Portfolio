/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'vditor' {
  const Vditor: any
  export default Vditor
}

interface Window {
  vueErrorHandler?: (event: PromiseRejectionEvent) => void;
  vditorErrorCleanup?: (() => void) | null;
  vditorCleanupFunctions?: Array<() => void>;
  markdownTest?: unknown;
  testBatchMessages?: () => void;
  openMediaLibrary?: () => void;
  categoryAutoRecommendTimer?: ReturnType<typeof setTimeout>;
}
