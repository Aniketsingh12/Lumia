import { useState } from 'react'
import { FileText, Trash2, Link as LinkIcon, Loader2 } from 'lucide-react'
import { useKnowledge } from '../../hooks/useKnowledge'
import { formatRelative } from '../../lib/utils'
import FileUploader from './FileUploader'
import Badge from '../common/Badge'
import EmptyState from '../common/EmptyState'
import toast from 'react-hot-toast'

export default function KnowledgeTab({ botId }: { botId: string }) {
  const { docs, loading, uploading, uploadFile, uploadUrl, deleteDoc } = useKnowledge(botId)
  const [urlInput, setUrlInput] = useState('')
  const [showUrlForm, setShowUrlForm] = useState(false)

  const handleUrlSubmit = async () => {
    if (!urlInput.trim()) return
    try {
      await uploadUrl(urlInput)
      setUrlInput('')
      setShowUrlForm(false)
      toast.success('URL ingestion started')
    } catch {
      toast.error('Failed to ingest URL')
    }
  }

  const totalChunks = docs.reduce((sum, d) => sum + d.chunk_count, 0)

  return (
    <div>
      {/* Stats */}
      <div className="flex gap-4 mb-6">
        <div className="card px-4 py-3">
          <p className="text-sm text-gray-500">Documents</p>
          <p className="text-2xl font-bold text-gray-900">{docs.length}</p>
        </div>
        <div className="card px-4 py-3">
          <p className="text-sm text-gray-500">Total Chunks</p>
          <p className="text-2xl font-bold text-gray-900">{totalChunks}</p>
        </div>
        <div className="card px-4 py-3">
          <p className="text-sm text-gray-500">Status</p>
          <p className="text-2xl font-bold text-green-400">
            {docs.every((d) => d.status === 'ready') ? 'Ready' : 'Processing'}
          </p>
        </div>
      </div>

      {/* Upload */}
      <FileUploader botId={botId} onUpload={uploadFile} uploading={uploading} />

      {/* URL Ingest */}
      <div className="mt-4">
        {showUrlForm ? (
          <div className="flex gap-2">
            <input
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="input flex-1"
              placeholder="https://example.com/page-to-ingest"
              onKeyDown={(e) => e.key === 'Enter' && handleUrlSubmit()}
            />
            <button onClick={handleUrlSubmit} className="btn-primary">Add URL</button>
            <button onClick={() => setShowUrlForm(false)} className="btn-secondary">Cancel</button>
          </div>
        ) : (
          <button onClick={() => setShowUrlForm(true)} className="btn-secondary flex items-center gap-2">
            <LinkIcon className="w-4 h-4" />
            Add URL
          </button>
        )}
      </div>

      {/* Doc List */}
      <div className="mt-6">
        {docs.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No documents yet"
            description="Upload PDFs, DOCX, TXT, or CSV files to build your knowledge base"
          />
        ) : (
          <div className="space-y-2">
            {docs.map((doc) => (
              <div key={doc.id} className="card flex items-center gap-4 p-4">
                <FileText className="w-8 h-8 text-gray-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{doc.filename}</p>
                  <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                    <span className="uppercase">{doc.file_type}</span>
                    <span>{doc.chunk_count} chunks</span>
                    {doc.uploaded_at && <span>{formatRelative(doc.uploaded_at)}</span>}
                  </div>
                </div>
                <Badge status={doc.status}>{doc.status}</Badge>
                <button
                  onClick={() => deleteDoc(doc.id)}
                  className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
