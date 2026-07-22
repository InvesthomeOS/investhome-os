'use client';

import {
  CAMPAIGNS,
  CONVERSION_SERIES,
  MARKETING_KPIS,
  SOURCES,
  formatTry,
} from './demo-data';

function ConversionChart() {
  const w = 560;
  const h = 168;
  const pad = { t: 12, r: 12, b: 26, l: 32 };
  const n = CONVERSION_SERIES.labels.length;
  const max = Math.max(...CONVERSION_SERIES.leads, ...CONVERSION_SERIES.conversions) * 1.12;

  const xs = (i: number) => pad.l + (i / Math.max(n - 1, 1)) * (w - pad.l - pad.r);
  const ys = (v: number) => pad.t + ((max - v) / max) * (h - pad.t - pad.b);

  const area = (values: readonly number[]) => {
    const top = values.map((v, i) => `${xs(i).toFixed(1)},${ys(v).toFixed(1)}`).join(' ');
    return `${pad.l},${h - pad.b} ${top} ${w - pad.r},${h - pad.b}`;
  };

  const line = (values: readonly number[]) =>
    values.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xs(i).toFixed(1)} ${ys(v).toFixed(1)}`).join(' ');

  return (
    <svg
      className="g1-chart"
      viewBox={`0 0 ${w} ${h}`}
      role="img"
      aria-label="Haftalık lead ve dönüşüm grafiği"
    >
      {[0.25, 0.5, 0.75, 1].map((p) => {
        const y = pad.t + (1 - p) * (h - pad.t - pad.b);
        return (
          <line key={p} x1={pad.l} x2={w - pad.r} y1={y} y2={y} stroke="#ebe4da" strokeWidth={1} />
        );
      })}
      <polygon points={area(CONVERSION_SERIES.leads)} fill="url(#g1LeadFill)" />
      <path d={line(CONVERSION_SERIES.leads)} fill="none" stroke="#9d7b55" strokeWidth={2.25} />
      <path
        d={line(CONVERSION_SERIES.conversions)}
        fill="none"
        stroke="#2f6f6c"
        strokeWidth={2.25}
        strokeDasharray="4 3"
      />
      {CONVERSION_SERIES.labels.map((label, i) => (
        <text
          key={label}
          x={xs(i)}
          y={h - 8}
          textAnchor="middle"
          fill="#9a9288"
          fontSize={11}
          fontFamily="IBM Plex Sans, sans-serif"
        >
          {label}
        </text>
      ))}
      <defs>
        <linearGradient id="g1LeadFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#9d7b55" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#9d7b55" stopOpacity="0" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function MarketingAnalyticsTab() {
  const maxLeads = Math.max(...SOURCES.map((s) => s.leads), 1);

  return (
    <div className="g1-mkt" data-testid="g1-marketing">
      <div className="g1-preview__toolbar">
        <div className="g1-preview__toolbar-left">
          <div>
            <h2 className="g1-preview__title">Pazarlama Analitiği</h2>
            <p className="g1-preview__subtitle">
              Son 7 gün · kampanya performansı ve kaynak attribution (demo)
            </p>
          </div>
        </div>
      </div>

      <div className="g1-kpi-row">
        {MARKETING_KPIS.map((kpi) => (
          <div key={kpi.id} className="g1-kpi">
            <div className="g1-kpi__label">{kpi.label}</div>
            <div className="g1-kpi__value">{kpi.value}</div>
            <div className={`g1-kpi__delta ${kpi.up ? 'g1-kpi__delta--up' : 'g1-kpi__delta--down'}`}>
              {kpi.delta}
            </div>
          </div>
        ))}
      </div>

      <div className="g1-mkt-grid">
        <section className="g1-panel">
          <div className="g1-panel__head">
            <h3 className="g1-panel__title">Dönüşüm trendi</h3>
            <span className="g1-panel__hint">Lead (alan) · Dönüşüm (kesik)</span>
          </div>
          <ConversionChart />
        </section>

        <section className="g1-panel">
          <div className="g1-panel__head">
            <h3 className="g1-panel__title">Kaynak attribution</h3>
            <span className="g1-panel__hint">Lead sayısı</span>
          </div>
          <div className="g1-attr">
            {SOURCES.map((s) => (
              <div key={s.source} className="g1-attr__row">
                <span className="g1-attr__name">{s.source}</span>
                <div className="g1-attr__track" aria-hidden>
                  <i style={{ width: `${(s.leads / maxLeads) * 100}%` }} />
                </div>
                <span className="g1-attr__val">{s.leads}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="g1-panel">
        <div className="g1-panel__head">
          <h3 className="g1-panel__title">Kampanya performansı</h3>
          <span className="g1-panel__hint">Harcama · CPL · Dönüşüm</span>
        </div>
        <div className="g1-table-wrap">
          <table className="g1-table">
            <thead>
              <tr>
                <th>Kampanya</th>
                <th>Kanal</th>
                <th className="num">Harcama</th>
                <th className="num">Lead</th>
                <th className="num">CPL</th>
                <th className="num">Conv %</th>
              </tr>
            </thead>
            <tbody>
              {CAMPAIGNS.map((c) => (
                <tr key={c.id}>
                  <td>
                    <strong>{c.name}</strong>
                  </td>
                  <td>{c.channel}</td>
                  <td className="num">{formatTry(c.spend)}</td>
                  <td className="num">{c.leads}</td>
                  <td className="num">₺{c.cpl.toLocaleString('tr-TR')}</td>
                  <td className="num">%{c.conv.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="g1-panel">
        <div className="g1-panel__head">
          <h3 className="g1-panel__title">Lead kaynak tablosu</h3>
          <span className="g1-panel__hint">Oturum · oran · ilişkili gelir</span>
        </div>
        <div className="g1-table-wrap">
          <table className="g1-table">
            <thead>
              <tr>
                <th>Kaynak</th>
                <th className="num">Oturum</th>
                <th className="num">Lead</th>
                <th className="num">Oran</th>
                <th className="num">Gelir</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES.map((s) => (
                <tr key={s.source}>
                  <td>
                    <strong>{s.source}</strong>
                  </td>
                  <td className="num">{s.sessions.toLocaleString('tr-TR')}</td>
                  <td className="num">{s.leads}</td>
                  <td className="num">%{s.rate.toFixed(1)}</td>
                  <td className="num">{formatTry(s.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
