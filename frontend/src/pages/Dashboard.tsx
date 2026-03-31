import { useEffect, useState } from 'react'
import { matchesApi, type Match } from '../api/client'
import MatchCard from '../components/MatchCard'
import LoadingSpinner from '../components/LoadingSpinner'
import LeagueSidebar from '../components/LeagueSidebar'

export default function Dashboard() {
  const [matches, setMatches] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [daysAhead, setDaysAhead] = useState(7)
  const [selectedLeagueId, setSelectedLeagueId] = useState<number | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    matchesApi
      .getUpcoming({
        days_ahead: daysAhead,
        ...(selectedLeagueId !== null ? { league_id: selectedLeagueId } : {}),
      })
      .then((res) => setMatches(res.data))
      .catch((err) => setError(err?.message ?? 'Failed to load matches'))
      .finally(() => setLoading(false))
  }, [daysAhead, selectedLeagueId])

  return (
    <div className="flex gap-6 items-start">
      <LeagueSidebar selectedLeagueId={selectedLeagueId} onSelect={setSelectedLeagueId} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-800">Upcoming Matches</h1>
          <div className="flex items-center gap-2">
            <label htmlFor="days" className="text-sm text-gray-600">Show next</label>
            <select
              id="days"
              value={daysAhead}
              onChange={(e) => setDaysAhead(Number(e.target.value))}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            >
              {[1, 3, 7, 14, 30].map((d) => (
                <option key={d} value={d}>{d} day{d !== 1 ? 's' : ''}</option>
              ))}
            </select>
          </div>
        </div>

        {loading && <LoadingSpinner />}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            <strong>Error:</strong> {error}
          </div>
        )}

        {!loading && !error && matches.length === 0 && (
          <div className="text-center py-16 text-gray-500">
            <div className="text-4xl mb-3">📅</div>
            <p>No upcoming matches found for the next {daysAhead} days.</p>
          </div>
        )}

        {!loading && matches.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-4">
            {matches.map((match) => (
              <MatchCard key={match.id} match={match} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

