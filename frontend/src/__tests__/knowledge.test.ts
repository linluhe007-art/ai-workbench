import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import apiClient from "../api/client";
import { searchKnowledge, listDocuments, getDocument, deleteDocument, getKnowledgeStats, DOC_TYPES } from "../api/knowledge";
import { useKnowledgeDocs } from "../hooks/useKnowledge";

vi.mock("../api/client");
var mockGet = vi.mocked(apiClient.get);
var mockPost = vi.mocked(apiClient.post);
var mockDelete = vi.mocked(apiClient.delete);
beforeEach(function() { vi.clearAllMocks(); });

function wrapper(obj) { var qc = new QueryClient({ defaultOptions: { queries: { retry: false } } }); return React.createElement(QueryClientProvider, { client: qc }, obj.children); }

describe("Knowledge API", function() {
  it("searchKnowledge calls POST", async function() {
    mockPost.mockResolvedValue({ data: { success: true } });
    var res = await searchKnowledge("test");
    expect(res.success).toBe(true);
    expect(mockPost).toHaveBeenCalled();
  });

  it("listDocuments calls GET", async function() {
    mockGet.mockResolvedValue({ data: { success: true, documents: [] } });
    var res = await listDocuments();
    expect(res.success).toBe(true);
    expect(mockGet).toHaveBeenCalled();
  });

  it("getDocument calls GET with id", async function() {
    mockGet.mockResolvedValue({ data: { success: true } });
    var res = await getDocument("d1");
    expect(res.success).toBe(true);
    expect(mockGet).toHaveBeenCalled();
  });

  it("deleteDocument calls DELETE", async function() {
    mockDelete.mockResolvedValue({ data: { success: true } });
    var res = await deleteDocument("d1");
    expect(res.success).toBe(true);
    expect(mockDelete).toHaveBeenCalled();
  });

  it("getKnowledgeStats calls GET", async function() {
    mockGet.mockResolvedValue({ data: { success: true, data: { total_documents: 5 } } });
    var res = await getKnowledgeStats();
    expect(res.success).toBe(true);
  });

  it("DOC_TYPES has 5 types", function() {
    expect(DOC_TYPES).toHaveLength(5);
    expect(DOC_TYPES).toContain("pdf");
    expect(DOC_TYPES).toContain("markdown");
  });
});

describe("useKnowledgeDocs hook", function() {
  it("returns data", async function() {
    mockGet.mockResolvedValue({ data: { success: true, documents: [{ id: "1", title: "Test", doc_type: "txt", chunk_count: 2, tags: ["ai"], summary: "s", filename: "t.txt", source_url: "", metadata: {}, created_at: "2026-01-01" }] } });
    var result = renderHook(function() { return useKnowledgeDocs(); }, { wrapper: wrapper });
    await waitFor(function() { return expect(result.result.current.isSuccess).toBe(true); });
    expect(result.result.current.data.documents[0].title).toBe("Test");
  });
});

describe("Knowledge error handling", function() {
  it("handles search error", async function() {
    mockPost.mockRejectedValue(new Error("Fail"));
    await expect(searchKnowledge("test")).rejects.toThrow("Fail");
  });

  it("handles empty results", async function() {
    mockPost.mockResolvedValue({ data: { success: true, results: [] } });
    var res = await searchKnowledge("nothing");
    expect(res.results).toEqual([]);
  });
});
