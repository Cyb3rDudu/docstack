"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { useDocstoreStore } from "@/stores/docstoreStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Database, FileText, Layers } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { user, logout, checkAuth } = useAuthStore();
  const { docstores, isLoading, error, fetchDocstores, createDocstore, clearError } = useDocstoreStore();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2",
    chunking_strategy: "sentence",
    chunk_size: 200,
    chunk_overlap: 20,
  });

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

  const handleCreateDocstore = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    try {
      await createDocstore(formData);
      setIsCreateDialogOpen(false);
      setFormData({
        name: "",
        description: "",
        embedding_model: "sentence-transformers/all-MiniLM-L6-v2",
        chunking_strategy: "sentence",
        chunk_size: 200,
        chunk_overlap: 20,
      });
    } catch (error) {
      console.error("Failed to create docstore:", error);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
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
                  className="inline-flex items-center border-b-2 border-primary px-1 pt-1 text-sm font-medium text-gray-900"
                >
                  Docstores
                </button>
                <button
                  onClick={() => router.push("/dashboard/search")}
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-900"
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
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">Document Stores</h2>
            <p className="mt-2 text-gray-600">
              Manage your RAG-enabled document repositories
            </p>
          </div>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Docstore
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[525px]">
              <form onSubmit={handleCreateDocstore}>
                <DialogHeader>
                  <DialogTitle>Create Document Store</DialogTitle>
                  <DialogDescription>
                    Create a new document store with custom embedding and chunking settings
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  {error && (
                    <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
                      {error}
                    </div>
                  )}
                  <div className="grid gap-2">
                    <Label htmlFor="name">Name *</Label>
                    <Input
                      id="name"
                      placeholder="My Document Store"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      placeholder="Store for technical documentation"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="embedding_model">Embedding Model</Label>
                    <Input
                      id="embedding_model"
                      placeholder="sentence-transformers/all-MiniLM-L6-v2"
                      value={formData.embedding_model}
                      onChange={(e) => setFormData({ ...formData, embedding_model: e.target.value })}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                      <Label htmlFor="chunk_size">Chunk Size</Label>
                      <Input
                        id="chunk_size"
                        type="number"
                        value={formData.chunk_size}
                        onChange={(e) => setFormData({ ...formData, chunk_size: parseInt(e.target.value) })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="chunk_overlap">Chunk Overlap</Label>
                      <Input
                        id="chunk_overlap"
                        type="number"
                        value={formData.chunk_overlap}
                        onChange={(e) => setFormData({ ...formData, chunk_overlap: parseInt(e.target.value) })}
                      />
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button type="submit" disabled={isLoading}>
                    {isLoading ? "Creating..." : "Create Docstore"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {isLoading && docstores.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Loading docstores...</p>
          </div>
        ) : docstores.length === 0 ? (
          <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <Database className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">
              No docstores yet
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating your first document store
            </p>
            <div className="mt-6">
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Docstore
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {docstores.map((docstore) => (
              <Card
                key={docstore.id}
                className="cursor-pointer transition-shadow hover:shadow-lg"
                onClick={() => router.push(`/dashboard/docstores/${docstore.id}`)}
              >
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    {docstore.name}
                  </CardTitle>
                  {docstore.description && (
                    <CardDescription>{docstore.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1 text-gray-600">
                        <FileText className="h-4 w-4" />
                        Documents
                      </span>
                      <span className="font-medium">{docstore.document_count}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1 text-gray-600">
                        <Layers className="h-4 w-4" />
                        Chunks
                      </span>
                      <span className="font-medium">{docstore.chunk_count}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-600">Size</span>
                      <span className="font-medium">{formatBytes(docstore.total_size_bytes)}</span>
                    </div>
                    <div className="pt-2 border-t">
                      <p className="text-xs text-gray-500">
                        Model: {docstore.embedding_model}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
