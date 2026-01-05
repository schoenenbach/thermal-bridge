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

