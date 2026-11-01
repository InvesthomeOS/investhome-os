'use client';

import { useTranslations } from 'next-intl';
import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';
import { InvestorPositionCard } from './investor-position-card';

export interface InvestmentOverviewProps {
  detail: InvestmentDetail;
}

export function InvestmentOverviewSection({ detail }: InvestmentOverviewProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const { overview, property, investment: inv } = detail;

  return (
    <div className="inv-detail-overview">
      <section className="inv-detail-panel" aria-labelledby="thesis-heading">
        <SectionHeader title={tChrome('k8fd21aad26')} subtitle={tChrome('k26426ac2df')} />
        <div className="inv-detail-overview__content">
          <div className="inv-detail-overview__block">
            <h3 id="thesis-heading" className="inv-detail-overview__heading">
              Investment Thesis
            </h3>
            <p>{overview.thesis}</p>
          </div>
          <div className="inv-detail-overview__block">
            <h3 className="inv-detail-overview__heading">{tChrome('k69fb26dda8')}</h3>
            <p>{overview.strategy}</p>
          </div>
          <div className="inv-detail-overview__block">
            <h3 className="inv-detail-overview__heading">{tChrome('k069c56503b')}</h3>
            <p>{overview.businessPlan}</p>
          </div>
          <dl className="inv-detail-overview__meta">
            <div>
              <dt>{tChrome('k8469790818')}</dt>
              <dd>{overview.holdPeriod}</dd>
            </div>
            <div>
              <dt>{tChrome('kbae0f451fe')}</dt>
              <dd>{overview.propertyType}</dd>
            </div>
            <div>
              <dt>{tChrome('k78d4bd027f')}</dt>
              <dd>{overview.assetClass}</dd>
            </div>
            <div>
              <dt>{tChrome('kc834b90b94')}</dt>
              <dd>{property.unitCount > 0 ? property.unitCount : 'N/A'}</dd>
            </div>
            <div>
              <dt>{tChrome('k463f43660d')}</dt>
              <dd>{property.buildingSizeSqFt.toLocaleString()} sq ft</dd>
            </div>
          </dl>
          <div className="inv-detail-overview__dates">
            <h3 className="inv-detail-overview__heading">{tChrome('kb1166960be')}</h3>
            <ul className="inv-detail-overview__date-list">
              {overview.keyDates.map((kd) => (
                <li key={kd.label}>
                  <span>{kd.label}</span>
                  <time dateTime={kd.date}>{kd.date === 'TBD' || kd.date === 'N/A' ? kd.date : formatInvestorDate(kd.date)}</time>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="inv-detail-panel" aria-labelledby="property-heading">
        <SectionHeader title={tChrome('kca8911ec41')} subtitle={`${property.neighborhood} · ${property.submarket}`} />
        <div className="inv-detail-property">
          <div className="inv-detail-property__gallery" role="list" aria-label={tChrome('k7753d95fae')}>
            {property.galleryImages.map((img) => (
              <figure key={img.url} className="inv-detail-property__gallery-item" role="listitem">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={img.url} alt={img.alt} loading="lazy" />
              </figure>
            ))}
          </div>
          <div className="inv-detail-property__info">
            <p>{property.description}</p>
            <dl className="inv-detail-property__meta">
              <div>
                <dt>{tChrome('kd70f93df5e')}</dt>
                <dd>
                  {inv.address}, {inv.city}, {inv.state}
                </dd>
              </div>
              <div>
                <dt>{tChrome('kd2b782f85f')}</dt>
                <dd>{property.neighborhood}</dd>
              </div>
              <div>
                <dt>{tChrome('k5465174048')}</dt>
                <dd>{property.submarket}</dd>
              </div>
              {property.yearBuilt ? (
                <div>
                  <dt>{tChrome('k87f1a17808')}</dt>
                  <dd>{property.yearBuilt}</dd>
                </div>
              ) : null}
              {property.parkingSpaces ? (
                <div>
                  <dt>{tChrome('kaef05c2870')}</dt>
                  <dd>{property.parkingSpaces} spaces</dd>
                </div>
              ) : null}
            </dl>
            <div className="inv-detail-property__amenities">
              <h4>{tChrome('kcf19addeca')}</h4>
              <ul>
                {property.amenities.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <InvestorPositionCard detail={detail} />
    </div>
  );
}
