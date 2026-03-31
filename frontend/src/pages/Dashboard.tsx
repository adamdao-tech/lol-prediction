import { useEffect, useRef, useState } from 'react'
import { matchesApi, type Match } from '../api/client'
import MatchCard from '../components/MatchCard'
import LoadingSpinner from '../components/LoadingSpinner'
import LeagueSidebar from '../components/LeagueSidebar'

type Tab = 'live' | 'upcoming'

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('live')
  const [liveMatches, setLiveMatches] = useState<Match[]>([])
  const [upcomingMatches, setUpcomingMatches] = useState<Match[]>([])
  const [liveLoading, setLiveLoading] = useState(true)
  const [upcomingLoading, setUpcomingLoading] = useState(true)
  const [liveError, setLiveError] = useState<string | null>(null)
  const [upcomingError, setUpcomingError] = useState<string | null>(null)
  const [daysAhead, setDaysAhead] = useState(7)
  const [selectedLeagueId, setSelectedLeagueId] = useState<number | null>(null)

  const fetchLive = (leagueId: number | null) => {
    setLiveError(null)
    matchesApi
      .getLive(leagueId !== null ? { league_id: leagueId } : undefined)
      .then((res) => setLiveMatches(res.data))
      .catch((err) => setLiveError(err?.message ?? 'Failed to load live matches'))
      .finally(() => setLiveLoading(false))
  }

  const fetchUpcoming = (leagueId: number | null, days: number) => {
    setUpcomingLoading(true)
    setUpcomingError(null)
    matchesApi
      .getUpcoming({
        days_ahead: days,
        ...(leagueId !== null ? { league_id: leagueId } : {}),
      })
      .then((res) => setUpcomingMatches(res.data))
      .catch((err) => setUpcomingError(err?.message ?? 'Failed to load upcoming matches'))
      .finally(() => setUpcomingLoading(false))
  }

  // Initial load and when filters change
  useEffect(() => {
    setLiveLoading(true)
    fetchLive(selectedLeagueId)
  }, [selectedLeagueId])

  useEffect(() => {
    fetchUpcoming(selectedLeagueId, daysAhead)
  }, [selectedLeagueId, daysAhead])

  // Auto-refresh live matches every 30 seconds
  const liveLeagueRef = useRef(selectedLeagueId)
  liveLeagueRef.current = selectedLeagueId
  useEffect(() => {
    const interval = setInterval(() => {
      fetchLive(liveLeagueRef.current)
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const tabClass = (tab: Tab) =>
    activeTab === tab
      ? 'px-4 py-2 border-b-2 border-blue-600 text-blue-600 font-semibold text-sm'
      : 'px-4 py-2 text-gray-500 hover:text-gray-700 text-sm'

  return (
    <div className="flex gap-6 items-start">
      <LeagueSidebar selectedLeagueId={selectedLeagueId} onSelect={setSelectedLeagueId} />

      <div className="flex-1 min-w-0">
        {/* Tab bar */}
        <div className="flex border-b border-gray-200 mb-4">
          <button onClick={() => setActiveTab('live')} className={tabClass('live')}>
            <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse mr-1 align-middle" />
            Live
            {liveMatches.length > 0 && (
              <span className="ml-1 text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full">
                {liveMatches.length}
              </span>
            )}
          </button>
          <button onClick={() => setActiveTab('upcoming')} className={tabClass('upcoming')}>
            📅 Upcoming
          </button>
        </div>

        {/* Live tab */}
        {activeTab === 'live' && (
          <>
            {liveLoading && <LoadingSpinner />}
            {liveError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                <strong>Error:</strong> {liveError}
              </div>
            )}
            {!liveLoading && !liveError && liveMatches.length === 0 && (
              <div className="text-center py-16 text-gray-500">
                <div className="text-4xl mb-3">🎮</div>
                <p>No matches currently live.</p>
              </div>
            )}
            {!liveLoading && liveMatches.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-4">
                {liveMatches.map((match) => (
                  <MatchCard key={match.id} match={match} />
                ))}
              </div>
            )}
          </>
        )}

        {/* Upcoming tab */}
        {activeTab === 'upcoming' && (
          <>
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
                  {[1, 3, 7, 14].map((d) => (
                    <option key={d} value={d}>{d} day{d !== 1 ? 's' : ''}</option>
                  ))}
                </select>
              </div>
            </div>

            {upcomingLoading && <LoadingSpinner />}
            {upcomingError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                <strong>Error:</strong> {upcomingError}
              </div>
            )}
            {!upcomingLoading && !upcomingError && upcomingMatches.length === 0 && (
              <div className="text-center py-16 text-gray-500">
                <div className="text-4xl mb-3">📅</div>
                <p>No upcoming matches in the next {daysAhead} day{daysAhead !== 1 ? 's' : ''}.</p>
              </div>
            )}
            {!upcomingLoading && upcomingMatches.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-4">
                {upcomingMatches.map((match) => (
                  <MatchCard key={match.id} match={match} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

