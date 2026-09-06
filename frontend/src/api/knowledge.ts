import apiClient from "./client"

export interface KnowledgeDocument {
  id: string
  title: string
  doc_type: string
  filename: string
  source_url: string
  tags: string[]
  summary: string
  metadata: Record<string, unknown>
  chunk_count: number
  created_at: string
}

export interface KnowledgeChunk {
  id: string
  document_id: string
  chunk_index: number
  content: string
  tags: string[]
  created_at: string
}

export interface SearchResult {
  chunk_id: string
  document_id: string
  content: string
  score: number
  title: string
  doc_type: string
}

export interface KnowledgeStats {
  total_documents: number
  total_chunks: number
  by_type: Record<string, number>
}

export const uploadDocument = (file: File) => {
  const form = new FormData()
  form.append("file", file)
  return apiClient.post("/knowledge/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data)
}

export const indexWebContent = (content: string, filename = "", sourceUrl = "") =>
  apiClient.post("/knowledge/web", { content, filename, source_url: sourceUrl }).then((r) => r.data)

export const searchKnowledge = (query: string, limit = 20, docType?: string) =>
  apiClient.post("/knowledge/search", { query, limit, doc_type: docType }).then((r) => r.data)

export const listDocuments = (docType?: string, limit = 50) =>
  apiClient.get("/knowledge/documents", { params: { doc_type: docType, limit } }).then((r) => r.data)

export const getDocument = (docId: string) =>
  apiClient.get("/knowledge/documents/" + docId).then((r) => r.data)

export const deleteDocument = (docId: string) =>
  apiClient.delete("/knowledge/documents/" + docId).then((r) => r.data)

export const getKnowledgeStats = () =>
  apiClient.get("/knowledge/stats").then((r) => r.data)

export const getKnowledgeContext = (q: string, limit = 5) =>
  apiClient.get("/knowledge/context", { params: { q, limit } }).then((r) => r.data)

export const DOC_TYPES = ["pdf", "markdown", "txt", "code", "web"] as const
export const DOC_TYPE_LABELS: Record<string, string> = {
  pdf: "PDF", markdown: "Markdown", txt: "Text", code: "Code", web: "Web",
}
