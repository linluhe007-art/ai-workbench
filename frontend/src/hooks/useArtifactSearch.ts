import { useQuery } from "@tanstack/react-query"
import { searchArtifacts, type ArtifactSearchParams } from "../api/artifactSearch"

export function useArtifactSearch(params: ArtifactSearchParams, enabled = true) {
  return useQuery({
    queryKey: ["artifact-search", params],
    queryFn: () => searchArtifacts(params),
    enabled,
  })
}