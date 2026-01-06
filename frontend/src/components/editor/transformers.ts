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
