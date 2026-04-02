import { useEffect, useState } from 'react'
import apiClient from '../api/client'

interface ValueBetDetail {
  implied_prob: number
  edge: number
  is_value: boolean
  kelly_stake_pct: number
  expected_value: number
}

interface ValueBetItem {
  match_id: number
  team1_name: string
  team2_name: string
  model_prob_team1: number
  model_prob_team2: number
  odds_team1: number | null
  odds_team2: number | null
  value_team1: ValueBetDetail | null
  value_team2: ValueBetDetail | null
  scheduled_at: string | null
}

function EdgeBadge({ edge }: { edge: number }) {
  const pct = (edge * 100).toFixed(1)
  const color =
    edge >= 0.1 ? 'bg-green-100 text-green-800' :
    edge >= 0.05 ? 'bg-yellow-100 text-yellow-800' :
    'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${color}`}>
      +{pct}%
    </span>
  )
}

function TeamRow({
  teamName,
  modelProb,
  odds,
  vb,
}: {
  teamName: string
  modelProb: number
  odds: number | null
  vb: ValueBetDetail | null
}) {
  return (
    <div className={`flex items-center justify-between py-2 px-3 rounded-lg mb-1 ${vb?.is_value ? 'bg-green-50 border border-green-200' : 'bg-gray-50'}`}>
      <div className="flex items-center gap-2">
        {vb?.is_value && <span title="Value bet!">💎</span>}
        <span className="font-medium text-gray-800">{teamName}</span>
      </div>
      <div className="flex items-center gap-4 text-sm text-gray-600">
        <span>Model: <strong>{(modelProb * 100).toFixed(1)}%</strong></span>
        {odds && <span>Kurz: <strong>{odds.toFixed(2)}</strong></span>}
        {vb && <EdgeBadge edge={vb.edge} />}
        {vb?.is_value && (
          <span className="text-xs text-green-700">
            Kelly: {vb.kelly_stake_pct.toFixed(1)}% | EV: {vb.expected_value > 0 ? '+' : ''}{vb.expected_value.toFixed(3)}
          </span>
        )}
      </div>
    </div>
  )
}

export default function ValueBets() {
  const [items, setItems] = useState<ValueBetItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [minEdge, setMinEdge] = useState(0.04)
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    setLoading(true)
    const edgeParam = showAll ? 0 : minEdge
    apiClient
      .get<ValueBetItem[]>(`/value-bets?min_edge=${edgeParam}&limit=50`)
      .then((res) => {
        setItems(res.data)
        setError(null)
      })
      .catch((err) => {
        setError(err?.response?.data?.detail ?? err?.message ?? 'Chyba při načítání')
      })
      .finally(() => setLoading(false))
  }, [minEdge, showAll])

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">💎 Tipáč — Value Bety</h1>
          <p className="text-sm text-gray-500 mt-1">
            Zápasy, kde náš model vidí vyšší šanci výhry, než odpovídá kurzu bookmakera.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600">
            Min. edge:&nbsp;
            <select
              className="border rounded px-2 py-1 text-sm"
              value={minEdge}
              onChange={(e) => { setMinEdge(Number(e.target.value)); setShowAll(false) }}
            >
              <option value={0.02}>2%</option>
              <option value={0.04}>4%</option>
              <option value={0.07}>7%</option>
              <option value={0.10}>10%</option>
            </select>
          </label>
          <button
            className="text-xs text-blue-600 underline"
            onClick={() => setShowAll((v) => !v)}
          >
            {showAll ? 'Filtrovat' : 'Zobrazit vše'}
          </button>
        </div>
      </div>

      {loading && <p className="text-gray-500">Načítám...</p>}
      {error && <p className="text-red-500">{error}</p>}

      {!loading && !error && items.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-4xl mb-2">🔍</p>
          <p>Žádné value bety nenalezeny pro aktuální filtr.</p>
          <p className="text-sm mt-1">Zkus snížit minimální edge nebo klikni "Zobrazit vše".</p>
        </div>
      )}

      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.match_id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-gray-400">
                {item.scheduled_at
                  ? new Date(item.scheduled_at).toLocaleString('cs-CZ', {
                      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
                    })
                  : 'Datum neznámé'}
              </span>
              {(item.value_team1?.is_value || item.value_team2?.is_value) && (
                <span className="text-xs font-semibold px-2 py-0.5 bg-green-100 text-green-700 rounded-full">
                  ✅ Value nalezeno
                </span>
              )}
            </div>
            <TeamRow
              teamName={item.team1_name}
              modelProb={item.model_prob_team1}
              odds={item.odds_team1}
              vb={item.value_team1}
            />
            <TeamRow
              teamName={item.team2_name}
              modelProb={item.model_prob_team2}
              odds={item.odds_team2}
              vb={item.value_team2}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
