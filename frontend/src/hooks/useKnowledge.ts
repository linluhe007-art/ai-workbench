import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { searchKnowledge, listDocuments, getDocument, deleteDocument, getKnowledgeStats, uploadDocument, indexWebContent } from "../api/knowledge"

export const useKnowledgeSearch = (query: string, docType?: string) =>
  useQuery({ queryKey: ["knowledge", "search", query, docType], queryFn: () => searchKnowledge(query, 20, docType), enabled: query.length > 0 })

export const useKnowledgeDocs = (docType?: string) =>
  useQuery({ queryKey: ["knowledge", "docs", docType], queryFn: () => listDocuments(docType) })

export const useKnowledgeDoc = (docId: string) =>
  useQuery({ queryKey: ["knowledge", "doc", docId], queryFn: () => getDocument(docId), enabled: !!docId })

export const useKnowledgeStats = () =>
  useQuery({ queryKey: ["knowledge", "stats"], queryFn: getKnowledgeStats, refetchInterval: 15000 })

export const useUploadDocument = () => {
  const qc = useQueryClient()
  return useMutation({ mutationFn: (file: File) => uploadDocument(file), onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge"] }) })
}

export const useIndexWebContent = () => {
  const qc = useQueryClient()
  return useMutation({ mutationFn: ({ content, filename, sourceUrl }: { content: string; filename?: string; sourceUrl?: string }) => indexWebContent(content, filename, sourceUrl), onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge"] }) })
}

export const useDeleteDocument = () => {
  const qc = useQueryClient()
  return useMutation({ mutationFn: (docId: string) => deleteDocument(docId), onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge"] }) })
}
