/*
 * Copyright (C) 2026 Thomas
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';

/**
 * Temperature data from backend
 */
export interface TemperatureData {
    data: number[][];
    width: number;
    height: number;
    temp_min: number;
    temp_max: number;
    rows: number;
    cols: number;
}

interface HeatmapCanvasProps {
    temperatureData: TemperatureData;
    width: number;
    height: number;
    onProbe?: (temp: number, x: number, y: number) => void;
}

/**
 * Jet colormap: blue -> cyan -> green -> yellow -> red
 */
function jetColormap(t: number): [number, number, number] {
    // t is normalized 0-1
    const clamp = (v: number) => Math.max(0, Math.min(1, v));
    t = clamp(t);

    let r, g, b;
    if (t < 0.125) {
        r = 0;
        g = 0;
        b = 0.5 + t * 4;
    } else if (t < 0.375) {
        r = 0;
        g = (t - 0.125) * 4;
        b = 1;
    } else if (t < 0.625) {
        r = (t - 0.375) * 4;
        g = 1;
        b = 1 - (t - 0.375) * 4;
    } else if (t < 0.875) {
        r = 1;
        g = 1 - (t - 0.625) * 4;
        b = 0;
    } else {
        r = 1 - (t - 0.875) * 2;
        g = 0;
        b = 0;
    }

    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

/**
 * Interactive heatmap canvas component for temperature visualization.
 * Features:
 * - Jet colormap visualization
 * - Mouse hover probe showing temperature at cursor
 * - Configurable color scale
 */
export const HeatmapCanvas: React.FC<HeatmapCanvasProps> = ({
    temperatureData,
    width,
    height,
    onProbe
}) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [probeInfo, setProbeInfo] = useState<{ temp: number; x: number; y: number } | null>(null);
    const [colorMin, setColorMin] = useState(temperatureData.temp_min);
    const [colorMax, setColorMax] = useState(temperatureData.temp_max);

    // Update color range when data changes
    useEffect(() => {
        setColorMin(temperatureData.temp_min);
        setColorMax(temperatureData.temp_max);
    }, [temperatureData.temp_min, temperatureData.temp_max]);

    // Render heatmap
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const { data, rows, cols } = temperatureData;
        if (rows === 0 || cols === 0) return;

        // Calculate cell size
        const cellWidth = width / cols;
        const cellHeight = height / rows;

        // Create ImageData for efficiency
        const imageData = ctx.createImageData(width, height);
        const pixels = imageData.data;

        // Fill pixels
        for (let py = 0; py < height; py++) {
            // Map pixel y to data row (inverted - canvas y=0 is top, data row 0 is bottom)
            const dataRow = Math.min(rows - 1, Math.floor((1 - py / height) * rows));

            for (let px = 0; px < width; px++) {
                const dataCol = Math.min(cols - 1, Math.floor(px / width * cols));

                const temp = data[dataRow]?.[dataCol] ?? colorMin;
                const normalized = (temp - colorMin) / (colorMax - colorMin || 1);
                const [r, g, b] = jetColormap(normalized);

                const idx = (py * width + px) * 4;
                pixels[idx] = r;
                pixels[idx + 1] = g;
                pixels[idx + 2] = b;
                pixels[idx + 3] = 255;
            }
        }

        ctx.putImageData(imageData, 0, 0);
    }, [temperatureData, width, height, colorMin, colorMax]);

    // Handle mouse move for probe
    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const { data, rows, cols } = temperatureData;

        // Map to data coordinates
        const dataCol = Math.min(cols - 1, Math.floor(x / width * cols));
        const dataRow = Math.min(rows - 1, Math.floor((1 - y / height) * rows));

        const temp = data[dataRow]?.[dataCol] ?? 0;

        setProbeInfo({ temp, x, y });
        onProbe?.(temp, x, y);
    }, [temperatureData, width, height, onProbe]);

    const handleMouseLeave = useCallback(() => {
        setProbeInfo(null);
    }, []);

    return (
        <div style={{ position: 'relative', display: 'inline-block' }}>
            <canvas
                ref={canvasRef}
                width={width}
                height={height}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
                style={{
                    border: '1px solid #ddd',
                    cursor: 'crosshair'
                }}
            />

            {/* Color scale legend */}
            <div style={{
                position: 'absolute',
                right: -60,
                top: 0,
                bottom: 0,
                width: 50,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                fontSize: '11px',
                color: '#666'
            }}>
                <span>{colorMax.toFixed(1)}°C</span>
                <div style={{
                    width: 15,
                    height: height - 40,
                    background: 'linear-gradient(to bottom, #f00, #ff0, #0f0, #0ff, #00f)',
                    border: '1px solid #ccc',
                    margin: '5px 0'
                }} />
                <span>{colorMin.toFixed(1)}°C</span>
            </div>

            {/* Probe tooltip */}
            {probeInfo && (
                <div style={{
                    position: 'absolute',
                    left: probeInfo.x + 15,
                    top: probeInfo.y - 30,
                    background: 'rgba(0,0,0,0.85)',
                    color: '#fff',
                    padding: '4px 8px',
                    borderRadius: 4,
                    fontSize: '12px',
                    fontFamily: 'monospace',
                    pointerEvents: 'none',
                    whiteSpace: 'nowrap',
                    zIndex: 100
                }}>
                    {probeInfo.temp.toFixed(2)}°C
                </div>
            )}
        </div>
    );
};

export default HeatmapCanvas;
