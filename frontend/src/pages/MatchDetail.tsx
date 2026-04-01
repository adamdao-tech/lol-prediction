import { useEffect, useState, useCallback } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { matchesApi, predictionsApi, type MatchDetail } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import LiveGamePanel from '../components/LiveGamePanel'

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

function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}m ${s}s`
}

export default function MatchDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const gameIdParam = searchParams.get('game_id')
  const [match, setMatch] = useState<MatchDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

  const loadMatch = useCallback(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    matchesApi
      .getById(Number(id))
      .then((res) => setMatch(res.data))
      .catch((err) => setError(err?.message ?? 'Failed to load match'))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    loadMatch()
  }, [id])

  const handleGeneratePrediction = async () => {
    if (!id) return
    setGenerating(true)
    try {
      await predictionsApi.generate(Number(id))
      loadMatch()
    } catch (err: unknown) {
      alert('Failed to generate prediction')
    } finally {
      setGenerating(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (error) return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
      <strong>Error:</strong> {error}
    </div>
  )
  if (!match) return null

  // Resolve game_id: use URL param first, then auto-detect from running games
  const resolvedGameId: string | null = gameIdParam ?? (() => {
    if (match.status !== 'running') return null
    const runningGame = match.games.find((g) => g.status !== 'finished' && g.pandascore_id)
    if (runningGame?.pandascore_id) return runningGame.pandascore_id
    return null
  })()

  const latestPred = match.predictions.length > 0
    ? match.predictions.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
    : null

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-4">
        <Link to="/" className="text-yellow-600 hover:underline text-sm">← Back to Dashboard</Link>
      </div>

      {/* Match header */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-4">
        <div className="text-sm text-gray-500 mb-2">
          {match.tournament?.league?.name} &bull; {match.tournament?.name}
        </div>

        <div className="flex items-center justify-center gap-8 my-4">
          <div className="text-center">
            {match.team1?.image_url && (
              <img src={match.team1.image_url} alt={match.team1.name} className="w-16 h-16 mx-auto mb-2 object-contain" />
            )}
            <div className="text-xl font-bold">{match.team1?.name ?? 'TBD'}</div>
            <div className="text-gray-500 text-sm">{match.team1?.acronym}</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-300">VS</div>
            <div className="text-sm text-gray-500 mt-1">BO{match.number_of_games ?? '?'}</div>
          </div>
          <div className="text-center">
            {match.team2?.image_url && (
              <img src={match.team2.image_url} alt={match.team2.name} className="w-16 h-16 mx-auto mb-2 object-contain" />
            )}
            <div className="text-xl font-bold">{match.team2?.name ?? 'TBD'}</div>
            <div className="text-gray-500 text-sm">{match.team2?.acronym}</div>
          </div>
        </div>

        <div className="text-center text-gray-600">
          <span className="font-medium">{formatDate(match.scheduled_at)}</span>
          {match.patch_version && <span className="ml-2 text-sm text-gray-400">Patch {match.patch_version}</span>}
        </div>
        <div className="text-center mt-1">
          <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
            match.status === 'running' ? 'bg-green-100 text-green-800' :
            match.status === 'finished' ? 'bg-gray-100 text-gray-600' :
            'bg-blue-100 text-blue-800'
          }`}>
            {match.status}
          </span>
        </div>
      </div>

      {/* Live game panel — shown when match is running or game_id query param is present */}
      {(match.status === 'running' || gameIdParam) && (
        <LiveGamePanel gameId={resolvedGameId ?? String(id)} />
      )}

      {/* Predictions section */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Predictions</h2>
          <button
            onClick={handleGeneratePrediction}
            disabled={generating}
            className="bg-yellow-400 hover:bg-yellow-300 text-gray-900 text-sm font-medium px-4 py-1.5 rounded disabled:opacity-50 transition-colors"
          >
            {generating ? 'Generating...' : 'Generate Prediction'}
          </button>
        </div>

        {latestPred ? (
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center bg-gray-50 rounded p-3">
              <div className="text-2xl font-bold text-yellow-600">
                {(latestPred.win_prob_team1 * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500">{match.team1?.name ?? 'Team 1'} win</div>
            </div>
            <div className="text-center bg-gray-50 rounded p-3">
              <div className="text-2xl font-bold text-yellow-600">
                {(latestPred.win_prob_team2 * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500">{match.team2?.name ?? 'Team 2'} win</div>
            </div>
            {latestPred.predicted_total_kills && (
              <div className="text-center bg-gray-50 rounded p-3">
                <div className="text-2xl font-bold text-blue-600">{latestPred.predicted_total_kills}</div>
                <div className="text-sm text-gray-500">Predicted kills</div>
              </div>
            )}
            {latestPred.predicted_duration_seconds && (
              <div className="text-center bg-gray-50 rounded p-3">
                <div className="text-2xl font-bold text-blue-600">
                  {formatDuration(latestPred.predicted_duration_seconds)}
                </div>
                <div className="text-sm text-gray-500">Predicted duration</div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-gray-400 text-center py-4">No predictions yet. Click "Generate Prediction" to create one.</p>
        )}
      </div>

      {/* Odds section */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-4">
        <h2 className="text-lg font-semibold mb-4">Odds</h2>
        {match.odds_snapshots.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b">
                <th className="text-left pb-2">Bookmaker</th>
                <th className="text-right pb-2">{match.team1?.acronym ?? 'T1'}</th>
                <th className="text-right pb-2">{match.team2?.acronym ?? 'T2'}</th>
                <th className="text-right pb-2">Vig</th>
                <th className="text-right pb-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {match.odds_snapshots.map((snap) => (
                <tr key={snap.id} className="border-b last:border-0">
                  <td className="py-2">{snap.bookmaker}</td>
                  <td className="text-right py-2">{snap.team1_odds}</td>
                  <td className="text-right py-2">{snap.team2_odds}</td>
                  <td className="text-right py-2 text-gray-400">{snap.vig ? `${(snap.vig * 100).toFixed(2)}%` : '—'}</td>
                  <td className="text-right py-2 text-gray-400">{formatDate(snap.snapshot_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-400 text-center py-4">No odds imported yet.</p>
        )}
      </div>

      {/* Games section */}
      {match.games.length > 0 && (
        <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Games</h2>
          <div className="space-y-2">
            {match.games.map((game) => (
              <div key={game.id} className="flex items-center gap-4 bg-gray-50 rounded p-3 text-sm">
                <span className="font-medium">Game {game.game_number}</span>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  game.status === 'finished' ? 'bg-gray-200 text-gray-700' : 'bg-blue-100 text-blue-700'
                }`}>{game.status}</span>
                {game.total_kills != null && <span className="text-gray-600">{game.total_kills} kills</span>}
                {game.duration_seconds != null && (
                  <span className="text-gray-600">{formatDuration(game.duration_seconds)}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
