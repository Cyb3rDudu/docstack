"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { useDocstoreStore } from "@/stores/docstoreStore";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Search, Loader2, FileText, Database } from "lucide-react";

interface QueryResult {
  document_id: string;
  filename: string;
  content: string;
  score: number;
  metadata?: Record<string, any>;
}

export default function SearchPage() {
  const router = useRouter();
  const { user, logout, checkAuth } = useAuthStore();
  const { docstores, fetchDocstores } = useDocstoreStore();
  const [query, setQuery] = useState("");
  const [selectedDocstores, setSelectedDocstores] = useState<string[]>([]);
  const [results, setResults] = useState<QueryResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (!user) {
      router.push("/login");
    } else {
      fetchDocstores();
    }
  }, [user, router, fetchDocstores]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setHasSearched(true);

    try {
      let searchResults;
      if (selectedDocstores.length === 0) {
        const allDocstoreIds = docstores.map((d) => d.id);
        if (allDocstoreIds.length === 0) {
          setResults([]);
          setIsSearching(false);
          return;
        }
        searchResults = await api.queryMultiDocstores(allDocstoreIds, query, 10);
      } else if (selectedDocstores.length === 1) {
        searchResults = await api.queryDocstore(selectedDocstores[0], query, 10);
      } else {
        searchResults = await api.queryMultiDocstores(selectedDocstores, query, 10);
      }
      setResults(searchResults.results || searchResults);
    } catch (error) {
      console.error("Search failed:", error);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const toggleDocstore = (docstoreId: string) => {
    setSelectedDocstores((prev) =>
      prev.includes(docstoreId)
        ? prev.filter((id) => id !== docstoreId)
        : [...prev, docstoreId]
    );
  };

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Loading...</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 justify-between">
            <div className="flex">
              <div className="flex flex-shrink-0 items-center">
                <h1 className="text-xl font-bold">DocStack</h1>
              </div>
              <div className="ml-6 flex space-x-8">
                <button
                  onClick={() => router.push("/dashboard")}
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-900"
                >
                  Docstores
                </button>
                <button
                  onClick={() => router.push("/dashboard/search")}
                  className="inline-flex items-center border-b-2 border-primary px-1 pt-1 text-sm font-medium text-gray-900"
                >
                  Search
                </button>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                {user.full_name || user.email}
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
      </nav>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900">Search Documents</h2>
          <p className="mt-2 text-gray-600">
            Query your document stores using natural language
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-4">
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-base">Document Stores</CardTitle>
              <CardDescription className="text-xs">
                {selectedDocstores.length === 0
                  ? "Searching all docstores"
                  : `${selectedDocstores.length} selected`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {docstores.length === 0 ? (
                <p className="text-sm text-gray-500">
                  No docstores available. Create one first.
                </p>
              ) : (
                <div className="space-y-2">
                  {docstores.map((docstore) => (
                    <label
                      key={docstore.id}
                      className="flex items-center space-x-2 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedDocstores.includes(docstore.id)}
                        onChange={() => toggleDocstore(docstore.id)}
                        className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      />
                      <span className="text-sm">{docstore.name}</span>
                    </label>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="lg:col-span-3 space-y-6">
            <Card>
              <CardContent className="pt-6">
                <form onSubmit={handleSearch} className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      type="text"
                      placeholder="Ask a question about your documents..."
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  <Button type="submit" disabled={isSearching || !query.trim()}>
                    {isSearching ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Searching...
                      </>
                    ) : (
                      "Search"
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {isSearching ? (
              <div className="text-center py-12">
                <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400" />
                <p className="mt-4 text-gray-600">Searching documents...</p>
              </div>
            ) : hasSearched ? (
              results.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <FileText className="mx-auto h-12 w-12 text-gray-400" />
                    <p className="mt-4 text-gray-600">No results found</p>
                    <p className="mt-1 text-sm text-gray-500">
                      Try a different query or check if your pipelines are deployed
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold">
                      Results ({results.length})
                    </h3>
                  </div>
                  {results.map((result, index) => (
                    <Card key={index}>
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <CardTitle className="text-base flex items-center gap-2">
                              <FileText className="h-4 w-4" />
                              {result.filename || "Document"}
                            </CardTitle>
                            {result.metadata?.docstore_name && (
                              <CardDescription className="flex items-center gap-1 mt-1">
                                <Database className="h-3 w-3" />
                                {result.metadata.docstore_name}
                              </CardDescription>
                            )}
                          </div>
                          <div className="text-sm font-medium text-primary">
                            Score: {(result.score * 100).toFixed(1)}%
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {result.content}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <Search className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-gray-600">
                    Enter a query to search your documents
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    Results will appear here
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
