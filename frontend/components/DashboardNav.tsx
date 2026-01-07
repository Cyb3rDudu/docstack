"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";

interface DashboardNavProps {
  title?: string;
  backPath?: string;
  backLabel?: string;
  actions?: React.ReactNode;
}

export function DashboardNav({ title, backPath, backLabel, actions }: DashboardNavProps) {
  const router = useRouter();
  const { user, logout } = useAuthStore();

  return (
    <nav className="border-b bg-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 justify-between">
          <div className="flex">
            <div className="flex flex-shrink-0 items-center">
              <h1 className="text-xl font-bold cursor-pointer" onClick={() => router.push("/dashboard")}>
                DocStack
              </h1>
            </div>
            <div className="ml-6 flex space-x-8">
              <button
                onClick={() => router.push("/dashboard")}
                className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 border-b-2 border-transparent hover:border-gray-300"
              >
                Docstores
              </button>
              <button
                onClick={() => router.push("/dashboard/search")}
                className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-900 border-b-2 border-transparent hover:border-gray-300"
              >
                Search
              </button>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {actions}
            <span className="text-sm text-gray-700">
              {user?.full_name || user?.email}
            </span>
            <button
              onClick={() => logout()}
              className="text-sm text-gray-700 hover:text-gray-900"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
      {(title || backPath) && (
        <div className="border-t bg-gray-50">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex h-12 items-center justify-between">
              <div className="flex items-center space-x-4">
                {backPath && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => router.push(backPath)}
                  >
                    ← {backLabel || "Back"}
                  </Button>
                )}
                {title && <h2 className="text-lg font-semibold">{title}</h2>}
              </div>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
