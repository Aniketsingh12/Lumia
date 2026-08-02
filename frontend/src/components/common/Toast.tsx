// Using react-hot-toast globally via App.tsx <Toaster />
// This file provides custom toast styles if needed

import toast from 'react-hot-toast'

export function successToast(message: string) {
  toast.success(message, {
    style: { borderRadius: '8px', background: '#10b981', color: '#fff' },
  })
}

export function errorToast(message: string) {
  toast.error(message, {
    style: { borderRadius: '8px', background: '#ef4444', color: '#fff' },
  })
}
