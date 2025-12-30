"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { useDocstoreStore } from "@/stores/docstoreStore";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ArrowLeft, Plus, Rocket, FileCode, Loader2, CheckCircle, XCircle } from "lucide-react";

interface Pipeline {
  id: string;
  pipeline_type: "indexing" | "query";
  pipeline_name: string;
  yaml_content: string;
  is_deployed: boolean;
  deployed_at?: string;
  created_at: string;
}

export default function PipelinesPage() {
  const router = useRouter();
  const params = useParams();
  const docstoreId = params.id as string;
  const { user, checkAuth } = useAuthStore();
  const { currentDocstore, getDocstore } = useDocstoreStore();
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isDeploying, setIsDeploying] = useState<string | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedPipelineType, setSelectedPipelineType] = useState<"indexing" | "query">("indexing");

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (!user) {
      router.push("/login");
    } else {
      loadPipelines();
    }
  }, [user, router, docstoreId]);

  const loadPipelines = async () => {
    setIsLoading(true);
    try {
      await getDocstore(docstoreId);
      const pipelineData = await api.getPipelines(docstoreId);
      setPipelines(pipelineData);
    } catch (error) {
      console.error("Failed to load pipelines:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreatePipeline = async () => {
    setIsCreating(true);
    try {
      await api.createPipeline(docstoreId, selectedPipelineType);
      setIsCreateDialogOpen(false);
      await loadPipelines();
    } catch (error) {
      console.error("Failed to create pipeline:", error);
      alert("Failed to create pipeline. Please try again.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeployPipeline = async (pipelineId: string) => {
    setIsDeploying(pipelineId);
    try {
      await api.deployPipeline(pipelineId);
      await loadPipelines();
    } catch (error) {
      console.error("Failed to deploy pipeline:", error);
      alert("Failed to deploy pipeline. Please try again.");
    } finally {
      setIsDeploying(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (!user || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400" />
          <p className="mt-2 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!currentDocstore) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Docstore not found</p>
          <Button onClick={() => router.push("/dashboard")} className="mt-4">
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const indexingPipeline = pipelines.find((p) => p.pipeline_type === "indexing");
  const queryPipeline = pipelines.find((p) => p.pipeline_type === "query");

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push(`/dashboard/docstores/${docstoreId}`)}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <h1 className="text-xl font-bold">{currentDocstore.name} - Pipelines</h1>
            </div>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">Haystack Pipelines</h2>
            <p className="mt-2 text-gray-600">
              Manage indexing and query pipelines for this docstore
            </p>
          </div>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Generate Pipeline
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Generate Pipeline</DialogTitle>
                <DialogDescription>
                  Create a new Haystack pipeline configuration
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Pipeline Type</label>
                  <div className="flex gap-4">
                    <button
                      onClick={() => setSelectedPipelineType("indexing")}
                      className={`flex-1 rounded-lg border-2 p-4 text-left transition-colors ${
                        selectedPipelineType === "indexing"
                          ? "border-primary bg-primary/5"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <div className="font-medium">Indexing Pipeline</div>
                      <div className="text-sm text-gray-500">
                        Process and embed documents
                      </div>
                    </button>
                    <button
                      onClick={() => setSelectedPipelineType("query")}
                      className={`flex-1 rounded-lg border-2 p-4 text-left transition-colors ${
                        selectedPipelineType === "query"
                          ? "border-primary bg-primary/5"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <div className="font-medium">Query Pipeline</div>
                      <div className="text-sm text-gray-500">
                        Retrieve and search documents
                      </div>
                    </button>
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button onClick={handleCreatePipeline} disabled={isCreating}>
                  {isCreating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    "Generate Pipeline"
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileCode className="h-5 w-5" />
                    Indexing Pipeline
                  </CardTitle>
                  <CardDescription>Document processing and embedding</CardDescription>
                </div>
                {indexingPipeline?.is_deployed ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-gray-400" />
                )}
              </div>
            </CardHeader>
            <CardContent>
              {indexingPipeline ? (
                <div className="space-y-4">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status</span>
                      <span className="font-medium">
                        {indexingPipeline.is_deployed ? (
                          <span className="text-green-600">Deployed</span>
                        ) : (
                          <span className="text-gray-600">Not Deployed</span>
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Created</span>
                      <span className="font-medium">
                        {formatDate(indexingPipeline.created_at)}
                      </span>
                    </div>
                    {indexingPipeline.deployed_at && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Deployed</span>
                        <span className="font-medium">
                          {formatDate(indexingPipeline.deployed_at)}
                        </span>
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={() => handleDeployPipeline(indexingPipeline.id)}
                    disabled={isDeploying === indexingPipeline.id}
                    className="w-full"
                    variant={indexingPipeline.is_deployed ? "outline" : "default"}
                  >
                    {isDeploying === indexingPipeline.id ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Deploying...
                      </>
                    ) : (
                      <>
                        <Rocket className="mr-2 h-4 w-4" />
                        {indexingPipeline.is_deployed ? "Redeploy" : "Deploy"}
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <FileCode className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-sm text-gray-600">
                    No indexing pipeline yet
                  </p>
                  <Button
                    onClick={() => {
                      setSelectedPipelineType("indexing");
                      setIsCreateDialogOpen(true);
                    }}
                    className="mt-4"
                    variant="outline"
                  >
                    Generate Pipeline
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileCode className="h-5 w-5" />
                    Query Pipeline
                  </CardTitle>
                  <CardDescription>Document retrieval and search</CardDescription>
                </div>
                {queryPipeline?.is_deployed ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-gray-400" />
                )}
              </div>
            </CardHeader>
            <CardContent>
              {queryPipeline ? (
                <div className="space-y-4">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status</span>
                      <span className="font-medium">
                        {queryPipeline.is_deployed ? (
                          <span className="text-green-600">Deployed</span>
                        ) : (
                          <span className="text-gray-600">Not Deployed</span>
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Created</span>
                      <span className="font-medium">
                        {formatDate(queryPipeline.created_at)}
                      </span>
                    </div>
                    {queryPipeline.deployed_at && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Deployed</span>
                        <span className="font-medium">
                          {formatDate(queryPipeline.deployed_at)}
                        </span>
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={() => handleDeployPipeline(queryPipeline.id)}
                    disabled={isDeploying === queryPipeline.id}
                    className="w-full"
                    variant={queryPipeline.is_deployed ? "outline" : "default"}
                  >
                    {isDeploying === queryPipeline.id ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Deploying...
                      </>
                    ) : (
                      <>
                        <Rocket className="mr-2 h-4 w-4" />
                        {queryPipeline.is_deployed ? "Redeploy" : "Deploy"}
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <FileCode className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-sm text-gray-600">
                    No query pipeline yet
                  </p>
                  <Button
                    onClick={() => {
                      setSelectedPipelineType("query");
                      setIsCreateDialogOpen(true);
                    }}
                    className="mt-4"
                    variant="outline"
                  >
                    Generate Pipeline
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
