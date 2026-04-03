import Link from 'next/link';
import { notFound } from 'next/navigation';
import carsData from '../../data/cars.json';
import ImageCarousel from '../components/ImageCarousel';

const getDealTier = (score: number) => {
  if (score >= 90) return { text: 'Hidden Gem', icon: '💎', badgeClass: 'badge-gem' };
  if (score >= 85) return { text: 'Excellent', icon: '🌟', badgeClass: 'badge-excellent' };
  if (score >= 70) return { text: 'Great', icon: '👍', badgeClass: 'badge-good' };
  if (score >= 50) return { text: 'Fair', icon: '😐', badgeClass: 'badge-fair' };
  return { text: 'Poor', icon: '⚠️', badgeClass: 'badge-poor' };
};

const getScoreColor = (score: number) => {
  if (score >= 70) return 'var(--accent-green)';
  if (score >= 50) return 'var(--accent-yellow)';
  return 'var(--accent-red)';
};

export default async function ListingDetail({ params }: { params: { id: string } }) {
  const { id } = await params;
  const car = carsData.find((c) => c.id === id);

  if (!car) {
    notFound();
  }

  const uiDealScore = car.deal_score ?? 50;



  return (
    <div>
      {/* Background Banner */}
      <div style={{ backgroundColor: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-light)', padding: '2rem 0' }}>
        <div className="container">
          <Link href="/" style={{ color: 'var(--accent-blue)', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem', fontWeight: 500 }}>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" style={{ width: '1.25rem', height: '1.25rem' }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg> Back to Inventory
          </Link>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '2rem' }}>
            <div>
              <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '2.5rem', marginBottom: '0.5rem' }}>{car.title}</h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>{car.mileage.toLocaleString()} miles • {car.location}</p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Price</div>
              <div style={{ fontSize: '3rem', fontWeight: 700, color: 'var(--accent-blue)', lineHeight: 1 }}>${car.current_bid.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="container" style={{ padding: '3rem 2rem', display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)', gap: '4rem', alignItems: 'start' }}>

        {/* Left Column: Photos and Description */}
        <div>
          {/* Main Photo Gallery Carousel */}
          <ImageCarousel images={car.all_images} altText={car.title} />

          {/* Extracted Raw HTML Details */}
          <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '2.5rem', borderRadius: '12px', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-light)' }}>
            <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.75rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '1rem' }}>Vehicle Details</h3>
            <div
              className="raw-description-content"
              style={{ lineHeight: '1.6', color: 'var(--text-primary)' }}
              dangerouslySetInnerHTML={{ __html: car.raw_html_description }}
            />

            {/* Inline styles to fix GSA HTML formatting */}
            <style dangerouslySetInnerHTML={{
              __html: `
              .raw-description-content h4 {
                font-size: 1.25rem;
                margin-top: 2rem;
                margin-bottom: 0.75rem;
                color: var(--text-primary);
                border-bottom: 1px solid var(--border-light);
                padding-bottom: 0.25rem;
              }
              .raw-description-content ul {
                padding-left: 2rem;
                margin-bottom: 1rem;
                list-style-type: disc;
              }
              .raw-description-content li {
                margin-bottom: 0.5rem;
              }
              .raw-description-content p {
                margin-bottom: 1rem;
              }
            `}} />
          </div>
        </div>

        {/* Right Column: AI Deal Breakdown */}
        <div style={{ position: 'sticky', top: '100px' }}>

          <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '2rem', borderRadius: '12px', boxShadow: 'var(--shadow-md)', border: `2px solid ${getScoreColor(uiDealScore)}` }}>
            <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
              <div className={`badge ${getDealTier(uiDealScore).badgeClass}`} style={{ marginBottom: '1rem', fontSize: '1rem', padding: '0.5rem 1rem' }}>
                {getDealTier(uiDealScore).text} Deal
              </div>
              <div style={{ fontSize: '4rem', fontWeight: 800, lineHeight: 1 }}>{uiDealScore}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.5rem' }}>Intelligent Deal Score (out of 100)</div>
            </div>

            <h4 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1.5rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem' }}>Under The Hood Breakdown</h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

              {/* Signal 1: Price */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                  <span style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ color: 'var(--accent-blue)' }}>📊</span> Market Value
                    <span className="custom-tooltip-container">
                      <span style={{ fontSize: '0.85rem', opacity: 0.6, marginLeft: '0.3rem' }}>(i)</span>
                      <span className="custom-tooltip-text">Evaluates depreciation, mileage, and historical market trends to determine a fair baseline retail price.</span>
                    </span>
                  </span>
                  <span><strong>{car.price_score ?? 50}</strong> / 100</span>
                </div>
                <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${car.price_score ?? 50}%`, height: '100%', backgroundColor: getScoreColor(car.price_score ?? 50) }}></div>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginTop: '0.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span>
                  {car.current_bid < car.predicted_market_value
                      ? `Price is $${(car.predicted_market_value - car.current_bid).toLocaleString()} below predicted fair market value.`
                      : `Price is $${(car.current_bid - car.predicted_market_value).toLocaleString()} above predicted fair market value.`}
                  </span>
                  <span style={{ fontWeight: 500 }}>Predicted Value: ${car.predicted_market_value.toLocaleString()}</span>
                </div>
              </div>

              {/* Signal 2: Visual Condition */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                  <span style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ color: 'var(--accent-yellow)' }}>✨</span> Visual Condition
                    <span className="custom-tooltip-container">
                      <span style={{ fontSize: '0.85rem', opacity: 0.6, marginLeft: '0.3rem' }}>(i)</span>
                      <span className="custom-tooltip-text">AI vision models automatically scan all vehicle images to detect visible paint damage, rust, or severe interior wear.</span>
                    </span>
                  </span>
                  <span><strong>{Math.round(car.condition_score)}</strong> / 100</span>
                </div>
                <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(100, Math.max(0, car.condition_score))}%`, height: '100%', backgroundColor: getScoreColor(car.condition_score) }}></div>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
                  Based on multimodal analysis of listing photos.
                </div>
              </div>

              {/* Signal 3: Scam Risk */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                  <span style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ color: 'var(--accent-red)' }}>🔍</span> Authenticity Score
                    <span className="custom-tooltip-container">
                      <span style={{ fontSize: '0.85rem', opacity: 0.6, marginLeft: '0.3rem' }}>(i)</span>
                      <span className="custom-tooltip-text">Compares the provided listing description against a vast database of known scam scripts and suspicious phrasing.</span>
                    </span>
                  </span>
                  <span style={{ color: getScoreColor(car.scam_distance), fontWeight: 600 }}>
                    {car.scam_distance >= 70 ? 'Safe' : car.scam_distance >= 50 ? 'Caution' : 'High Risk'}
                  </span>
                </div>
                <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${car.scam_distance}%`, height: '100%', backgroundColor: getScoreColor(car.scam_distance) }}></div>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
                  Authenticity rating based on semantic distance from known fraudulent listings (score: {Math.round(car.scam_distance)}/100).
                </div>
              </div>

            </div>

            <button className="btn btn-primary" style={{ width: '100%', marginTop: '2rem' }}>
              Contact Seller • ${car.current_bid.toLocaleString()}
            </button>
            <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>
              <a href={car.listing_url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline' }}>View Original Listing</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
