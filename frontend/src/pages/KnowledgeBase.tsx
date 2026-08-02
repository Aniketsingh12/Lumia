import { useState, useEffect } from 'react'
import { useBots } from '../hooks/useBots'
import { useKnowledge } from '../hooks/useKnowledge'
import FileUploader from '../components/bot-builder/FileUploader'
import { FileText, Trash2, RefreshCw } from 'lucide-react'
import { getStatusColor, formatRelative } from '../lib/utils'
import Badge from '../components/common/Badge'
import EmptyState from '../components/common/EmptyState'
import toast from 'react-hot-toast'

export default function KnowledgeBase() {
  const { bots } = useBots()
  const [selectedBot, setSelectedBot] = useState('')

  useEffect(() => {
    if (bots.length > 0 && !selectedBot) {
      setSelectedBot(bots[0].id)
    }
  }, [bots, selectedBot])
  const { docs, loading, uploading, uploadFile, deleteDoc, reindex } = useKnowledge(selectedBot)

  const handleDelete = async (docId: string) => {
    try {
      await deleteDoc(docId)
      toast.success('Document deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const handleReindex = async () => {
    try {
      await reindex()
      toast.success('Reindexing started')
    } catch {
      toast.error('Failed to reindex')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-gray-500 mt-1">Manage documents for your bots</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedBot}
            onChange={(e) => setSelectedBot(e.target.value)}
            className="input w-48"
          >
            <option value="">Select bot</option>
            {bots.map((bot) => (
              <option key={bot.id} value={bot.id}>
                {bot.name}
              </option>
            ))}
          </select>
          <button onClick={handleReindex} className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Reindex
          </button>
        </div>
      </div>

      {selectedBot && (
        <div className="mb-6">
          <FileUploader botId={selectedBot} onUpload={uploadFile} uploading={uploading} />
        </div>
      )}

      {docs.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents uploaded"
          description="Upload PDFs, DOCX, TXT, or CSV files to build your bot's knowledge base"
        />
      ) : (
        <div className="card divide-y divide-gray-100">
          {docs.map((doc) => (
            <div key={doc.id} className="flex items-center gap-4 p-4">
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
                onClick={() => handleDelete(doc.id)}
                className="p-2 text-gray-400 hover:text-red-500 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
