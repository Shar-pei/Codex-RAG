import { useState, useCallback, useEffect, useRef } from 'react'
import ApiKeyAlert from '@/components/ApiKeyAlert'
import StatusIndicator from '@/components/status/StatusIndicator'
import { SiteInfo, webuiPrefix } from '@/lib/constants'
import { useBackendState, useAuthStore } from '@/stores/state'
import { useSettingsStore } from '@/stores/settings'
import { APP_TABS, type AppTab } from '@/lib/appTabs'
import { getAuthStatus } from '@/api/lightrag'
import SiteHeader from '@/features/SiteHeader'
import { InvalidApiKeyError, RequireApiKeError } from '@/api/lightrag'
import { ZapIcon } from 'lucide-react'

import GraphViewer from '@/features/GraphViewer'
import DocumentManager from '@/features/DocumentManager'
import RetrievalTesting from '@/features/RetrievalTesting'
import ApiSite from '@/features/ApiSite'

import { Tabs, TabsContent } from '@/components/ui/Tabs'

const TAB_COMPONENTS: Record<AppTab, () => JSX.Element> = {
  documents: DocumentManager,
  'knowledge-graph': GraphViewer,
  retrieval: RetrievalTesting,
  api: ApiSite
}

function App() {
  const message = useBackendState.use.message()
  const enableHealthCheck = useSettingsStore.use.enableHealthCheck()
  const currentTab = useSettingsStore.use.currentTab()
  const [apiKeyAlertOpen, setApiKeyAlertOpen] = useState(false)
  const [initializing, setInitializing] = useState(true) // Add initializing state
  const versionCheckRef = useRef(false); // Prevent duplicate calls in Vite dev mode
  const healthCheckInitializedRef = useRef(false); // Prevent duplicate health checks in Vite dev mode

  const handleApiKeyAlertOpenChange = useCallback((open: boolean) => {
    setApiKeyAlertOpen(open)
    if (!open) {
      useBackendState.getState().clear()
    }
  }, [])

  // Track component mount status with useRef
  const isMountedRef = useRef(true);

  // Set up mount/unmount status tracking
  useEffect(() => {
    isMountedRef.current = true;

    // Handle page reload/unload
    const handleBeforeUnload = () => {
      isMountedRef.current = false;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      isMountedRef.current = false;
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Health check - can be disabled
  useEffect(() => {
    // Health check function
    const performHealthCheck = async () => {
      try {
        // Only perform health check if component is still mounted
        if (isMountedRef.current) {
          await useBackendState.getState().check();
        }
      } catch (error) {
        console.error('Health check error:', error);
      }
    };

    // Set health check function in the store
    useBackendState.getState().setHealthCheckFunction(performHealthCheck);

    if (!enableHealthCheck || apiKeyAlertOpen) {
      useBackendState.getState().clearHealthCheckTimer();
      return;
    }

    // On first mount or when enableHealthCheck becomes true and apiKeyAlertOpen is false,
    // perform an immediate health check and start the timer
    if (!healthCheckInitializedRef.current) {
      healthCheckInitializedRef.current = true;
    }

    // Start/reset the health check timer using the store
    useBackendState.getState().resetHealthCheckTimer();

    // Component unmount cleanup
    return () => {
      useBackendState.getState().clearHealthCheckTimer();
    };
  }, [enableHealthCheck, apiKeyAlertOpen]);

  // Version check - independent and executed only once
  useEffect(() => {
    const checkVersion = async () => {
      // Prevent duplicate calls in Vite dev mode
      if (versionCheckRef.current) return;
      versionCheckRef.current = true;

      // Check if version info was already obtained in login page
      const versionCheckedFromLogin = sessionStorage.getItem('VERSION_CHECKED_FROM_LOGIN') === 'true';
      if (versionCheckedFromLogin) {
        setInitializing(false); // Skip initialization if already checked
        return;
      }

      try {
        setInitializing(true); // Start initialization

        // Get version info
        const token = localStorage.getItem('LIGHTRAG-API-TOKEN');
        const status = await getAuthStatus();

        // If auth is not configured and a new token is returned, use the new token
        if (!status.auth_configured && status.access_token) {
          useAuthStore.getState().login(
            status.access_token, // Use the new token
            true, // Guest mode
            status.core_version,
            status.api_version,
            status.webui_title || null,
            status.webui_description || null
          );
        } else if (token && (status.core_version || status.api_version || status.webui_title || status.webui_description)) {
          // Otherwise use the old token (if it exists)
          const isGuestMode = status.auth_mode === 'disabled' || useAuthStore.getState().isGuestMode;
          useAuthStore.getState().login(
            token,
            isGuestMode,
            status.core_version,
            status.api_version,
            status.webui_title || null,
            status.webui_description || null
          );
        }

        // Set flag to indicate version info has been checked
        sessionStorage.setItem('VERSION_CHECKED_FROM_LOGIN', 'true');
      } catch (error) {
        console.error('Failed to get version info:', error);
      } finally {
        // Ensure initializing is set to false even if there's an error
        setInitializing(false);
      }
    };

    // Execute version check
    checkVersion();
  }, []); // Empty dependency array ensures it only runs once on mount

  const handleTabChange = useCallback(
    (tab: string) => useSettingsStore.getState().setCurrentTab(tab as AppTab),
    []
  )

  useEffect(() => {
    if (message) {
      if (message.includes(InvalidApiKeyError) || message.includes(RequireApiKeError)) {
        setApiKeyAlertOpen(true)
      }
    }
  }, [message])

  return (
    initializing ? (
      <div className="flex h-screen w-screen flex-col">
        <header className="border-border/40 bg-background/95 supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50 flex h-10 w-full border-b px-4 backdrop-blur">
          <div className="min-w-[200px] w-auto flex items-center">
            <a href={webuiPrefix} className="flex items-center gap-2">
              <ZapIcon className="size-4 text-emerald-400" aria-hidden="true" />
              <span className="font-bold md:inline-block">{SiteInfo.name}</span>
            </a>
          </div>
          <div className="flex h-10 flex-1 items-center justify-center" />
          <nav className="w-[200px] flex items-center justify-end" />
        </header>

        <div className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <div className="mx-auto mb-2 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
            <p>Initializing...</p>
          </div>
        </div>
      </div>
    ) : (
      <main className="flex h-screen w-screen overflow-hidden">
        <Tabs
          value={currentTab}
          className="!m-0 flex grow flex-col !p-0 overflow-hidden"
          onValueChange={handleTabChange}
        >
          <SiteHeader />
          <div className="relative grow">
            {APP_TABS.map((tab) => {
              const TabComponent = TAB_COMPONENTS[tab.id]
              return (
                <TabsContent key={tab.id} value={tab.id} className={tab.contentClassName}>
                  <TabComponent />
                </TabsContent>
              )
            })}
          </div>
        </Tabs>
        {enableHealthCheck && <StatusIndicator />}
        <ApiKeyAlert open={apiKeyAlertOpen} onOpenChange={handleApiKeyAlertOpenChange} />
      </main>
    )
  )
}

export default App
