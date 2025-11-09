import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  Cell,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { CheckCircle, XCircle, AlertTriangle, AlertCircle } from "lucide-react";
import "./index.css";
import refreshIcon from "./assets/refresh.svg";
import poyoIcon from "./assets/poyo.png";
import cauldronIcon from "./assets/cauldron.svg";
import alertIcon from "./assets/alert.svg";
import clockIcon from "./assets/clock.svg";

const CauldronGridMap = ({ cauldrons, currentLevels, market }) => {
  if (!cauldrons?.length) {
    return (
      <div className="flex h-[400px] w-full items-center justify-center rounded-lg border border-white/20 bg-black/20">
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

  // 🧭 Add padding so markers at the edges aren't clipped
  const paddingFactor = 0.15; // 5% of range on each side
  const latRange = maxLat - minLat;
  const lonRange = maxLon - minLon;

  const paddedMinLat = minLat - latRange * paddingFactor;
  const paddedMaxLat = maxLat + latRange * paddingFactor;
  const paddedMinLon = minLon - lonRange * paddingFactor;
  const paddedMaxLon = maxLon + lonRange * paddingFactor;

  const normalize = (val, min, max) => ((val - min) / (max - min)) * 100;

  // Generate 5 evenly spaced grid markers for each axis (using padded range)
  const latTicks = Array.from(
    { length: 5 },
    (_, i) => paddedMinLat + ((paddedMaxLat - paddedMinLat) / 4) * i,
  );
  const lonTicks = Array.from(
    { length: 5 },
    (_, i) => paddedMinLon + ((paddedMaxLon - paddedMinLon) / 4) * i,
  );

  return (
    <div className="relative mb-2 h-[300px] w-full overflow-hidden rounded-lg border border-white/20 bg-white/60">
      {/* 🗺️ Grid Lines and Labels */}
      {/* Vertical (Longitude) lines */}
      {lonTicks.map((lon, i) => {
        const x = normalize(lon, paddedMinLon, paddedMaxLon);
        return (
          <React.Fragment key={`lon-${i}`}>
            <div
              className="absolute top-0 bottom-0 border-l border-black/10"
              style={{ left: `${x}%` }}
            />
            <div
              className="absolute bottom-0 translate-x-[-50%] transform text-[10px]"
              style={{ left: `${x}%`, paddingBottom: "2px" }}
            >
              {lon.toFixed(3)}°
            </div>
          </React.Fragment>
        );
      })}

      {/* Horizontal (Latitude) lines */}
      {latTicks.map((lat, i) => {
        const y = 100 - normalize(lat, paddedMinLat, paddedMaxLat);
        return (
          <React.Fragment key={`lat-${i}`}>
            <div
              className="absolute right-0 left-0 border-t border-black/10"
              style={{ top: `${y}%` }}
            />
            <div
              className="absolute left-0 translate-y-[-50%] transform pl-1 text-[10px]"
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

        let color = "bg-[#2E404A]"; // green (default)
        let textColor = "text-white"; // white text for green

        if (fillPercent < 40) {
          color = "bg-[#794B72]"; // red if < 40%
        } else if (fillPercent < 75) {
          color = "bg-[#e6d18c]"; // yellow if < 75%
          textColor = "text-[#190d42]";
        }

        const x = normalize(c.longitude, paddedMinLon, paddedMaxLon);
        const y = 100 - normalize(c.latitude, paddedMinLat, paddedMaxLat);

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
              className={`flex h-10 w-10 items-center justify-center rounded-full text-xs font-semibold ${color} ${textColor}`}
              style={{ opacity: 0.85 }}
            >
              {Math.round(fillPercent)}%
            </div>
            <p className="mt-1 rounded bg-black/50 px-1 text-center text-[10px] text-white">
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
            left: `${normalize(market.longitude, paddedMinLon, paddedMaxLon)}%`,
            top: `${100 - normalize(market.latitude, paddedMinLat, paddedMaxLat)}%`,
            transform: "translate(-50%, -50%)",
          }}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-yellow-400 text-lg font-bold text-black shadow-lg">
            ✦
          </div>
          <p className="mt-1 rounded bg-black/50 px-1 text-center text-[10px] text-yellow-200">
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
  const [currentPage, setCurrentPage] = useState(1);
  const ticketsPerPage = 10;
  const [annotatedTickets, setAnnotatedTickets] = useState([]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(false), 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async (forceRefresh = false) => {
    try {
      setLoading(true);

      const cauldronRes = await fetch(
        `/api/Information/cauldrons${forceRefresh ? "?forceRefresh=true" : ""}`,
      );
      if (!cauldronRes.ok)
        throw new Error(`Cauldrons API returned ${cauldronRes.status}`);
      const cauldronData = await cauldronRes.json();
      setCauldrons(cauldronData);

      // Fetch market info
      const marketRes = await fetch(
        `/api/Information/market${forceRefresh ? "?forceRefresh=true" : ""}`,
      );
      if (!marketRes.ok)
        throw new Error(`Market API returned ${marketRes.status}`);
      const marketData = await marketRes.json();
      setMarket(marketData);

      // Fetch historical data
      const dataRes = await fetch(
        `/api/Data${forceRefresh ? "?forceRefresh=true" : ""}`,
      );
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
      const ticketRes = await fetch(
        `/api/analyze/annotated-tickets${forceRefresh ? "?forceRefresh=true" : ""}`,
      );
      if (!ticketRes.ok)
        throw new Error(`Tickets API returned ${ticketRes.status}`);
      const ticketData = await ticketRes.json();
      const tickets = ticketData.tickets || [];
      setTickets(tickets);
      setAnnotatedTickets(tickets);

      // Set first cauldron as selected by default
      if (cauldronData.length > 0 && selectedCauldron === null) {
        setSelectedCauldron(cauldronData[0].id);
      }

      setError(null);
    } catch (err) {
      setError(
        "Failed to fetch data: " +
          (err instanceof Error ? err.message : String(err)),
      );
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data for selected cauldron
  const getChartData = () => {
    if (!selectedCauldron || historicalData.length === 0) return [];

    // Take last 100 data points for visualization
    return historicalData.slice(-100).map((entry) => ({
      time: new Date(entry.timestamp).toLocaleTimeString(),
      level:
        (entry.cauldron_levels && entry.cauldron_levels[selectedCauldron]) || 0,
    }));
  };
  const chartData = getChartData();

  // Calculate min/max for dynamic Y-axis scaling
  let minLevel = 0;
  let maxLevel = 0;

  if (chartData.length > 0) {
    const levels = chartData.map((d) => d.level);
    minLevel = Math.min(...levels) * 0.99; // 5% padding below
    maxLevel = Math.max(...levels) * 1.01; // 5% padding above
  }
  // Prepare bar chart data for all cauldrons
  const getBarChartData = () => {
    return cauldrons.map((cauldron) => ({
      name: cauldron.name || cauldron.id,
      currentLevel: currentLevels[cauldron.id] || 0,
      maxVolume: cauldron.max_volume,
      utilization: (
        ((currentLevels[cauldron.id] || 0) / cauldron.max_volume) *
        100
      ).toFixed(1),
    }));
  };

  const getSeverityBadge = (ticket) => {
    const isSuspicious =
      ticket.is_suspicious === true ||
      ticket.is_suspicious === "true" ||
      ticket.is_suspicious === 1;

    if (!isSuspicious) {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-green-500 px-2 py-1 text-xs font-semibold text-white">
          <CheckCircle className="h-3 w-3" />
          VALID
        </span>
      );
    }

    const severity = ticket.suspicion_severity || "medium";
    const styles = {
      critical: { bg: "bg-red-500", icon: XCircle },
      high: { bg: "bg-orange-500", icon: AlertTriangle },
      medium: { bg: "bg-yellow-500 text-black", icon: AlertCircle },
    };

    const style = styles[severity] || styles.medium;
    const Icon = style.icon;

    return (
      <span
        className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold ${style.bg} text-white`}
      >
        <Icon className="h-3 w-3" />
        {severity?.toUpperCase() || "SUSPICIOUS"}
      </span>
    );
  };

  if (loading && cauldrons.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-purple-900 via-indigo-900 to-blue-900">
        <div className="text-2xl text-white">Loading potion data... 🧙‍♀️</div>
      </div>
    );
  }

  const sortedTickets = tickets.sort(
    (a, b) => new Date(b.date) - new Date(a.date),
  );

  const totalPages = Math.ceil(sortedTickets.length / ticketsPerPage);
  const indexOfLastTicket = currentPage * ticketsPerPage;
  const indexOfFirstTicket = indexOfLastTicket - ticketsPerPage;
  const currentTickets = sortedTickets.slice(
    indexOfFirstTicket,
    indexOfLastTicket,
  );

  return (
    <div className="ibm-regular min-h-screen w-full bg-zinc-200 text-[#190d42]">
      <div className="mx-auto flex w-full flex-col gap-3 p-6">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <img src={poyoIcon} alt="Logo" width={70} height={70} />
              <div className="flex flex-col">
                <h1 className="cinzel-title flex items-center gap-2 font-bold">
                  The Brew Report
                </h1>
                <p className="text-xl font-bold text-[#794B72]">
                  What's that? What's abrew?
                </p>
              </div>
            </div>
          </div>
          <button
            onClick={() => fetchData(true)}
            className="flex cursor-pointer items-center justify-center rounded-full bg-transparent p-4 transition-all duration-90 ease-out hover:scale-107 active:scale-90"
            disabled={loading}
          >
            {loading ? (
              <span className="flex animate-spin items-center">
                <img src={refreshIcon} alt="Loading" className="h-6 w-6" />
              </span>
            ) : (
              <img src={refreshIcon} alt="Refresh" className="h-6 w-6" />
            )}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 rounded-lg border border-red-500 bg-red-500/20 p-4">
            <p className="text-red-200">{error}</p>
            <button
              onClick={() => fetchData(false)}
              className="mt-2 rounded bg-red-500 px-4 py-2 transition-colors hover:bg-red-600"
            >
              Retry
            </button>
          </div>
        )}

        {/* 🗺️ Grid-based Map Visualization */}
        <CauldronGridMap
          cauldrons={cauldrons}
          currentLevels={currentLevels}
          market={market}
        />

        <div className="mb-2 rounded-lg border border-white/20 bg-white/80 p-6">
          <div className="mb-4 flex items-center gap-2">
            <img
              src={cauldronIcon}
              alt="Cauldron icon"
              width={40}
              height={40}
            />
            <h2 className="text-2xl font-bold">Current Cauldron Levels</h2>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={getBarChartData()} barGap={-40}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0)" />
              <XAxis
                dataKey="name"
                stroke="#190d42"
                tickFormatter={(value) => value.split(" ")[0]}
              />
              <YAxis stroke="#190d42" />
              <Tooltip
                cursor={{ fill: "rgba(0, 0, 0, 0.07)" }}
                contentStyle={{
                  backgroundColor: "rgba(0,0,0,0.9)",
                  border: "none",
                  borderRadius: "8px",
                  color: "#fff",
                }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    const percent = (
                      (data.currentLevel / data.maxVolume) *
                      100
                    ).toFixed(0);
                    return (
                      <div
                        style={{
                          backgroundColor: "rgba(0,0,0,0.9)",
                          border: "none",
                          borderRadius: "8px",
                          padding: "10px",
                          color: "#fff",
                        }}
                      >
                        <p>{data.name}</p>
                        <p style={{ color: "#8b5cf6" }}>
                          {data.currentLevel}/{data.maxVolume} L ({percent}%)
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar
                dataKey="maxVolume"
                fillOpacity={0}
                fill="#8b5cf6"
                name="Max Capacity (L)"
                barSize={40}
              >
                {getBarChartData().map((entry, index) => {
                  const percent = entry.currentLevel / entry.maxVolume;
                  let color = "#2E404A"; // green (default)

                  if (percent < 0.3)
                    color = "#794B72"; // red if < 40%
                  else if (percent < 0.6) color = "#e6d18c"; // yellow if < 75%

                  return (
                    <Cell
                      key={`cell-max-${index}`}
                      stroke={color}
                      strokeWidth={2}
                    />
                  );
                })}
              </Bar>

              <Bar
                dataKey="currentLevel"
                fill="#8b5cf6"
                name="Current Level (L)"
                barSize={40}
              >
                {getBarChartData().map((entry, index) => {
                  const percent = entry.currentLevel / entry.maxVolume;
                  let color = "#2E404A"; // green (default)

                  if (percent < 0.3)
                    color = "#794B72"; // red if < 40%
                  else if (percent < 0.6) color = "#e6d18c"; // yellow if < 75%

                  return <Cell key={`cell-current-${index}`} fill={color} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Cauldron Details Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Cauldron Selection and Line Chart */}
          <div className="rounded-lg border border-white/20 bg-white/80 p-6">
            <div className="mb-4 flex items-center gap-2">
              <img src={clockIcon} alt="Clock icon" width={45} height={45} />
              <h2 className="text-2xl font-bold">Historical Levels</h2>
            </div>

            {/* Cauldron Selector */}
            {cauldrons.length > 0 ? (
              <>
                <select
                  value={selectedCauldron || ""}
                  onChange={(e) => setSelectedCauldron(e.target.value)}
                  className="mb-4 w-full rounded-lg border border-gray-400 bg-white/20 px-4 py-2"
                >
                  {cauldrons.map((cauldron) => (
                    <option key={cauldron.id} value={cauldron.id}>
                      {cauldron.name || cauldron.id}
                    </option>
                  ))}
                </select>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={getChartData()}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(0,0,0,0.15)"
                    />
                    <XAxis dataKey="time" stroke="#190d42" minTickGap={50} />
                    <YAxis
                      stroke="#190d42"
                      domain={[minLevel, maxLevel]}
                      tickFormatter={(value) => value.toFixed(1)}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "rgba(0,0,0,0.9)",
                        border: "none",
                        borderRadius: "8px",
                        color: "#fff",
                      }}
                      formatter={(value) => {
                        const selectedCauldronData = cauldrons.find(
                          (c) => c.id === selectedCauldron,
                        );
                        if (selectedCauldronData) {
                          const percent = (
                            (value / selectedCauldronData.max_volume) *
                            100
                          ).toFixed(0);
                          return [
                            `${value}/${selectedCauldronData.max_volume} L (${percent}%)`,
                          ];
                        }
                        return [value, "Level (L)"];
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

          <div className="rounded-lg border border-white/20 bg-white/80 p-6">
            <div className="mb-4 flex items-center gap-2">
              <img src={alertIcon} alt="Alert icon" width={45} height={45} />
              <h2 className="text-2xl font-bold">Important Events</h2>
            </div>

            {/* Show recent suspicious tickets */}
            <div className="max-h-[300px] space-y-3 overflow-y-auto">
              {sortedTickets
                .filter((ticket) => ticket.is_suspicious)
                .slice(0, 5)
                .map((ticket) => {
                  const severity = ticket.suspicion_severity || "medium";
                  const severityColors = {
                    critical: "border-red-500 bg-red-50",
                    high: "border-orange-500 bg-orange-50",
                    medium: "border-yellow-500 bg-yellow-50",
                  };
                  const bgColor =
                    severityColors[severity] || severityColors.medium;

                  return (
                    <div
                      key={ticket.ticket_id}
                      className={`rounded-lg border-l-4 p-3 ${bgColor}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="mb-1 flex items-center gap-2">
                            {getSeverityBadge(ticket)}
                            <span className="font-mono text-xs text-gray-600">
                              {ticket.ticket_id}
                            </span>
                          </div>
                          <p className="text-sm font-semibold">
                            {ticket.cauldron_id} • {ticket.amount_collected}L
                          </p>
                          <p className="text-xs text-gray-600">
                            Courier: {ticket.courier_id} •{" "}
                            {new Date(ticket.date).toLocaleDateString()}
                          </p>
                          {ticket.suspicion_reason && (
                            <p className="mt-1 text-xs text-gray-700 italic">
                              {ticket.suspicion_reason}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}

              {sortedTickets.filter((ticket) => ticket.is_suspicious).length ===
                0 && (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <CheckCircle className="mb-2 h-12 w-12 text-green-600" />
                  <p className="text-sm text-gray-600">
                    No suspicious activity detected
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Recent Tickets */}

        <h2 className="mt-4 text-3xl font-bold">Recent Transport Tickets</h2>
        <div className="overflow-x-auto rounded-xl bg-white/80">
          {tickets.length > 0 ? (
            <>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/20 bg-zinc-300">
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Ticket ID</th>
                    <th className="px-4 py-2 text-left">Cauldron</th>
                    <th className="px-4 py-2 text-left">Amount</th>
                    <th className="px-4 py-2 text-left">Courier</th>
                    <th className="px-4 py-2 text-left">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-300">
                  {currentTickets.map((ticket) => {
                    const rowClass = ticket.is_suspicious
                      ? ticket.suspicion_severity === "critical"
                        ? "bg-red-50 hover:bg-red-100"
                        : ticket.suspicion_severity === "high"
                          ? "bg-orange-50 hover:bg-orange-100"
                          : "bg-yellow-50 hover:bg-yellow-100"
                      : "hover:bg-gray-100";

                    return (
                      <tr
                        key={ticket.ticket_id}
                        className={`transition-colors ${rowClass}`}
                      >
                        <td className="px-4 py-2">
                          {getSeverityBadge(ticket)}
                        </td>
                        <td className="px-4 py-2 font-mono text-sm">
                          {ticket.ticket_id}
                        </td>
                        <td className="px-4 py-2">{ticket.cauldron_id}</td>
                        <td className="px-4 py-2 font-semibold">
                          {ticket.amount_collected}L
                        </td>
                        <td className="px-4 py-2">{ticket.courier_id}</td>
                        <td className="px-4 py-2">
                          {new Date(ticket.date).toLocaleDateString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              <div className="flex flex-col gap-3 border-t border-zinc-300 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm">
                  Showing {indexOfFirstTicket + 1}–
                  {Math.min(indexOfLastTicket, sortedTickets.length)} of{" "}
                  {sortedTickets.length} tickets
                </div>

                <div className="flex flex-wrap items-center justify-center gap-2">
                  <button
                    onClick={() =>
                      setCurrentPage((prev) => Math.max(prev - 1, 1))
                    }
                    disabled={currentPage === 1}
                    className="rounded bg-zinc-300 px-4 py-2 transition-colors hover:bg-zinc-400 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Previous
                  </button>

                  <select
                    value={currentPage}
                    onChange={(e) => setCurrentPage(Number(e.target.value))}
                    className="rounded border border-zinc-300 bg-zinc-200 px-3 py-2 focus:ring-2 focus:ring-zinc-400 focus:outline-none"
                  >
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(
                      (page) => (
                        <option key={page} value={page}>
                          Page {page}
                        </option>
                      ),
                    )}
                  </select>

                  <button
                    onClick={() =>
                      setCurrentPage((prev) => Math.min(prev + 1, totalPages))
                    }
                    disabled={currentPage === totalPages}
                    className="rounded bg-zinc-300 px-4 py-2 transition-colors hover:bg-zinc-400 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          ) : (
            <p className="p-4 text-purple-200">No tickets available</p>
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-sm">
          Last updated: {new Date().toLocaleTimeString()} • Auto-refresh every
          10s
        </div>
      </div>
    </div>
  );
};

export default App;
