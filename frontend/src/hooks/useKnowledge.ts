import { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

interface Doc {
  id: string
  bot_id: string
  filename: string
  file_type: string
  status: string
  chunk_count: number
  uploaded_at?: string
}

export function useKnowledge(botId: string) {
  const [docs, setDocs] = useState<Doc[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  const fetchDocs = useCallback(async () => {
    if (!botId) return
    setLoading(true)
    try {
      const { data } = await api.get(`/bots/${botId}/docs`)
      setDocs(data)
    } catch (e) {
      console.error('Failed to fetch docs', e)
    }
    setLoading(false)
  }, [botId])

  useEffect(() => {
    fetchDocs()
  }, [fetchDocs])

  const uploadFile = async (file: File) => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post(`/bots/${botId}/docs/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setDocs((prev) => [...prev, data])
      return data
    } finally {
      setUploading(false)
    }
  }

  const uploadUrl = async (url: string, name?: string) => {
    const { data } = await api.post(`/bots/${botId}/docs/url`, { url, name })
    setDocs((prev) => [...prev, data])
    return data
  }

  const deleteDoc = async (docId: string) => {
    await api.delete(`/bots/${botId}/docs/${docId}`)
    setDocs((prev) => prev.filter((d) => d.id !== docId))
  }

  const reindex = async () => {
    await api.post(`/bots/${botId}/docs/reindex`)
    await fetchDocs()
  }

  return { docs, loading, uploading, uploadFile, uploadUrl, deleteDoc, reindex, refetch: fetchDocs }
}
