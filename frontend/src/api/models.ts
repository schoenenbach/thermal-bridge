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
