import { useState, useMemo } from 'react';
import { Search, Shield, Filter } from 'lucide-react';

import { API_ENDPOINTS_DATA } from '../../data/docsData.js';

export { API_ENDPOINTS_DATA };

const CATEGORIES = ['All', 'Meetings', 'Tasks', 'Chat', 'Extraction', 'Users', 'Highlights', 'Notifications'];

/**
 * ApiTable — Interactive API Reference Table (Section 9 Line 728 & ARCHITECTURE.md Section 8)
 * Renders all 21 endpoints with category filtering, search, and responsive breakdown.
 */
function ApiTable() {
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredEndpoints = useMemo(() => {
    return API_ENDPOINTS_DATA.filter((ep) => {
      const matchesCategory = selectedCategory === 'All' || ep.category === selectedCategory;
      const q = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !q ||
        ep.path.toLowerCase().includes(q) ||
        ep.method.toLowerCase().includes(q) ||
        ep.purpose.toLowerCase().includes(q) ||
        ep.category.toLowerCase().includes(q);

      return matchesCategory && matchesSearch;
    });
  }, [selectedCategory, searchQuery]);

  return (
    <div className="api-table-container" aria-label="MeetMind AI API Reference (21 Endpoints)">
      {/* Controls Bar */}
      <div className="api-table-controls">
        <div className="api-search-wrapper">
          <Search size={16} className="api-search-icon" aria-hidden="true" />
          <input
            type="text"
            className="api-search-input"
            placeholder="Search 21 endpoints by path, method, or purpose..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Filter API endpoints"
          />
        </div>

        <div className="api-category-pills" role="tablist" aria-label="Filter by endpoint category">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              type="button"
              role="tab"
              aria-selected={selectedCategory === cat}
              className={`api-category-pill ${selectedCategory === cat ? 'is-active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Table Wrapper */}
      <div className="api-table-wrapper">
        <table className="api-table">
          <thead>
            <tr>
              <th scope="col" style={{ width: '45px' }}>#</th>
              <th scope="col" style={{ width: '90px' }}>Method</th>
              <th scope="col">Endpoint Path</th>
              <th scope="col">Purpose</th>
              <th scope="col" style={{ width: '110px' }}>Category</th>
              <th scope="col" style={{ width: '85px' }}>Auth</th>
            </tr>
          </thead>
          <tbody>
            {filteredEndpoints.length === 0 ? (
              <tr>
                <td colSpan="6" className="api-table-empty">
                  No matching endpoints found for &ldquo;{searchQuery}&rdquo;.
                </td>
              </tr>
            ) : (
              filteredEndpoints.map((ep) => {
                const methodClass = `api-method-${ep.method.toLowerCase()}`;
                return (
                  <tr key={ep.id} className="api-table-row">
                    <td className="api-cell-id">{ep.id}</td>
                    <td className="api-cell-method">
                      <span className={`api-method-badge ${methodClass}`}>{ep.method}</span>
                    </td>
                    <td className="api-cell-path">
                      <code className="api-path-code">{ep.path}</code>
                    </td>
                    <td className="api-cell-purpose">{ep.purpose}</td>
                    <td className="api-cell-category">
                      <span className="api-category-tag">{ep.category}</span>
                    </td>
                    <td className="api-cell-auth">
                      {ep.auth === 'Bearer' ? (
                        <span className="api-auth-badge" title="JWT Bearer Token Required">
                          <Shield size={11} aria-hidden="true" />
                          Bearer
                        </span>
                      ) : (
                        <span className="api-auth-none">None</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="api-table-footer">
        <span className="api-count-text">
          Showing <strong>{filteredEndpoints.length}</strong> of <strong>{API_ENDPOINTS_DATA.length}</strong> documented endpoints
        </span>
        <span className="api-spec-version">OpenAPI 3.1.0 • FastAPI v0.115+</span>
      </div>
    </div>
  );
}

export default ApiTable;
