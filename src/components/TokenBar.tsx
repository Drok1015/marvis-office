type TokenBarProps = {
  totalTokens: number;
};

export function TokenBar({ totalTokens }: TokenBarProps) {
  const dailyLimit = 10_000_000;
  const pct = Math.min((totalTokens / dailyLimit) * 100, 100);
  const remaining = Math.max(dailyLimit - totalTokens, 0);

  return (
    <div className="token-bar">
      <div className="token-head">
        <div className="token-item consumed">
          <span className="token-kicker">今日消耗</span>
          <strong>{totalTokens.toLocaleString()}</strong>
          <small>Token</small>
        </div>
        <div className="token-item remain">
          <span className="token-kicker">剩余额度</span>
          <strong>{remaining.toLocaleString()}</strong>
          <small>Token</small>
        </div>
      </div>
      <div className="token-track">
        <span style={{ width: `${pct}%` }} />
      </div>
      <div className="token-foot">
        <span>日上限 {dailyLimit.toLocaleString()}</span>
        <span>已用 {pct.toFixed(2)}%</span>
      </div>
    </div>
  );
}
