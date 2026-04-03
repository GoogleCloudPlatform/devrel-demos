"use client";

import { useState } from 'react';

export default function ImageCarousel({ images, altText }: { images: string[], altText: string }) {
  const [currentIndex, setCurrentIndex] = useState(0);

  if (!images || images.length === 0) {
    return (
      <img
        src="/placeholder-car.jpg"
        alt="No Image Available"
        style={{ width: '100%', height: '500px', objectFit: 'cover', borderRadius: '12px', boxShadow: 'var(--shadow-sm)' }}
      />
    );
  }

  return (
    <div style={{ marginBottom: '3rem' }}>
      {/* Main Large Image */}
      <div style={{ position: 'relative', width: '100%', height: '500px', borderRadius: '12px', overflow: 'hidden', boxShadow: 'var(--shadow-md)', backgroundColor: '#000' }}>
        <img
          src={images[currentIndex]}
          alt={`${altText} - primary view`}
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
        />

        {/* Carousel Controls */}
        {images.length > 1 && (
          <>
            <button
              onClick={() => setCurrentIndex((prev) => (prev === 0 ? images.length - 1 : prev - 1))}
              style={{
                position: 'absolute', top: '50%', left: '1rem', transform: 'translateY(-50%)',
                background: 'rgba(255,255,255,0.9)', border: 'none', borderRadius: '50%',
                width: '40px', height: '40px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: 'var(--shadow-sm)', zIndex: 10
              }}
            >
              ❮
            </button>
            <button
              onClick={() => setCurrentIndex((prev) => (prev === images.length - 1 ? 0 : prev + 1))}
              style={{
                position: 'absolute', top: '50%', right: '1rem', transform: 'translateY(-50%)',
                background: 'rgba(255,255,255,0.9)', border: 'none', borderRadius: '50%',
                width: '40px', height: '40px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: 'var(--shadow-sm)', zIndex: 10
              }}
            >
              ❯
            </button>

            <div style={{
              position: 'absolute', bottom: '1rem', right: '1rem',
              background: 'rgba(0,0,0,0.6)', color: 'white', padding: '0.25rem 0.75rem',
              borderRadius: '100px', fontSize: '0.8rem', fontWeight: 500
            }}>
              {currentIndex + 1} / {images.length}
            </div>
          </>
        )}
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div style={{ display: 'flex', gap: '1rem', overflowX: 'auto', padding: '1rem 0', scrollbarWidth: 'none' }}>
          {images.map((imgUrl, i) => (
            <div
              key={i}
              onClick={() => setCurrentIndex(i)}
              style={{
                width: '120px', height: '90px', flexShrink: 0, cursor: 'pointer',
                borderRadius: '8px', overflow: 'hidden',
                border: currentIndex === i ? '2px solid var(--accent-blue)' : '2px solid transparent',
                opacity: currentIndex === i ? 1 : 0.6,
                transition: 'all 0.2s ease'
              }}
            >
              <img
                src={imgUrl}
                alt={`Thumbnail ${i + 1}`}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
