import React from 'react';
import { BarChart as RechartsBar, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import './ChartWrappers.css';

export const BarChart = ({
    data,
    dataKey,
    key: barKey, // Support key as alias
    xKey = 'name',
    title,
    color = '#10b981',
    height = 300,
    showLegend = false,
    formatValue = (val) => val
}) => {
    const finalDataKey = dataKey || barKey || 'value';
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            return (
                <div className="custom-tooltip">
                    <p className="tooltip-label">{payload[0].payload[xKey]}</p>
                    <p className="tooltip-value" style={{ color }}>
                        {formatValue(payload[0].value)}
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="chart-wrapper">
            {title && <h3 className="chart-title">{title}</h3>}
            <ResponsiveContainer width="100%" height={height}>
                <RechartsBar data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                    <XAxis
                        dataKey={xKey}
                        stroke="#94a3b8"
                        tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <YAxis
                        stroke="#94a3b8"
                        tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f1f5f9' }} />
                    {showLegend && <Legend />}
                    <Bar dataKey={finalDataKey} fill={color} radius={[8, 8, 0, 0]} />
                </RechartsBar>
            </ResponsiveContainer>
        </div>
    );
};

export default BarChart;
