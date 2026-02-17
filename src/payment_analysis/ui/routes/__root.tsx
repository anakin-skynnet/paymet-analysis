import * as React from 'react'
import { Outlet, createRootRoute } from '@tanstack/react-router'
import { Toaster } from 'sonner'

export const Route = createRootRoute({
  component: RootComponent,
})

function RootComponent() {
  return (
    <React.Fragment>
      <React.Suspense
        fallback={
          <div className="flex h-screen w-full items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        }
      >
        <Outlet />
      </React.Suspense>
      <Toaster position="bottom-right" richColors closeButton />
    </React.Fragment>
  )
}
