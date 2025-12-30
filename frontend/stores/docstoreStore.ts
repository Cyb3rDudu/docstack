import { create } from "zustand";
import { api } from "@/lib/api";

export interface Docstore {
  id: string;
  name: string;
  slug: string;
  description?: string;
  index_name: string;
  embedding_model: string;
  chunking_strategy: string;
  chunk_size: number;
  chunk_overlap: number;
  document_count: number;
  chunk_count: number;
  total_size_bytes: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateDocstoreData {
  name: string;
  description?: string;
  embedding_model?: string;
  chunking_strategy?: string;
  chunk_size?: number;
  chunk_overlap?: number;
}

interface DocstoreState {
  docstores: Docstore[];
  currentDocstore: Docstore | null;
  isLoading: boolean;
  error: string | null;

  fetchDocstores: () => Promise<void>;
  createDocstore: (data: CreateDocstoreData) => Promise<Docstore>;
  getDocstore: (id: string) => Promise<void>;
  updateDocstore: (id: string, data: Partial<CreateDocstoreData>) => Promise<void>;
  deleteDocstore: (id: string) => Promise<void>;
  clearError: () => void;
}

export const useDocstoreStore = create<DocstoreState>((set, get) => ({
  docstores: [],
  currentDocstore: null,
  isLoading: false,
  error: null,

  fetchDocstores: async () => {
    set({ isLoading: true, error: null });
    try {
      const docstores = await api.getDocstores();
      set({ docstores, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch docstores",
        isLoading: false,
      });
    }
  },

  createDocstore: async (data: CreateDocstoreData) => {
    set({ isLoading: true, error: null });
    try {
      const docstore = await api.createDocstore(data);
      set((state) => ({
        docstores: [...state.docstores, docstore],
        isLoading: false,
      }));
      return docstore;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to create docstore";
      set({ error: errorMessage, isLoading: false });
      throw error;
    }
  },

  getDocstore: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const docstore = await api.getDocstore(id);
      set({ currentDocstore: docstore, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch docstore",
        isLoading: false,
      });
    }
  },

  updateDocstore: async (id: string, data: Partial<CreateDocstoreData>) => {
    set({ isLoading: true, error: null });
    try {
      const docstore = await api.updateDocstore(id, data);
      set((state) => ({
        docstores: state.docstores.map((d) => (d.id === id ? docstore : d)),
        currentDocstore: state.currentDocstore?.id === id ? docstore : state.currentDocstore,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to update docstore",
        isLoading: false,
      });
      throw error;
    }
  },

  deleteDocstore: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.deleteDocstore(id);
      set((state) => ({
        docstores: state.docstores.filter((d) => d.id !== id),
        currentDocstore: state.currentDocstore?.id === id ? null : state.currentDocstore,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete docstore",
        isLoading: false,
      });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));
