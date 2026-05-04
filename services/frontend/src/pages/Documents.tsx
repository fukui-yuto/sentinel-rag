import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Upload, Trash2, FileText } from "lucide-react";

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

export function DocumentsPage() {
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["documents", page],
    queryFn: () => api.get<DocumentList>(`/documents?page=${page}`),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.upload<Document>("/documents", file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/documents/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
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
    <div className="space-y-6">
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
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Sensitivity</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Size</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Chunks</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((doc) => (
                  <tr key={doc.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 flex items-center gap-2">
                      <FileText size={16} className="text-gray-400" />
                      <span className="truncate max-w-xs">{doc.filename}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor[doc.status] || ""}`}>
                        {doc.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${sensitivityColor[doc.sensitivity] || ""}`}>
                        {doc.sensitivity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{formatBytes(doc.file_size_bytes)}</td>
                    <td className="px-4 py-3 text-gray-500">{doc.chunk_count}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(doc.created_at).toLocaleDateString("ja-JP")}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => deleteMutation.mutate(doc.id)}
                        className="text-gray-400 hover:text-red-500"
                      >
                        <Trash2 size={16} />
                      </button>
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
  );
}
