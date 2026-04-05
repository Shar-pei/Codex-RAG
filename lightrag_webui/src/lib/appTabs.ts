export const APP_TABS = [
  {
    id: 'documents',
    labelKey: 'header.documents',
    contentClassName: 'absolute inset-0 overflow-auto'
  },
  {
    id: 'knowledge-graph',
    labelKey: 'header.knowledgeGraph',
    contentClassName: 'absolute inset-0 overflow-hidden'
  },
  {
    id: 'retrieval',
    labelKey: 'header.retrieval',
    contentClassName: 'absolute inset-0 overflow-hidden'
  },
  {
    id: 'api',
    labelKey: 'header.api',
    contentClassName: 'absolute inset-0 overflow-hidden'
  }
] as const

export type AppTab = (typeof APP_TABS)[number]['id']

export const DEFAULT_APP_TAB: AppTab = 'documents'
