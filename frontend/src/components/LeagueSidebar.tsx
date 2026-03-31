import { useEffect, useState } from 'react'
import { leaguesApi, type League } from '../api/client'

interface Props {
  selectedLeagueId: number | null
  onSelect: (id: number | null) => void
}

export default function LeagueSidebar({ selectedLeagueId, onSelect }: Props) {
  const [leagues, setLeagues] = useState<League[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    leaguesApi
      .list()
      .then((res) => setLeagues(res.data))
      .catch(() => setLeagues([]))
      .finally(() => setLoading(false))
  }, [])

  // Prioritní ligy nahoře — zbytek seřazen abecedně
  const PRIORITY = ['lck', 'lpl', 'lec', 'lcs', 'worlds', 'msi', 'pcs', 'vcs', 'cblol', 'ljl']

  const sorted = [...leagues].sort((a, b) => {
    const ai = PRIORITY.indexOf((a.slug ?? '').toLowerCase())
    const bi = PRIORITY.indexOf((b.slug ?? '').toLowerCase())
    if (ai !== -1 && bi !== -1) return ai - bi
    if (ai !== -1) return -1
    if (bi !== -1) return 1
    return a.name.localeCompare(b.name)
  })

  return (
    <aside className="w-56 flex-shrink-0">
      <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Leagues</h2>
        </div>
        <nav className="py-1">
          <button
            onClick={() => onSelect(null)}
            className={`w-full text-left px-4 py-2 text-sm transition-colors ${
              selectedLeagueId === null
                ? 'bg-yellow-50 text-yellow-700 font-semibold border-l-2 border-yellow-500'
                : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            All Leagues
          </button>

          {loading && (
            <div className="px-4 py-3 text-sm text-gray-400">Loading…</div>
          )}

          {sorted.map((league) => (
            <button
              key={league.id}
              onClick={() => onSelect(league.id)}
              className={`w-full text-left px-4 py-2 text-sm transition-colors flex items-center gap-2 ${
                selectedLeagueId === league.id
                  ? 'bg-yellow-50 text-yellow-700 font-semibold border-l-2 border-yellow-500'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              {league.image_url && (
                <img
                  src={league.image_url}
                  alt={league.name}
                  className="w-4 h-4 object-contain flex-shrink-0"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
              )}
              <span className="truncate">{league.name}</span>
            </button>
          ))}
        </nav>
      </div>
    </aside>
  )
}
