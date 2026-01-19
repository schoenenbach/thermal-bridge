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

import { ScenarioElement } from './types';

export const resolveValue = (val: any, variables: any): number => {
    if (typeof val === 'number') return val;
    if (typeof val === 'string') {
        const match = val.match(/^\$\{(.+)\}$/);
        if (match) {
            const varName = match[1];
            const resolved = variables[varName];
            return typeof resolved === 'number' ? resolved : 0;
        }
        const parsed = parseFloat(val);
        return isNaN(parsed) ? 0 : parsed;
    }
    return 0;
};

/**
 * Inverse transform: Convert canvas coordinates back to scenario coordinates.
 * Canvas has Y=0 at top, Scenario has Y=0 at bottom.
 */
export const inverseTransformPosition = (
    canvasX: number,
    canvasY: number,
    height: number,
    maxY: number
): { simX: number, simY: number } => {
    // Canvas: Y=0 is top, so element at canvasY with height h has bottom at canvasY + h
    // Scenario: Y=0 is bottom, so simY is distance from bottom to element bottom
    const simY = maxY - (canvasY + height);
    return { simX: canvasX, simY };
};

/**
 * Update scenario element with new canvas position/dimensions.
 * Returns a new scenario object with the updated element.
 */
export const updateScenarioElement = (
    scenario: any,
    elementIndex: number,
    updates: { x?: number, y?: number, width?: number, height?: number },
    maxY: number
): any => {
    if (!scenario || !scenario.elements || elementIndex < 0 || elementIndex >= scenario.elements.length) {
        return scenario;
    }

    const newScenario = { ...scenario };
    newScenario.elements = [...scenario.elements];
    const element = { ...newScenario.elements[elementIndex] };

    // Get current params
    const params = { ...(element.params || {}) };

    // If position changed, apply inverse transform
    if (updates.x !== undefined || updates.y !== undefined || updates.width !== undefined || updates.height !== undefined) {
        const currentWidth = updates.width ?? params.width ?? 0;
        const currentHeight = updates.height ?? params.height ?? 0;
        const canvasX = updates.x ?? 0;
        const canvasY = updates.y ?? 0;

        const { simX, simY } = inverseTransformPosition(canvasX, canvasY, currentHeight, maxY);

        if (updates.x !== undefined) params.x = simX;
        if (updates.y !== undefined) params.y = simY;
        if (updates.width !== undefined) params.width = updates.width;
        if (updates.height !== undefined) params.height = updates.height;
    }

    element.params = params;
    newScenario.elements[elementIndex] = element;

    return newScenario;
};

export const transformElements = (scenarioData: any, variables: any): { elements: ScenarioElement[], stageHeight: number } => {
    // Get canvas bounds to determine logical height for Y-flipping
    let maxY = 500;
    if (scenarioData.canvas && scenarioData.canvas.bounds) {
        const bounds = scenarioData.canvas.bounds;
        const rawMaxY = bounds[3];
        maxY = resolveValue(rawMaxY, variables) || 500;
    }

    const loadedElements = (scenarioData.elements || []).map((el: any, index: number) => {
        const params = el.params || {};
        const props = { ...el, ...params };

        // Resolve raw values
        const rawX = resolveValue(props.x, variables);
        const rawY = resolveValue(props.y, variables);
        const w = resolveValue(props.width, variables);
        const h = resolveValue(props.height, variables);

        const canvasY = maxY - (rawY + h);

        // Handle Polygons
        let calculatedPoints: number[] = [];
        if (el.type === 'polygon' && el.points && scenarioData.points) {
            calculatedPoints = el.points.flatMap((ptName: string) => {
                const ptDef = scenarioData.points[ptName];
                if (ptDef) {
                    const ptX = resolveValue(ptDef[0], variables);
                    const ptY = resolveValue(ptDef[1], variables);
                    // Transform Y
                    return [ptX, maxY - ptY];
                }
                return [0, 0];
            });
        }

        return {
            ...el,
            id: el.id || `el-${index}`,
            type: el.type,
            x: rawX,
            y: canvasY,
            width: w,
            height: h,
            calculatedPoints: calculatedPoints,
            simX: rawX,
            simY: rawY
        };
    });

    const supportedElements = loadedElements.filter((el: any) =>
        ['wall', 'rect', 'polygon', 'window_detail', 'window'].includes(el.type)
    );

    return { elements: supportedElements, stageHeight: maxY };
};
