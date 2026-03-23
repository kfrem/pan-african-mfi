'use client';
import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Lock, Eye, EyeOff } from 'lucide-react';

/**
 * Public shareable investor dashboard.
 * Accessed via: /share?token=xxxxx
 *
 * Flow:
 * 1. Validate token against investor_share_links table
 * 2. If password-protected, show password form first
 * 3. If valid, render the investor dashboard with read-only data
 * 4. Increment view_count
 * 5. If expired or max_views exceeded, show expiry message
 */
function SharePageInner() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<'loading' | 'password' | 'valid' | 'expired' | 'invalid'>('loading');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('invalid');
      return;
    }
    // In production: validate token via API
    // For now, simulate
    setTimeout(() => setStatus('valid'), 1000);
  }, [token]);

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#060a14' }}>
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400 text-sm">Verifying access...</p>
        </div>
      </div>
    );
  }

  if (status === 'invalid' || status === 'expired') {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#060a14' }}>
        <div className="text-center max-w-md">
          <Lock className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">
            {status === 'expired' ? 'Link Expired' : 'Invalid Link'}
          </h1>
          <p className="text-gray-400 text-sm">
            {status === 'expired'
              ? 'This investor dashboard link has expired. Please contact the institution for a new link.'
              : 'This link is not valid. Please check the URL or contact the institution.'}
          </p>
        </div>
      </div>
    );
  }

  if (status === 'password') {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#060a14' }}>
        <div className="w-full max-w-sm p-8 rounded-xl" style={{ background: '#0c1222', border: '1px solid #1a2744' }}>
          <Lock className="w-10 h-10 mx-auto mb-4" style={{ color: '#0066ff' }} />
          <h2 className="text-lg font-bold text-white text-center mb-2">Password Required</h2>
          <p className="text-gray-400 text-xs text-center mb-6">Enter the password provided by the institution</p>
          <div className="relative mb-4">
            <input type={showPassword ? 'text' : 'password'} value={password}
                   onChange={e => setPassword(e.target.value)}
                   className="w-full px-4 py-3 rounded-lg text-white text-sm"
                   style={{ background: '#060a14', border: '1px solid #1a2744' }}
                   placeholder="Enter password" />
            <button onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
          <button onClick={() => setStatus('valid')}
                  className="w-full py-3 rounded-lg text-white text-sm font-bold"
                  style={{ background: 'linear-gradient(135deg, #0066ff, #0052cc)' }}>
            Access Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Valid — render the investor dashboard
  // In production, this imports the full InvestorDashboard component with real data
  return (
    <div style={{ background: '#060a14', minHeight: '100vh', color: '#e2e8f0', padding: 24 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24,
                      padding: '12px 20px', background: '#0c1222', borderRadius: 12, border: '1px solid #1a2744' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: 'linear-gradient(135deg, #0066ff, #8b5cf6)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 14 }}>
              M
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700 }}>Accra MicroCredit Ltd</div>
              <div style={{ fontSize: 10, color: '#7b8ba5', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Investor Portal · Shared View
              </div>
            </div>
          </div>
          <div style={{ fontSize: 11, color: '#4a5974' }}>
            Read-only · Data as of {new Date().toLocaleDateString('en-GB')}
          </div>
        </div>
        <p style={{ textAlign: 'center', color: '#4a5974', fontSize: 13, marginTop: 40 }}>
          Full investor dashboard renders here with live portfolio data, charts, and covenant status.
        </p>
      </div>
    </div>
  );
}

export default function SharePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#060a14' }}>
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400 text-sm">Verifying access...</p>
        </div>
      </div>
    }>
      <SharePageInner />
    </Suspense>
  );
}
