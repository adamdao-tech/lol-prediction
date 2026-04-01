import { useEffect, useState } from 'react'
import { liveApi, type LiveWindow } from '../api/client'

interface Props {
  gameId: string
}

const DRAGON_EMOJI: Record<string, string> = {
  infernal: '🔥',
  mountain: '🪨',
  ocean: '🌊',
  cloud: '💨',
  hextech: '⚡',
  chemtech: '☠️',
  elder: '🐉',
}

function dragonLabel(dragon: string): string {
  const key = dragon.toLowerCase()
  return (DRAGON_EMOJI[key] ?? '🐉') + ' ' + dragon.charAt(0).toUpperCase() + dragon.slice(1)
}

function formatGold(gold: number): string {
  if (Math.abs(gold) >= 1000) {
    return (gold / 1000).toFixed(1) + 'k'
  }
  return String(gold)
}

function DiffStat({ label, blueSide, redSide }: { label: string; blueSide: number; redSide: number }) {
  return (
    <div className="bg-gray-50 rounded p-2">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="font-bold text-gray-800">
        <span className="text-blue-600">{blueSide}</span>
        {' / '}
        <span className="text-red-500">{redSide}</span>
      </div>
    </div>
  )
}

function Sparkline({ history }: { history: number[] }) {
  if (history.length < 3) return null

  const width = 300
  const height = 40
  const min = Math.min(...history)
  const max = Math.max(...history)
  const range = max - min || 0.01

  const points = history.map((v, i) => {
    const x = (i / (history.length - 1)) * width
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  return (
    <div className="mt-3">
      <div className="text-xs text-gray-400 mb-1">Trend (last {history.length} frames)</div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        style={{ height: '40px' }}
        preserveAspectRatio="none"
      >
        <polyline
          points={points.join(' ')}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
    </div>
  )
}

export default function LiveGamePanel({ gameId }: Props) {
  const [data, setData] = useState<LiveWindow | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  useEffect(() => {
    const fetchData = () => {
      liveApi
        .getLivePrediction(gameId)
        .then((res) => {
          setData(res.data)
          setLastUpdated(new Date())
          setError(null)
        })
        .catch((err) => {
          setError(err?.response?.data?.detail ?? err?.message ?? 'Failed to load live data')
        })
    }

    fetchData()
    const interval = setInterval(fetchData, 30_000)
    return () => clearInterval(interval)
  }, [gameId])

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4 text-red-700 text-sm">
        🔴 Live data unavailable: {error}
      </div>
    )
  }

  if (!data || !data.prediction) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4 text-gray-500 text-sm text-center animate-pulse">
        Loading live game data…
      </div>
    )
  }

  const pred = data.prediction
  const bluePct = Math.round(pred.win_prob_blue * 100)
  const redPct = Math.round(pred.win_prob_red * 100)
  const goldDiff = pred.signals.gold_diff

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
          <h2 className="text-lg font-semibold">Live Game</h2>
          {pred.game_timer && pred.game_timer !== '00:00' && (
            <span className="text-sm text-gray-600 font-mono">⏱ {pred.game_timer}</span>
          )}
          <span className="text-xs text-gray-400 font-normal ml-1">game id: {gameId}</span>
        </div>
        {lastUpdated && (
          <span className="text-xs text-gray-400">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Win probability bar */}
      <div className="mb-5">
        <div className="flex justify-between text-sm font-medium mb-1">
          <span className="text-blue-600">Blue {bluePct}%</span>
          <span className="text-red-500">Red {redPct}%</span>
        </div>
        <div className="h-4 rounded-full overflow-hidden flex bg-red-400">
          <div
            className="bg-blue-500 transition-all duration-700"
            style={{ width: `${bluePct}%` }}
          />
        </div>
        <Sparkline history={data.prob_history ?? []} />
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3 mb-4 text-center text-sm">
        {/* Gold */}
        <div className="bg-gray-50 rounded p-2">
          <div className="text-xs text-gray-500 mb-1">Gold diff</div>
          <div className={`font-bold ${goldDiff > 0 ? 'text-blue-600' : goldDiff < 0 ? 'text-red-500' : 'text-gray-700'}`}>
            {goldDiff > 0 ? '↑' : goldDiff < 0 ? '↓' : '—'} {formatGold(Math.abs(goldDiff))}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">
            {formatGold(pred.blue_total_gold)} / {formatGold(pred.red_total_gold)}
          </div>
        </div>

        {/* Kills */}
        <div className="bg-gray-50 rounded p-2">
          <div className="text-xs text-gray-500 mb-1">Kills</div>
          <div className="font-bold text-gray-800">
            <span className="text-blue-600">{pred.blue_total_kills}</span>
            {' — '}
            <span className="text-red-500">{pred.red_total_kills}</span>
          </div>
        </div>

        <DiffStat
          label="Towers"
          blueSide={pred.blue_towers}
          redSide={pred.red_towers}
        />
        <DiffStat
          label="Barons"
          blueSide={pred.blue_barons}
          redSide={pred.red_barons}
        />
        <DiffStat
          label="Dragons"
          blueSide={pred.blue_dragons.length}
          redSide={pred.red_dragons.length}
        />
        <DiffStat
          label="Inhibitors"
          blueSide={pred.signals.inhibitor_diff >= 0 ? pred.signals.inhibitor_diff : 0}
          redSide={pred.signals.inhibitor_diff < 0 ? -pred.signals.inhibitor_diff : 0}
        />
      </div>

      {/* Dragons detail */}
      {(pred.blue_dragons.length > 0 || pred.red_dragons.length > 0) && (
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <div className="text-gray-400 mb-1">Blue dragons</div>
            <div className="flex flex-wrap gap-1">
              {pred.blue_dragons.map((d, i) => (
                <span key={i} className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                  {dragonLabel(d)}
                </span>
              ))}
            </div>
          </div>
          <div>
            <div className="text-gray-400 mb-1">Red dragons</div>
            <div className="flex flex-wrap gap-1">
              {pred.red_dragons.map((d, i) => (
                <span key={i} className="bg-red-50 text-red-600 px-2 py-0.5 rounded-full">
                  {dragonLabel(d)}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
