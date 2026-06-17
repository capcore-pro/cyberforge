// ============================================
// KLING BALANCE WIDGET — CyberForge
// Solde API Kling + rechargement
// ============================================

import { useState, useEffect } from "react";
import { Zap, AlertTriangle, ExternalLink, Plus } from "lucide-react";

interface KlingBalance {
  id: string;
  units_total: number;
  units_used: number;
  units_remaining: number;
  last_recharged_at: string | null;
  last_updated: string;
}

interface KlingBalanceWidgetProps {
  onRecharge?: () => void;
}

export default function KlingBalanceWidget({ onRecharge }: KlingBalanceWidgetProps) {
  const [balance, setBalance] = useState<KlingBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [recharging, setRecharging] = useState(false);
  const [unitsToAdd, setUnitsToAdd] = useState(100);
  const [showRecharge, setShowRecharge] = useState(false);

  useEffect(() => {
    fetchBalance();
    const interval = setInterval(fetchBalance, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchBalance = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8002/api/video/balance");
      const data = await res.json();
      if (data.success) setBalance(data.data);
    } catch (e) {
      console.error("Balance fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleRecharge = async () => {
    setRecharging(true);
    try {
      const res = await fetch("http://127.0.0.1:8002/api/video/balance/recharge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ units: unitsToAdd })
      });
      const data = await res.json();
      if (data.success) {
        await fetchBalance();
        setShowRecharge(false);
        onRecharge?.();
      }
    } catch (e) {
      console.error("Recharge error:", e);
    } finally {
      setRecharging(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 animate-pulse">
        <div className="h-4 bg-gray-800 rounded w-24 mb-2" />
        <div className="h-8 bg-gray-800 rounded w-16" />
      </div>
    );
  }

  if (!balance) return null;

  const isLow = balance.units_remaining < 20;
  const isCritical = balance.units_remaining < 5;
  const usagePercent = balance.units_total > 0
    ? Math.round((balance.units_used / balance.units_total) * 100)
    : 0;

  return (
    <div className={`rounded-xl border p-4 ${
      isCritical
        ? "bg-red-950 border-red-800"
        : isLow
        ? "bg-yellow-950 border-yellow-800"
        : "bg-gray-900 border-gray-800"
    }`}>

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap size={16} className={
            isCritical ? "text-red-400" :
            isLow ? "text-yellow-400" :
            "text-cyan-400"
          } />
          <span className="text-sm font-medium text-gray-300">
            Crédits Kling
          </span>
        </div>
        {(isLow || isCritical) && (
          <AlertTriangle size={14} className={
            isCritical ? "text-red-400" : "text-yellow-400"
          } />
        )}
      </div>

      {/* Solde */}
      <div className="flex items-end gap-1 mb-3">
        <span className={`text-3xl font-bold ${
          isCritical ? "text-red-400" :
          isLow ? "text-yellow-400" :
          "text-white"
        }`}>
          {balance.units_remaining}
        </span>
        <span className="text-gray-500 text-sm mb-1">
          / {balance.units_total} unités
        </span>
      </div>

      {/* Barre progression */}
      <div className="w-full bg-gray-800 rounded-full h-1.5 mb-3">
        <div
          className={`h-1.5 rounded-full transition-all ${
            isCritical ? "bg-red-500" :
            isLow ? "bg-yellow-500" :
            "bg-cyan-500"
          }`}
          style={{ width: `${100 - usagePercent}%` }}
        />
      </div>

      {/* Estimation */}
      <p className="text-xs text-gray-500 mb-3">
        ≈ {Math.floor(balance.units_remaining / 10)} vidéos 5s restantes
      </p>

      {/* Alerte critique */}
      {isCritical && (
        <p className="text-xs text-red-400 mb-3">
          ⚠️ Solde critique — recharge nécessaire
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => setShowRecharge(!showRecharge)}
          className="flex items-center gap-1 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 
                     text-white text-xs rounded-lg transition-colors"
        >
          <Plus size={12} />
          Recharger
        </button>
        <a
          href="https://kling.ai/dev/api-key"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 
                     text-gray-300 text-xs rounded-lg transition-colors"
        >
          <ExternalLink size={12} />
          Kling Console
        </a>
      </div>

      {/* Panel rechargement */}
      {showRecharge && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <p className="text-xs text-gray-400 mb-2">
            Après achat sur Kling Console, indique les unités ajoutées :
          </p>
          <div className="flex gap-2">
            <input
              type="number"
              value={unitsToAdd}
              onChange={(e) => setUnitsToAdd(Number(e.target.value))}
              min={10}
              max={10000}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 
                         py-1.5 text-white text-sm focus:outline-none focus:border-cyan-500"
            />
            <button
              onClick={handleRecharge}
              disabled={recharging}
              className="px-3 py-1.5 bg-green-600 hover:bg-green-500 disabled:opacity-50
                         text-white text-xs rounded-lg transition-colors"
            >
              {recharging ? "..." : "Confirmer"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
