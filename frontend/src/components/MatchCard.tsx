import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { liveApi, type Match } from '../api/client'

interface Props {
  match: Match
}

function formatDate(dt: string | null): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('cs-CZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    scheduled: 'bg-blue-100 text-blue-800',
    running: 'bg-green-100 text-green-800',
    finished: 'bg-gray-100 text-gray-600',
    cancelled: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

export default function MatchCard({ match }: Props) {
  const pred = match.latest_prediction
  const odds = match.latest_odds
  const isLive = match.status === 'running'

  const [liveProb, setLiveProb] = useState<{ blue: number; red: number } | null>(null)

  useEffect(() => {
    if (!isLive || !match.live_game_id) return

    liveApi
      .getLivePrediction(match.live_game_id)
      .then((res) => {
        const p = res.data.prediction
        if (p) {
          setLiveProb({ blue: p.win_prob_blue, red: p.win_prob_red })
        }
      })
      .catch(() => {
        // Silently fall back to pre-game prediction
      })
  }, [isLive, match.live_game_id])

  const showBlueProb = liveProb ? Math.round(liveProb.blue * 100) : pred ? Math.round(pred.win_prob_team1 * 100) : null
  const showRedProb = liveProb ? Math.round(liveProb.red * 100) : pred ? Math.round(pred.win_prob_team2 * 100) : null

  return (
    <div className={`bg-white rounded-lg shadow border p-4 hover:shadow-md transition-shadow ${
      isLive ? 'border-green-400 ring-2 ring-green-300' : 'border-gray-200'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-500">
          {match.tournament?.league?.name ?? '—'} &bull; {match.tournament?.name ?? '—'}
        </span>
        <div className="flex items-center gap-1">
          {isLive && (
            <span className="flex items-center gap-0.5 text-xs font-semibold text-red-600">
              <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              LIVE
            </span>
          )}
          <StatusBadge status={match.status} />
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 my-3">
        <div className="text-center flex-1">
          {match.team1?.image_url && (
            <img src={match.team1.image_url} alt={match.team1.name} className="w-8 h-8 mx-auto mb-1 object-contain" />
          )}
          <div className="font-semibold text-gray-800">{match.team1?.acronym ?? match.team1?.name ?? 'TBD'}</div>
          {showBlueProb !== null && (
            <div className={`text-sm font-medium ${liveProb ? 'text-blue-600' : 'text-yellow-600'}`}>
              {showBlueProb}%
            </div>
          )}
        </div>
        <div className="text-gray-400 font-bold text-lg">vs</div>
        <div className="text-center flex-1">
          {match.team2?.image_url && (
            <img src={match.team2.image_url} alt={match.team2.name} className="w-8 h-8 mx-auto mb-1 object-contain" />
          )}
          <div className="font-semibold text-gray-800">{match.team2?.acronym ?? match.team2?.name ?? 'TBD'}</div>
          {showRedProb !== null && (
            <div className={`text-sm font-medium ${liveProb ? 'text-red-500' : 'text-yellow-600'}`}>
              {showRedProb}%
            </div>
          )}
        </div>
      </div>

      <div className="text-center text-sm text-gray-500 mb-3">
        {formatDate(match.scheduled_at)} &bull; BO{match.number_of_games ?? '?'}
      </div>

      {odds && (
        <div className="text-xs text-gray-500 text-center mb-2">
          Odds: {odds.team1_odds} / {odds.team2_odds} ({odds.bookmaker})
        </div>
      )}

      {/* Live win probability mini bar */}
      {isLive && liveProb && (
        <div className="mb-2">
          <div className="h-2 rounded-full overflow-hidden flex bg-red-400">
            <div
              className="bg-blue-500 transition-all duration-700"
              style={{ width: `${Math.round(liveProb.blue * 100)}%` }}
            />
          </div>
        </div>
      )}

      <Link
        to={`/matches/${match.id}`}
        className="block w-full text-center bg-yellow-400 hover:bg-yellow-300 text-gray-900 text-sm font-medium py-1.5 rounded transition-colors"
      >
        Detail →
      </Link>
    </div>
  )
}
