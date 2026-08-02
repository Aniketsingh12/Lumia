import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

interface FileUploaderProps {
  botId: string
  onUpload: (file: File) => Promise<any>
  uploading: boolean
}

export default function FileUploader({ botId, onUpload, uploading }: FileUploaderProps) {
  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      for (const file of acceptedFiles) {
        try {
          await onUpload(file)
          toast.success(`${file.name} uploaded!`)
        } catch {
          toast.error(`Failed to upload ${file.name}`)
        }
      }
    },
    [onUpload]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/csv': ['.csv'],
    },
    disabled: uploading,
  })

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
        isDragActive
          ? 'border-primary-400 bg-primary-50'
          : 'border-gray-300 hover:border-gray-400 bg-gray-50'
      } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <>
          <Loader2 className="w-10 h-10 text-primary-500 mx-auto mb-3 animate-spin" />
          <p className="text-gray-600 font-medium">Uploading...</p>
        </>
      ) : isDragActive ? (
        <>
          <Upload className="w-10 h-10 text-primary-500 mx-auto mb-3" />
          <p className="text-primary-600 font-medium">Drop files here</p>
        </>
      ) : (
        <>
          <FileText className="w-10 h-10 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600 font-medium">Drag & drop files here</p>
          <p className="text-sm text-gray-400 mt-1">or click to browse (PDF, DOCX, TXT, CSV)</p>
        </>
      )}
    </div>
  )
}
