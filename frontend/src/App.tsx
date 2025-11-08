import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Activity, AlertTriangle, TrendingUp, Droplet } from 'lucide-react';

const App = () => {
  const [cauldrons, setCauldrons] = useState([]);
  const [currentLevels, setCurrentLevels] = useState({});
  const [historicalData, setHistoricalData] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCauldron, setSelectedCauldron] = useState(null);

  useEffect(() => {
    fetchData();
    // Refresh data every 30 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async (forceRefresh = false) => {
    try {
      setLoading(true);
      
      // Fetch cauldrons info
      const cauldronRes = await fetch(`/api/Information/cauldrons?forceRefresh=${forceRefresh}`);
      const cauldronData = await cauldronRes.json();
      setCauldrons(cauldronData);
      
      // Fetch historical data
      const dataRes = await fetch(`/api/Data?forceRefresh=${forceRefresh}`);
      const histData = await dataRes.json();
      setHistoricalData(histData);
      
      // Get latest levels from most recent data point
      if (histData.length > 0) {
        const latest = histData[histData.length - 1];
        setCurrentLevels(latest.cauldron_levels || {});
      }
      
      // Fetch tickets
      const ticketRes = await fetch(`/api/Tickets?forceRefresh=${forceRefresh}`);
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
      level: entry.cauldron_levels[selectedCauldron] || 0
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
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-indigo-900 to-blue-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">🧙‍♀️ Potion Factory Dashboard</h1>
          <p className="text-purple-200">Real-time monitoring of cauldron levels</p>
          <button
            onClick={() => fetchData(true)}  // 👈 we'll update fetchData next
            className="mt-4 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors"
          >
            🔁 Force Refresh
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 rounded-lg p-4 mb-6">
            <p className="text-red-200">{error}</p>
            <button 
              onClick={fetchData}
              className="mt-2 bg-red-500 hover:bg-red-600 px-4 py-2 rounded transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-5 h-5 text-blue-300" />
              <div className="text-sm text-purple-200">Total Cauldrons</div>
            </div>
            <div className="text-3xl font-bold">{cauldrons.length}</div>
          </div>
          
          <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
            <div className="flex items-center gap-2 mb-2">
              <Droplet className="w-5 h-5 text-cyan-300" />
              <div className="text-sm text-purple-200">Total Capacity</div>
            </div>
            <div className="text-3xl font-bold">
              {cauldrons.reduce((sum, c) => sum + c.max_volume, 0).toFixed(0)}L
            </div>
          </div>
          
          <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-5 h-5 text-green-300" />
              <div className="text-sm text-purple-200">Current Volume</div>
            </div>
            <div className="text-3xl font-bold">
              {Object.values(currentLevels).reduce((sum, level) => sum + level, 0).toFixed(0)}L
            </div>
          </div>
          
          <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-5 h-5 text-yellow-300" />
              <div className="text-sm text-purple-200">Total Tickets</div>
            </div>
            <div className="text-3xl font-bold">{tickets.length}</div>
          </div>
        </div>

        {/* Current Levels Bar Chart */}
        <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 border border-white/20 mb-6">
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Cauldron Selection and Line Chart */}
          <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 border border-white/20">
            <h2 className="text-2xl font-bold mb-4">Historical Levels</h2>
            
            {/* Cauldron Selector */}
            <select
              value={selectedCauldron || ''}
              onChange={(e) => setSelectedCauldron(e.target.value)}
              className="w-full bg-white/20 text-white px-4 py-2 rounded-lg mb-4 border border-white/30"
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
          </div>

          {/* Cauldron Status List */}
          <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 border border-white/20">
            <h2 className="text-2xl font-bold mb-4">Cauldron Status</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {cauldrons.map(cauldron => {
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
                    <div className="text-xs text-purple-200 mt-1">
                      {percentage.toFixed(1)}% full
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Recent Tickets */}
        <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 border border-white/20">
          <h2 className="text-2xl font-bold mb-4">Recent Transport Tickets</h2>
          <div className="overflow-x-auto">
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
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-purple-200 text-sm">
          Last updated: {new Date().toLocaleTimeString()} • Auto-refresh every 5s
        </div>
      </div>
    </div>
  );
};

export default App;