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

/**
 * API Data Models
 * Mirrored from backend/app/models.py
 */

export interface ScenarioSummary {
    filename: string;
    name: string;
    description?: string;
    element_count: number;
    has_measurements: boolean;
}

export interface ValidationError {
    field: string;
    message: string;
    line?: number;
}

export interface ValidationResult {
    is_valid: boolean;
    errors: ValidationError[];
    warnings: string[];
    scenario_name?: string;
}

export interface MaterialInfo {
    id: string;
    name: string;
    lambda: number;
    color: string;
    category?: string;
    source?: string;
}

export interface TemperatureData {
    data: number[][];
    width: number;
    height: number;
    temp_min: number;
    temp_max: number;
    rows: number;
    cols: number;
}

export interface ScenarioDetail {
    filename: string;
    yaml_content: string;
    data: any; // Full scenario object
}

// Basic structure for Scenario for typing parts of the UI
export interface Scenario {
    name: string;
    description?: string;
    canvas: {
        bounds: [number, number, number, number];
        grid: number;
    };
    elements: any[];
}
