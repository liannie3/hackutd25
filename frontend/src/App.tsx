import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Activity, AlertTriangle, TrendingUp, Droplet } from 'lucide-react';
import './index.css';

const CauldronGridMap = ({ cauldrons, currentLevels, market }) => {
  if (!cauldrons?.length) {
    return (
      <div className="h-[400px] w-full flex items-center justify-center rounded-lg border border-white/20 bg-black/20">
        <p className="">No cauldrons available for map display</p>
      </div>
    );
  }

  const lats = cauldrons.map((c) => c.latitude);
  const lons = cauldrons.map((c) => c.longitude);

  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);

  const normalize = (val, min, max) => ((val - min) / (max - min)) * 100;

  // Generate 5 evenly spaced grid markers for each axis
  const latTicks = Array.from({ length: 5 }, (_, i) => minLat + ((maxLat - minLat) / 4) * i);
  const lonTicks = Array.from({ length: 5 }, (_, i) => minLon + ((maxLon - minLon) / 4) * i);

  return (
    <div className="relative w-full h-[300px] bg-black/20 border border-white/20 rounded-lg overflow-hidden">
      {/* 🗺️ Grid Lines and Labels */}
      {/* Vertical (Longitude) lines */}
      {lonTicks.map((lon, i) => {
        const x = normalize(lon, minLon, maxLon);
        return (
          <React.Fragment key={`lon-${i}`}>
            <div
              className="absolute top-0 bottom-0 border-l border-white/10"
              style={{ left: `${x}%` }}
            />
            <div
              className="absolute bottom-0 text-[10px] transform translate-x-[-50%]"
              style={{ left: `${x}%`, paddingBottom: '2px' }}
            >
              {lon.toFixed(3)}°
            </div>
          </React.Fragment>
        );
      })}

      {/* Horizontal (Latitude) lines */}
      {latTicks.map((lat, i) => {
        const y = 100 - normalize(lat, minLat, maxLat);
        return (
          <React.Fragment key={`lat-${i}`}>
            <div
              className="absolute left-0 right-0 border-t border-white/10"
              style={{ top: `${y}%` }}
            />
            <div
              className="absolute left-0 text-[10px] transform translate-y-[-50%] pl-1"
              style={{ top: `${y}%` }}
            >
              {lat.toFixed(3)}°
            </div>
          </React.Fragment>
        );
      })}

      {/* 🧪 Cauldron markers */}
      {cauldrons.map((c) => {
        const level = currentLevels[c.id] || 0;
        const fillPercent = Math.min((level / c.max_volume) * 100, 100);

        let color = "bg-green-500";
        if (fillPercent > 80) color = "bg-red-500";
        else if (fillPercent > 50) color = "bg-orange-400";

        const x = normalize(c.longitude, minLon, maxLon);
        const y = 100 - normalize(c.latitude, minLat, maxLat);

        return (
          <div
            key={c.id}
            className="absolute flex flex-col items-center"
            style={{
              left: `${x}%`,
              top: `${y}%`,
              transform: "translate(-50%, -50%)",
            }}
          >
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-xs ${color}`}
              style={{ opacity: 0.85 }}
            >
              {Math.round(fillPercent)}%
            </div>
            <p className="mt-1 text-white text-[10px] text-center bg-black/50 px-1 rounded">
              {c.name || c.id}
            </p>
          </div>
        );
      })}

      {/* 🏪 Market marker */}
      {market && (
        <div
          className="absolute flex flex-col items-center"
          style={{
            left: `${normalize(market.longitude, minLon, maxLon)}%`,
            top: `${100 - normalize(market.latitude, minLat, maxLat)}%`,
            transform: "translate(-50%, -50%)",
          }}
        >
          <div className="w-10 h-10 rounded-md bg-yellow-400 flex items-center justify-center font-bold text-black text-lg shadow-lg">
            ✦
          </div>
          <p className="mt-1 text-yellow-200 text-[10px] text-center bg-black/50 px-1 rounded">
            {market.name}
          </p>
        </div>
      )}
    </div>
  );
};


const App = () => {
  const [cauldrons, setCauldrons] = useState([]);
  const [currentLevels, setCurrentLevels] = useState({});
  const [historicalData, setHistoricalData] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCauldron, setSelectedCauldron] = useState(null);
  const [market, setMarket] = useState(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(false), 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async (forceRefresh = false) => {
    try {
      setLoading(true);
      
      const cauldronRes = await fetch(`/api/Information/cauldrons${forceRefresh ? '?forceRefresh=true' : ''}`);
      if (!cauldronRes.ok) throw new Error(`Cauldrons API returned ${cauldronRes.status}`);
      const cauldronData = await cauldronRes.json();
      setCauldrons(cauldronData);

      // Fetch market info
      const marketRes = await fetch(`/api/Information/market${forceRefresh ? '?forceRefresh=true' : ''}`);
      if (!marketRes.ok) throw new Error(`Market API returned ${marketRes.status}`);
      const marketData = await marketRes.json();
      setMarket(marketData);

      
      // Fetch historical data
      const dataRes = await fetch(`/api/Data${forceRefresh ? '?forceRefresh=true' : ''}`);
      if (!dataRes.ok) throw new Error(`Data API returned ${dataRes.status}`);
      const histData = await dataRes.json();
      
      // Limit historical data to last 200 points to prevent memory issues
      setHistoricalData(histData.slice(-200));
      
      // Get latest levels from most recent data point
      if (histData.length > 0) {
        const latest = histData[histData.length - 1];
        setCurrentLevels(latest.cauldron_levels || {});
      }
      
      // Fetch tickets
      const ticketRes = await fetch(`/api/Tickets${forceRefresh ? '?forceRefresh=true' : ''}`);
      if (!ticketRes.ok) throw new Error(`Tickets API returned ${ticketRes.status}`);
      const ticketData = await ticketRes.json();
      setTickets(ticketData.transport_tickets || []);
      
      // Set first cauldron as selected by default
      if (cauldronData.length > 0 && !selectedCauldron) {
        setSelectedCauldron(cauldronData[0].id);
      }

      setError(null);
    } catch (err) {
      setError('Failed to fetch data: ' + (err instanceof Error ? err.message : String(err)));
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data for selected cauldron
  const getChartData = () => {
    if (!selectedCauldron || historicalData.length === 0) return [];
    
    // Take last 100 data points for visualization
    return historicalData.slice(-100).map(entry => ({
      time: new Date(entry.timestamp).toLocaleTimeString(),
      level: (entry.cauldron_levels && entry.cauldron_levels[selectedCauldron]) || 0
    }));
  };

  // Prepare bar chart data for all cauldrons
  const getBarChartData = () => {
    return cauldrons.map(cauldron => ({
      name: cauldron.name || cauldron.id,
      currentLevel: currentLevels[cauldron.id] || 0,
      maxVolume: cauldron.max_volume,
      utilization: ((currentLevels[cauldron.id] || 0) / cauldron.max_volume * 100).toFixed(1)
    }));
  };

  if (loading && cauldrons.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-indigo-900 to-blue-900 flex items-center justify-center">
        <div className="text-white text-2xl">Loading potion data... 🧙‍♀️</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#cecece] w-full text-[#2a2336]">
      <div className="w-full mx-auto p-6 flex flex-col gap-4">
        {/* Header */}
        <div className="mb-8 flex justify-between">
          <div>
            <h1 className="font-bold mb-2">🧙‍♀️ The Brew Report</h1>
            <p className="text-purple-700">Real-time monitoring of cauldron levels</p>
          </div>
          <button
            onClick={() => fetchData(true)}
            className="mt-4 bg-blue-500 text-white hover:bg-blue-600px-4 py-2 rounded-lg transition-colors"
            disabled={loading}
          >
            {loading ? '⏳ Loading...' : '🔁 Force Refresh'}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 rounded-lg p-4 mb-6">
            <p className="text-red-200">{error}</p>
            <button 
              onClick={() => fetchData(false)}
              className="mt-2 bg-red-500 hover:bg-red-600 px-4 py-2 rounded transition-colors"
            >
              Retry
            </button>
          </div>
        )}
        {/* 🗺️ Grid-based Map Visualization */}
        <CauldronGridMap cauldrons={cauldrons} currentLevels={currentLevels} market={market}/>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 rounded-lg p-4 mb-6">
            <p className="text-red-200">{error}</p>
            <button
              onClick={() => fetchData(false)}
              className="mt-2 bg-red-500 hover:bg-red-600 px-4 py-2 rounded transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        

        {/* Current Levels Bar Chart */}
        <div className="bg-white/10 rounded-lg p-6 border border-white/20">
          <h2 className="text-2xl font-bold mb-4">Current Cauldron Levels</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={getBarChartData()}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="name" stroke="#fff" />
              <YAxis stroke="#fff" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(0,0,0,0.8)', 
                  border: 'none', 
                  borderRadius: '8px',
                  color: '#fff'
                }}
              />
              <Legend />
              <Bar dataKey="currentLevel" fill="#8b5cf6" name="Current Level (L)" />
              <Bar dataKey="maxVolume" fill="#6366f1" name="Max Capacity (L)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Cauldron Details Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Cauldron Selection and Line Chart */}
          <div className="bg-white/10 rounded-lg p-6 border border-white/20">
            <h2 className="text-2xl font-bold mb-4">Historical Levels</h2>
            
            {/* Cauldron Selector */}
            {cauldrons.length > 0 ? (
              <>
                <select
                  value={selectedCauldron || ''}
                  onChange={(e) => setSelectedCauldron(e.target.value)}
                  className="w-full bg-white/20 px-4 py-2 rounded-lg mb-4 border border-white/30"
                >
                  {cauldrons.map(cauldron => (
                    <option key={cauldron.id} value={cauldron.id}>
                      {cauldron.name || cauldron.id}
                    </option>
                  ))}
                </select>

                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={getChartData()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis dataKey="time" stroke="#fff" />
                    <YAxis stroke="#fff" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0,0,0,0.8)', 
                        border: 'none', 
                        borderRadius: '8px',
                        color: '#fff'
                      }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="level" 
                      stroke="#8b5cf6" 
                      strokeWidth={2}
                      dot={false}
                      name="Level (L)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </>
            ) : (
              <p className="text-purple-800">No cauldrons available</p>
            )}
          </div>

          {/* Cauldron Status List */}
          <div className="bg-white/10 rounded-lg p-6 border border-white/20">
            <h2 className="text-2xl font-bold mb-4">Cauldron Status</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {cauldrons.length > 0 ? (
                cauldrons.map(cauldron => {
                  const level = currentLevels[cauldron.id] || 0;
                  const percentage = (level / cauldron.max_volume * 100);
                  const isHigh = percentage > 80;
                  const isMedium = percentage > 50;
                  
                  return (
                    <div 
                      key={cauldron.id} 
                      className="bg-white/10 rounded-lg p-4 border border-white/20"
                    >
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold">{cauldron.name || cauldron.id}</span>
                        <span className="text-sm">
                          {level.toFixed(1)}L / {cauldron.max_volume}L
                        </span>
                      </div>
                      <div className="w-full bg-white/20 rounded-full h-3">
                        <div
                          className={`h-3 rounded-full transition-all ${
                            isHigh ? 'bg-red-500' :
                            isMedium ? 'bg-yellow-500' :
                            'bg-green-500'
                          }`}
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        />
                      </div>
                      <div className="text-xs mt-1">
                        {percentage.toFixed(1)}% full
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-purple-200">No cauldrons available</p>
              )}
            </div>
          </div>
        </div>

        {/* Recent Tickets */}
        <div className="bg-white/10 rounded-lg p-6 border border-white/20">
          <h2 className="text-2xl font-bold mb-4">Recent Transport Tickets</h2>
          <div className="overflow-x-auto">
            {tickets.length > 0 ? (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/20">
                    <th className="text-left py-2 px-4">Ticket ID</th>
                    <th className="text-left py-2 px-4">Cauldron</th>
                    <th className="text-left py-2 px-4">Amount</th>
                    <th className="text-left py-2 px-4">Courier</th>
                    <th className="text-left py-2 px-4">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.slice(-10).reverse().map(ticket => (
                    <tr key={ticket.ticket_id} className="border-b border-white/10">
                      <td className="py-2 px-4">{ticket.ticket_id}</td>
                      <td className="py-2 px-4">{ticket.cauldron_id}</td>
                      <td className="py-2 px-4">{ticket.amount_collected}L</td>
                      <td className="py-2 px-4">{ticket.courier_id}</td>
                      <td className="py-2 px-4">{new Date(ticket.date).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-purple-200">No tickets available</p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-sm">
          Last updated: {new Date().toLocaleTimeString()} • Auto-refresh every 10s
        </div>
      </div>
    </div>
  );
};

export default App;