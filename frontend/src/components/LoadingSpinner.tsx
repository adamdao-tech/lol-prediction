export default function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="animate-spin rounded-full h-10 w-10 border-4 border-yellow-400 border-t-transparent" />
      <span className="ml-3 text-gray-500">Loading...</span>
    </div>
  )
}
