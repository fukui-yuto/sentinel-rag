import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Upload, Trash2, FileText, X, ChevronRight, AlertTriangle, Loader2 } from "lucide-react";

interface Document {
  id: string;
  filename: string;
  status: string;
  sensitivity: string;
  file_size_bytes: number;
  chunk_count: number;
  created_at: string;
}

interface DocumentList {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
}

interface Chunk {
  id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  created_at: string;
}

export function DocumentsPage() {
  const [page, setPage] = useState(1);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["documents", page],
    queryFn: () => api.get<DocumentList>(`/documents?page=${page}`),
    refetchInterval: (query) => {
      const items = query.state.data?.items;
      return items?.some((d: Document) => d.status === "pending" || d.status === "processing") ? 3000 : false;
    },
  });

  const { data: chunks, isLoading: chunksLoading } = useQuery({
    queryKey: ["document-chunks", selectedDoc?.id],
    queryFn: () => api.get<Chunk[]>(`/documents/${selectedDoc!.id}/chunks`),
    enabled: !!selectedDoc,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.upload<Document>("/documents", file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/documents/${id}`),
    onSuccess: (_data, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (selectedDoc?.id === deletedId) setSelectedDoc(null);
      setDeleteTarget(null);
      setDeleteError(null);
    },
    onError: (err) => {
      setDeleteError(err instanceof Error ? err.message : "Delete failed");
    },
  });

  const handleUpload = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files) {
        Array.from(files).forEach((file) => uploadMutation.mutate(file));
      }
    };
    input.click();
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const statusColor: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    processing: "bg-blue-100 text-blue-800",
    indexed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    deleted: "bg-gray-100 text-gray-800",
  };

  const sensitivityColor: Record<string, string> = {
    public: "bg-green-100 text-green-800",
    internal: "bg-blue-100 text-blue-800",
    confidential: "bg-orange-100 text-orange-800",
    restricted: "bg-red-100 text-red-800",
  };

  return (
    <div className="flex gap-6 h-[calc(100vh-6rem)]">
      {/* Document List */}
      <div className={`space-y-4 transition-all ${selectedDoc ? "w-1/2" : "w-full"}`}>
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">Documents</h2>
          <button
            onClick={handleUpload}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Upload size={16} />
            Upload
          </button>
        </div>

        {isLoading ? (
          <p className="text-gray-400">Loading...</p>
        ) : (
          <>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                    {!selectedDoc && (
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Sensitivity</th>
                    )}
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Size</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Chunks</th>
                    {!selectedDoc && (
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
                    )}
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((doc) => (
                    <tr
                      key={doc.id}
                      onClick={() => setSelectedDoc(doc)}
                      className={`border-b border-gray-100 hover:bg-blue-50 cursor-pointer transition-colors ${
                        selectedDoc?.id === doc.id ? "bg-blue-50 border-l-2 border-l-blue-500" : ""
                      }`}
                    >
                      <td className="px-4 py-3 flex items-center gap-2">
                        <FileText size={16} className="text-gray-400 shrink-0" />
                        <span className="truncate max-w-xs">{doc.filename}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor[doc.status] || ""}`}>
                          {doc.status}
                        </span>
                      </td>
                      {!selectedDoc && (
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${sensitivityColor[doc.sensitivity] || ""}`}>
                            {doc.sensitivity}
                          </span>
                        </td>
                      )}
                      <td className="px-4 py-3 text-gray-500">{formatBytes(doc.file_size_bytes)}</td>
                      <td className="px-4 py-3 text-gray-500">{doc.chunk_count}</td>
                      {!selectedDoc && (
                        <td className="px-4 py-3 text-gray-500">
                          {new Date(doc.created_at).toLocaleDateString("ja-JP")}
                        </td>
                      )}
                      <td className="px-4 py-3 flex items-center gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteTarget(doc);
                          }}
                          className="text-gray-400 hover:text-red-500"
                        >
                          <Trash2 size={16} />
                        </button>
                        <ChevronRight size={14} className="text-gray-300" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {data && data.total > data.page_size && (
              <div className="flex justify-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  Prev
                </button>
                <span className="px-3 py-1 text-gray-600">
                  {page} / {Math.ceil(data.total / data.page_size)}
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * data.page_size >= data.total}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Document Detail Panel */}
      {selectedDoc && (
        <div className="w-1/2 bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between shrink-0">
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-gray-900 truncate">{selectedDoc.filename}</h3>
              <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                <span className={`px-2 py-0.5 rounded-full font-medium ${statusColor[selectedDoc.status] || ""}`}>
                  {selectedDoc.status}
                </span>
                <span className={`px-2 py-0.5 rounded-full font-medium ${sensitivityColor[selectedDoc.sensitivity] || ""}`}>
                  {selectedDoc.sensitivity}
                </span>
                <span>{formatBytes(selectedDoc.file_size_bytes)}</span>
                <span>{selectedDoc.chunk_count} chunks</span>
              </div>
            </div>
            <button
              onClick={() => setSelectedDoc(null)}
              className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            >
              <X size={20} />
            </button>
          </div>

          {/* Chunks Content */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {chunksLoading ? (
              <p className="text-gray-400 text-sm">Loading chunks...</p>
            ) : chunks && chunks.length > 0 ? (
              chunks.map((chunk) => (
                <div key={chunk.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                      Chunk {chunk.chunk_index + 1}
                    </span>
                    <span className="text-xs text-gray-400">{chunk.token_count} tokens</span>
                  </div>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {chunk.content}
                  </p>
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-gray-400">
                <FileText size={40} className="mx-auto mb-3 opacity-50" />
                <p className="text-sm">
                  {selectedDoc.status === "indexed"
                    ? "No chunks found."
                    : selectedDoc.status === "pending"
                    ? "Document is waiting to be processed."
                    : selectedDoc.status === "processing"
                    ? "Document is being processed..."
                    : selectedDoc.status === "failed"
                    ? "Document processing failed."
                    : "No content available."}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-sm mx-4 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-full">
                <AlertTriangle size={20} className="text-red-600" />
              </div>
              <h3 className="text-lg font-semibold">Delete Document</h3>
            </div>
            <p className="text-sm text-gray-600">
              Are you sure you want to delete <strong>{deleteTarget.filename}</strong>? This action cannot be undone.
            </p>
            {deleteError && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{deleteError}</p>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Progress */}
      {uploadMutation.isPending && (
        <div className="fixed bottom-6 right-6 bg-white border border-gray-200 rounded-xl shadow-lg px-4 py-3 flex items-center gap-3">
          <Loader2 size={18} className="text-blue-600 animate-spin" />
          <span className="text-sm text-gray-700">Uploading...</span>
        </div>
      )}
    </div>
  );
}
