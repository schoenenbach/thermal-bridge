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
