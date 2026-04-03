"use client";

import { useState } from 'react';
import Link from 'next/link';
import carsData from '../data/cars.json';

const getDealTier = (score: number) => {
  if (score >= 90) return { text: 'Hidden Gem', icon: '💎', badgeClass: 'badge-gem' };
  if (score >= 85) return { text: 'Excellent', icon: '🌟', badgeClass: 'badge-excellent' };
  if (score >= 70) return { text: 'Great', icon: '👍', badgeClass: 'badge-good' };
  if (score >= 50) return { text: 'Fair', icon: '😐', badgeClass: 'badge-fair' };
  return { text: 'Poor', icon: '⚠️', badgeClass: 'badge-poor' };
};

const computeUiScore = (car: any) => car.deal_score ?? 50;

export default function Home() {
  const [cars, setCars] = useState(() => {
    return [...carsData].sort((a: any, b: any) => computeUiScore(b) - computeUiScore(a)).slice(0, 6);
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    // Reset if search is empty
    if (!searchQuery.trim()) {
      setCars([...carsData].sort((a: any, b: any) => computeUiScore(b) - computeUiScore(a)).slice(0, 6));
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!res.ok) throw new Error('Search request failed');

      const data = await res.json();
      const auctionIds = data.auctionIds || [];

      // Filter local JSON data and maintain the exact semantic ordering returned by BigQuery
      const newCarsArray = auctionIds
        .map((id: string) => carsData.find((c: any) => c.id === id))
        .filter(Boolean); // removes any undefined elements

      setCars(newCarsArray);

    } catch (error) {
      console.error('Semantic search error:', error);
      alert('Error connecting to Google Cloud. Do you have local Application Default Credentials configured?');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container" style={{ padding: '3rem 2rem' }}>

      {/* Page Header */}
      <div style={{ marginBottom: '3rem', textAlign: 'center', animation: 'fadeIn 0.6s ease-out' }}>
        <h2 style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '3rem',
          fontWeight: 800,
          background: 'linear-gradient(90deg, #202124, #5F6368)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '1rem'
        }}>
          Find Your Hidden Gem
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', maxWidth: '600px', margin: '0 auto', textWrap: 'balance' }}>
          We analyze thousands of data points and photos using Google Cloud AI to find you the safest, best-priced vehicles on the market.
        </p>
      </div>

      {/* Filters Area (Live Semantic Search) */}
      <form
        onSubmit={handleSearch}
        style={{
          backgroundColor: 'var(--bg-secondary)',
          padding: '1.5rem',
          borderRadius: '12px',
          boxShadow: 'var(--shadow-sm)',
          border: '1px solid var(--border-light)',
          marginBottom: '2rem',
          display: 'flex',
          gap: '1rem',
          flexWrap: 'wrap'
        }}
      >
        <div style={{ flex: 1, minWidth: '200px' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            disabled={isLoading}
            placeholder="Try searching for &quot;A reliable truck for work...&quot;"
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              borderRadius: '6px',
              border: '1px solid var(--border-medium)',
              fontFamily: 'var(--font-sans)',
              fontSize: '1rem',
              opacity: isLoading ? 0.7 : 1,
            }}
          />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className="btn btn-primary"
          style={{ opacity: isLoading ? 0.7 : 1 }}
        >
          ✨ {isLoading ? 'Searching...' : 'Search Inventory'}
        </button>
      </form>

      {/* Grid of Cars */}
      {cars.length === 0 && !isLoading && (
        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
          <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>No matches found</h3>
          <p>Try rephrasing your search query, or clear the search box to see all inventory.</p>
        </div>
      )}

      {/* Grid of Cars */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', animation: 'fadeIn 0.6s ease-out' }}>
        <h3 style={{ fontSize: '1.75rem', fontFamily: 'var(--font-sans)', fontWeight: 700 }}>
          {searchQuery && cars.length > 0 ? 'Search Results' : 'Featured Deals'}
        </h3>
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: '2rem'
      }}>
        {cars.map((car: any, index: number) => {
          const uiDealScore = computeUiScore(car);
          return (
          <Link href={`/${car.id}`} key={car.id} style={{ textDecoration: 'none' }}>
            <div style={{
              backgroundColor: 'var(--bg-secondary)',
              borderRadius: '16px',
              overflow: 'hidden',
              boxShadow: 'var(--shadow-sm)',
              border: '1px solid var(--border-light)',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease',
              cursor: 'pointer',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              animation: `fadeIn 0.5s ease-out ${index * 0.1}s forwards`,
              opacity: 0,
            }}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
              }}
            >
              {/* Image Container */}
              <div style={{
                position: 'relative',
                height: '240px',
                width: '100%',
                backgroundColor: '#E8EAED',
                overflow: 'hidden'
              }}>
                <img
                  src={car.preview_image}
                  alt={car.title}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover'
                  }}
                  onError={(e) => { e.currentTarget.src = 'https://placehold.co/600x400/E8EAED/80868B?text=Photo+Unavailable'; }}
                />

                {/* The "Hotels.com" Floating Deal Badge */}
                <div style={{
                  position: 'absolute',
                  top: '1rem',
                  left: '1rem',
                  backdropFilter: 'blur(8px)',
                  WebkitBackdropFilter: 'blur(8px)',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                  }} className={`badge ${getDealTier(uiDealScore).badgeClass}`}>
                  <span style={{ fontSize: '1.25rem', marginRight: '0.5rem' }}>
                      {getDealTier(uiDealScore).icon}
                  </span>
                  <div>
                    <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', opacity: 0.9 }}>Deal Score</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>{uiDealScore} <span style={{ fontWeight: 400, opacity: 0.8, fontSize: '0.9rem' }}>({getDealTier(uiDealScore).text})</span></div>
                  </div>
                </div>
              </div>

              {/* Content Container */}
              <div style={{ padding: '1.5rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <div style={{ marginBottom: '0.5rem' }}>
                  <h3 style={{
                      fontFamily: 'var(--font-sans)',
                      fontSize: '1.25rem',
                      fontWeight: 700,
                      color: 'var(--text-primary)',
                    margin: 0,
                      lineHeight: '1.3',
                      display: '-webkit-box',
                      WebkitLineClamp: 1,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden'
                  }}>
                    {car.title}
                    </h3>
                </div>

                <div style={{
                  color: 'var(--text-secondary)',
                    fontSize: '0.875rem',
                  display: 'flex',
                    gap: '0.75rem',
                  marginBottom: '1rem'
                }}>
                    <span>{car.mileage.toLocaleString()} mi</span>
                  <span>•</span>
                  <span>{car.location}</span>
                </div>

                <p style={{
                  color: 'var(--text-secondary)',
                  fontSize: '0.95rem',
                  lineHeight: '1.5',
                  marginBottom: '1.5rem',
                    flex: 1,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden'
                }}>
                  {car.short_description}
                </p>

                <div style={{
                  paddingTop: '1rem',
                  borderTop: '1px solid var(--border-light)',
                  display: 'flex',
                    alignItems: 'baseline',
                    gap: '0.25rem',
                }}>
                    <span style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>$</span>
                    <span style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                      {car.current_bid.toLocaleString()}
                    </span>
                </div>
              </div>
            </div>
          </Link>
          );
        })}
      </div>

      {/* Semantic Search Note */}
      {searchQuery && cars.length > 0 && (
        <div style={{
          textAlign: 'center',
          marginTop: '3rem',
          color: 'var(--text-secondary)',
          fontSize: '0.95rem',
          fontFamily: 'var(--font-sans)',
          animation: 'fadeIn 0.6s ease-out'
        }}>
          💡 <i>Listings are sorted by semantic similarity</i>
        </div>
      )}
    </div>
  );
}
