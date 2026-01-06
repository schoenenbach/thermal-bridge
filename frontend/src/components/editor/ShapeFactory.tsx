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

import React from 'react';
import WallShape from './shapes/WallShape';
import PolygonShape from './shapes/PolygonShape'; // Assuming imported
import { ScenarioElement, RectElement, PolygonElement } from './types';
import { Rect, Text, Group } from 'react-konva';

interface ShapeFactoryProps {
    element: ScenarioElement;
    isSelected: boolean;
    onSelect: (id: string) => void;
    onChange: (id: string, newAttrs: any) => void;
}

const ShapeFactory: React.FC<ShapeFactoryProps> = ({ element, isSelected, onSelect, onChange }) => {
    // Generate a temporary ID if missing
    const id = element.id || `el-${Math.random().toString(36).substr(2, 9)}`;

    switch (element.type) {
        case 'rect':
        case 'wall':
            const rectEl = element as RectElement;
            return (
                <WallShape
                    id={id}
                    x={rectEl.x}
                    y={rectEl.y}
                    width={rectEl.width}
                    height={rectEl.height}
                    isSelected={isSelected}
                    onSelect={onSelect}
                    onChange={onChange}
                />
            );
        case 'polygon':
            const polyEl = element as PolygonElement;
            if (polyEl.calculatedPoints && polyEl.calculatedPoints.length > 0) {
                return (
                    <PolygonShape
                        id={id}
                        points={polyEl.calculatedPoints}
                        isSelected={isSelected}
                        onSelect={onSelect}
                    />
                );
            }
            return null;
        case 'window':
        case 'window_detail':
            // Placeholder for Window
            // We'll render a box at the frame start position if available in params
            const params = element.params || {};
            if (params.x_frame_start && params.y_frame_start) {
                // Simplified visualization request
                return (
                    <Group x={params.x_frame_start} y={params.y_frame_start} onClick={() => onSelect(id)}>
                        <Rect width={100} height={100} stroke="red" dash={[5, 5]} />
                        <Text text="Window" fill="red" />
                    </Group>
                );
            }
            return null;
        default:
            console.warn('Unknown element type:', element.type);
            return null;
    }
};

export default ShapeFactory;
