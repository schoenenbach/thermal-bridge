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

export interface ScenarioElement {
    type: 'rect' | 'wall' | 'window' | 'insulation' | 'polygon' | 'window_detail';
    id?: string; // Some elements might not have ID in YAML, but we need one for UI
    [key: string]: any;
}

export interface RectElement extends ScenarioElement {
    type: 'rect' | 'wall';
    x: number;
    y: number;
    width: number;
    height: number;
}


export interface PolygonElement extends ScenarioElement {
    type: 'polygon';
    points: string[]; // Points are references to 'points' dict initially
    // Calculated points will be stored separately or mapped
    calculatedPoints?: number[];
}

export interface WindowElement extends ScenarioElement {
    type: 'window' | 'window_detail'; // Support both
    // ... params
}

