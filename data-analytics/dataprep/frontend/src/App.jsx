import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:3001/api';

function App() {
  const [artworks, setArtworks] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);

  const [selectedArtwork, setSelectedArtwork] = useState(null);
  const [similarArtworks, setSimilarArtworks] = useState([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);

  const fetchArtworks = useCallback(async (isNewSearch) => {
    setLoading(true);
    try {
      const currentPage = isNewSearch ? 1 : page;
      const response = await axios.get(`${API_BASE_URL}/artworks`, {
        params: { search, page: currentPage },
      });
      if (response.data.length < 20) {
        setHasMore(false);
      }
      if (isNewSearch) {
        setArtworks(response.data);
      } else {
        setArtworks(prev => [...prev, ...response.data]);
      }
    } catch (error) {
      console.error("Error fetching artworks:", error);
    } finally {
      setLoading(false);
    }
  }, [search, page]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setArtworks([]);
      setPage(1);
      setHasMore(true);
      fetchArtworks(true);
    }, 500); // Debounce search input
    return () => clearTimeout(handler);
  }, [search, fetchArtworks]);


  const fetchSimilarArtworks = async (objectId) => {
    setLoadingSimilar(true);
    setSimilarArtworks([]);
    try {
      const response = await axios.get(`${API_BASE_URL}/similar-artworks/${objectId}`);
      setSimilarArtworks(response.data);
    } catch (error) {
      console.error("Error fetching similar artworks:", error);
    } finally {
      setLoadingSimilar(false);
    }
  };

  const handleArtworkClick = (artwork) => {
    setSelectedArtwork(artwork);
    fetchSimilarArtworks(artwork.object_id);
  };

  const handleLoadMore = () => {
    setPage(prevPage => prevPage + 1);
  };
  
  useEffect(() => {
    if (page > 1) {
        fetchArtworks(false);
    }
  }, [page]);


  return (
    <div className="app-container">
      {/* Left Panel */}
      <div className="panel left-panel">
        <h2 className="h4 mb-3">Metropolitan Art Explorer</h2>
        <input
          type="text"
          className="form-control search-input"
          placeholder="Search by title..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <ul className="artworks-list">
          {artworks.map(art => (
            <li 
              key={`${art.object_id}-${page}`} 
              className={`artwork-item ${selectedArtwork?.object_id === art.object_id ? 'selected' : ''}`}
              onClick={() => handleArtworkClick(art)}
            >
              <img src={art.image_url} alt={art.title} onError={(e) => e.target.src='https://via.placeholder.com/80'} />
              <div className="artwork-info">
                <span className="title">{art.title || 'Untitled'}</span>
                <span className="artist">{art.artist_display_name || 'Unknown Artist'}</span>
              </div>
            </li>
          ))}
        </ul>
        {loading && <div className="text-center">Loading...</div>}
        {!loading && hasMore && (
          <div className="load-more-container">
            <button className="btn btn-primary" onClick={handleLoadMore}>Load More</button>
          </div>
        )}
      </div>

      {/* Right Panel */}
      <div className="panel right-panel">
        <h2 className="h4 mb-3">Similar Artworks</h2>
        {loadingSimilar ? (
          <div className="placeholder">Loading recommendations...</div>
        ) : selectedArtwork ? (
          <ul className="artworks-list">
            {similarArtworks.map(art => (
              <li key={art.object_id} className="artwork-item">
                <img src={art.image_url} alt={art.title} onError={(e) => e.target.src='https://via.placeholder.com/80'}/>
                <div className="artwork-info">
                  <span className="title">{art.title || 'Untitled'}</span>
                  <span className="artist">{art.artist_display_name || 'Unknown Artist'}</span>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="placeholder">Select an artwork on the left to see similar ones.</div>
        )}
      </div>
    </div>
  );
}

export default App;